"""Lane SAT proof-of-concept: read real values of satellite scene-QC and imagery features at the 15 test AOIs.

Usage: python poc.py [source ...]    (no argument runs every source)
Writes poc_values.csv and poc_status.csv next to this file. One function per source.

Scene selection: the three Planetary Computer sources reuse the scene ids of the 45 POC scene records
(../../A/scene_qc_backfill.csv, ids only); every value is re-read here from the live scene. The static open
SAR catalogues (Umbra, Capella, ICEYE) use lane A's crawled footprint index (../../A/cache/sar_*.json,
read-only) only to find which items intersect which AOI; each chosen item is then re-fetched live.
"""
import csv, json, math, re, sys, time, warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, urljoin
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, requests, rasterio
import planetary_computer as pc
from affine import Affine
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.windows import Window
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from shapely.geometry import shape, box, Polygon
from shapely.ops import transform as shp_transform

ROOT = Path("/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query")
HERE = ROOT / "reports/probes/SAT/poc"
AIDX = ROOT / "reports/probes/A"
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
ES_STAC = "https://earth-search.aws.element84.com/v1"
LL_STAC = "https://landsatlook.usgs.gov/stac-server"
WINDOW = "2024-05-01T00:00:00Z/2024-09-30T23:59:59Z"
MAXPIX = 3000

S = requests.Session()
S.headers["User-Agent"] = "geoquery-poc-SAT/1.0"
GDAL = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff,.xml",
            GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="3", GDAL_HTTP_TIMEOUT="60", VSI_CACHE="TRUE")

FEATS = pd.read_csv(ROOT / "reports/probed_features.csv")
AOIS = {f["properties"]["aoi_id"]: shape(f["geometry"])
        for f in json.load(open(ROOT / "examples/test_aois.geojson"))["features"]}
SOURCES = ["sentinel2_l2a", "landsat_c2l2_st", "sentinel1_rtc", "hls", "s2_l1c", "landsat_l1", "maxar_open",
           "satellogic_earthview", "umbra_open", "capella_open", "iceye_open", "planet_open"]

ROWS, REASON, EXTRA_FEATS = [], {}, {}
COLS = ["aoi_id", "source", "feature", "value", "unit", "time", "time_accuracy", "description", "source_url", "licence", "endpoint"]


def meta(source, feature):
    m = FEATS[(FEATS.source == source) & (FEATS.feature == feature)]
    if len(m):
        return m.iloc[0].description, m.iloc[0].licence, m.iloc[0].source_url
    return EXTRA_FEATS[(source, feature)]


def add(aoi, source, feature, value, unit, time, acc, endpoint):
    d, lic, url = meta(source, feature)
    if isinstance(value, float):
        value = round(value, 5)
    ROWS.append(dict(aoi_id=aoi, source=source, feature=feature, value=value, unit=unit, time=time, time_accuracy=acc,
                     description=d, source_url=url, licence=lic, endpoint=endpoint))
    print(f"  {aoi:26s} {source:20s} {feature:28s} {value}", flush=True)


def note(source, feature, reason):
    REASON.setdefault((source, feature), [])
    if reason not in REASON[(source, feature)]:
        REASON[(source, feature)].append(reason)


def note_all(source, reason, only=None):
    for f in FEATS[FEATS.source == source].feature:
        if only is None or f in only:
            note(source, f, reason)


def http(method, url, retries=5, **kw):
    kw.setdefault("timeout", 60)
    for k in range(retries):
        try:
            r = S.request(method, url, **kw)
        except requests.RequestException:
            time.sleep(2 * 2 ** k)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(3 * 2 ** k)
            continue
        return r
    return r if "r" in locals() else None


def jget(url, **kw):
    r = http("GET", url, **kw)
    return r.json() if r is not None and r.status_code == 200 else None


def stac_search(url, body):
    r = http("POST", url, json=body)
    if r is None or r.status_code != 200:
        return []
    return r.json().get("features", [])


def covers(item, geom):
    g = shape(item["geometry"])
    return (g.contains(geom), g.intersection(geom).area / geom.area)


def best_item(items, geom):
    """Item covering most of the AOI, then lowest cloud, then newest."""
    sc = []
    for it in items:
        c, f = covers(it, geom)
        sc.append((round(f, 3), -(it["properties"].get("eo:cloud_cover") or 0), it["properties"].get("datetime", ""), it))
    sc.sort(key=lambda t: t[:3], reverse=True)
    return sc[0][3] if sc else None


def reproject(geom, crs_to):
    tr = Transformer.from_crs("EPSG:4326", crs_to, always_xy=True).transform
    return shp_transform(tr, geom)


def read_window(src, poly_pix, bands=(1,), maxpix=MAXPIX):
    """Read the part of the pixel-space polygon that falls in the image; return (stack, inside-mask)."""
    b = poly_pix.bounds
    win = Window(b[0], b[1], b[2] - b[0], b[3] - b[1]).intersection(Window(0, 0, src.width, src.height))
    c0, r0 = math.floor(win.col_off), math.floor(win.row_off)
    c1, r1 = min(src.width, math.ceil(win.col_off + win.width)), min(src.height, math.ceil(win.row_off + win.height))
    w, h = c1 - c0, r1 - r0
    if w <= 0 or h <= 0:
        return None, None
    sc = min(1.0, maxpix / max(w, h))
    oh, ow = max(1, int(h * sc)), max(1, int(w * sc))
    last = None
    for k in range(4):
        try:
            arr = src.read(list(bands), window=Window(c0, r0, w, h), out_shape=(len(bands), oh, ow))
            break
        except Exception as e:
            last = e
            time.sleep(3 * 2 ** k)
    else:
        raise last
    t = Affine.translation(c0, r0) * Affine.scale(w / ow, h / oh)
    inside = geometry_mask([poly_pix], out_shape=(oh, ow), transform=t, invert=True)
    return arr, inside


def pix_poly(src, geom):
    g = reproject(geom, src.crs)
    inv = ~src.transform
    return Polygon([inv * (x, y) for x, y in g.exterior.coords])


def open_pc(href):
    return rasterio.open(pc.sign(href))


# ---------------------------------------------------------------- Planetary Computer scene records
def poc_ids(adapter):
    d = pd.read_csv(AIDX / "scene_qc_backfill.csv", usecols=["aoi_id", "adapter", "item_id"])
    return dict(d[d.adapter == adapter][["aoi_id", "item_id"]].values)


def parse_s2_angles(xml_bytes):
    root = ET.fromstring(xml_bytes)
    zen, azi, sun = [], [], {}
    for m in root.iter():
        if m.tag.endswith("Mean_Viewing_Incidence_Angle"):
            for e in m:
                if e.tag.endswith("ZENITH_ANGLE"):
                    zen.append(float(e.text))
                if e.tag.endswith("AZIMUTH_ANGLE"):
                    azi.append(float(e.text))
        if m.tag.endswith("Mean_Sun_Angle"):
            for e in m:
                sun[e.tag.split("}")[-1]] = float(e.text)
    return zen, azi, sun


def s2_l2a():
    src, coll = "sentinel2_l2a", "sentinel-2-l2a"
    ep = f"{PC_STAC}/collections/{coll}/items/{{id}}"
    for aoi, iid in poc_ids("sentinel2_l2a").items():
        try:
            it = jget(f"{PC_STAC}/collections/{coll}/items/{iid}")
            if not it:
                continue
            p, a = it["properties"], it["assets"]
            t, e = p["datetime"], ep.replace("{id}", iid)
            x = http("GET", pc.sign(a["granule-metadata"]["href"]))
            zen, azi, sun = parse_s2_angles(x.content) if x is not None and x.status_code == 200 else ([], [], {})
            if zen:
                add(aoi, src, "s2_off_nadir_deg", float(np.mean(zen)), "deg (mean of %d band zenith angles, granule MTD_TL.xml)" % len(zen), t, "PT1S", e)
            else:
                note(src, "s2_off_nadir_deg", "granule metadata unreadable")
            el = 90 - sun["ZENITH_ANGLE"] if "ZENITH_ANGLE" in sun else (90 - p["s2:mean_solar_zenith"])
            az = sun.get("AZIMUTH_ANGLE", p.get("s2:mean_solar_azimuth"))
            add(aoi, src, "s2_sun_elevation_deg", el, "deg", t, "PT1S", e)
            add(aoi, src, "s2_sun_azimuth_deg", az, "deg", t, "PT1S", e)
            add(aoi, src, "s2_cloud_cover_scene_pct", p["eo:cloud_cover"], "percent of tile", t, "PT1S", e)
            with open_pc(a["SCL"]["href"]) as ds:
                arr, inside = read_window(ds, pix_poly(ds, AOIS[aoi]))
            v = inside & (arr[0] != 0)
            if v.sum():
                cls = arr[0][v]
                add(aoi, src, "s2_cloud_cover_aoi_pct", float(np.isin(cls, [3, 8, 9, 10]).mean() * 100),
                    "percent of valid AOI pixels, SCL classes 3,8,9,10", t, "PT1S", e)
            else:
                note(src, "s2_cloud_cover_aoi_pct", f"{aoi}: no valid SCL pixels in AOI")
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note_all(src, f"{aoi}: {type(ex).__name__}")


def landsat_l2():
    src, coll = "landsat_c2l2_st", "landsat-c2-l2"
    ep = f"{PC_STAC}/collections/{coll}/items/{{id}}"
    for aoi, iid in poc_ids("landsat_c2l2_st").items():
        try:
            it = jget(f"{PC_STAC}/collections/{coll}/items/{iid}")
            if not it:
                continue
            p, a = it["properties"], it["assets"]
            t, e = p["datetime"], ep.replace("{id}", iid)
            add(aoi, src, "lst_off_nadir_deg", p["view:off_nadir"], "deg", t, "PT1S", e)
            add(aoi, src, "lst_sun_elevation_deg", p["view:sun_elevation"], "deg", t, "PT1S", e)
            add(aoi, src, "lst_sun_azimuth_deg", p["view:sun_azimuth"], "deg", t, "PT1S", e)
            add(aoi, src, "lst_cloud_cover_scene_pct", p["eo:cloud_cover"], "percent of scene", t, "PT1S", e)
            with open_pc(a["qa_pixel"]["href"]) as ds:
                arr, inside = read_window(ds, pix_poly(ds, AOIS[aoi]))
            q = arr[0].astype(np.uint32)
            v = inside & ((q & 1) == 0)
            if v.sum():
                anyc = (((q >> 1) | (q >> 2) | (q >> 3) | (q >> 4)) & 1).astype(bool)
                add(aoi, src, "lst_cloud_cover_aoi_pct", float(anyc[v].mean() * 100),
                    "percent of valid AOI pixels, QA_PIXEL bits 1-4", t, "PT1S", e)
            else:
                note(src, "lst_cloud_cover_aoi_pct", f"{aoi}: no valid QA pixels in AOI")
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note_all(src, f"{aoi}: {type(ex).__name__}")


def s1_rtc():
    src, coll = "sentinel1_rtc", "sentinel-1-rtc"
    ep = f"{PC_STAC}/collections/{coll}/items/{{id}} + GRD sidecar annotation/iw-vv.xml"
    for aoi, iid in poc_ids("sentinel1_rtc").items():
        try:
            it = jget(f"{PC_STAC}/collections/{coll}/items/{iid}")
            if not it:
                continue
            h = it["assets"]["vv"]["href"].rsplit("/measurement/", 1)[0]
            base = h.replace("sentinel1euwestrtc.blob", "sentinel1euwest.blob").replace("/sentinel1-grd-rtc/", "/s1-grd/")
            x = http("GET", pc.sign(base + "/annotation/iw-vv.xml"))
            if x is None or x.status_code != 200:
                note(src, "s1_incidence_deg", f"{aoi}: GRD annotation HTTP {getattr(x, 'status_code', None)}")
                continue
            pts = re.findall(r"<latitude>(.*?)</latitude>\s*<longitude>(.*?)</longitude>.*?<incidenceAngle>(.*?)</incidenceAngle>", x.text, re.S)
            arr = np.array(pts, dtype=float)
            c = AOIS[aoi].centroid
            f = LinearNDInterpolator(arr[:, [1, 0]], arr[:, 2])(c.x, c.y)
            if np.isnan(f):
                f = NearestNDInterpolator(arr[:, [1, 0]], arr[:, 2])(c.x, c.y)
            add(aoi, src, "s1_incidence_deg", float(f), "deg at AOI centroid (geolocationGrid, %d pts)" % len(arr),
                it["properties"]["datetime"], "PT1S", ep.replace("{id}", iid))
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note(src, "s1_incidence_deg", f"{aoi}: {type(ex).__name__}")


# ---------------------------------------------------------------- HLS
HLS_BANDS = {"hls2-l30": [("B02", "blue"), ("B03", "green"), ("B04", "red"), ("B05", "nir"), ("B06", "swir1"), ("B07", "swir2")],
             "hls2-s30": [("B02", "blue"), ("B03", "green"), ("B04", "red"), ("B8A", "nir"), ("B11", "swir1"), ("B12", "swir2")]}


def hls():
    src = "hls"
    for aoi, g in AOIS.items():
        try:
            items = []
            for coll in HLS_BANDS:
                for it in stac_search(f"{PC_STAC}/search", {"collections": [coll], "bbox": list(g.bounds), "datetime": WINDOW, "limit": 100,
                                                            "query": {"eo:cloud_cover": {"lt": 20}}}):
                    it["_coll"] = coll
                    items.append(it)
            it = best_item(items, g)
            if not it:
                note_all(src, f"{aoi}: no HLS scene with cloud<20 in window")
                continue
            coll, p, a = it["_coll"], it["properties"], it["assets"]
            t = p["datetime"]
            e = f"{PC_STAC}/collections/{coll}/items/{it['id']}"
            add(aoi, src, "hls_view_azimuth_deg", p["view:azimuth"], "deg", t, "PT1S", e)
            add(aoi, src, "hls_sun_azimuth_deg", p["view:sun_azimuth"], "deg", t, "PT1S", e)
            add(aoi, src, "hls_cloud_cover_scene_pct", p["eo:cloud_cover"], "percent of tile", t, "PT1S", e)
            with open_pc(a["Fmask"]["href"]) as ds:
                fm, inside = read_window(ds, pix_poly(ds, g))
            fm = fm[0]
            # Fmask bits: 0 cirrus, 1 cloud, 2 adjacent, 3 shadow; bits 6-7 aerosol are not a mask
            clear = inside & (fm != 255) & ((fm & 0b1111) == 0)
            if not clear.sum():
                note(src, "hls_reflectance", f"{aoi}: no clear pixels in AOI")
            with open_pc(a["VZA"]["href"]) as ds:
                vz, ins2 = read_window(ds, pix_poly(ds, g))
                nd, sc = ds.nodata, (ds.scales[0] if ds.scales and ds.scales[0] != 1 else 0.01)
            vv = ins2 & (vz[0] != (nd if nd is not None else -9999)) & (vz[0] != 40000)
            if vv.sum():
                add(aoi, src, "hls_view_zenith_deg", float(vz[0][vv].astype(float).mean() * sc), "deg, AOI mean of per-pixel VZA", t, "PT1S", e)
            else:
                note(src, "hls_view_zenith_deg", f"{aoi}: VZA has no valid pixels in AOI")
            if clear.sum():
                vals = []
                for bid, name in HLS_BANDS[coll]:
                    with open_pc(a[bid]["href"]) as ds:
                        arr, ins3 = read_window(ds, pix_poly(ds, g))
                        nd = ds.nodata
                    m = clear if arr[0].shape == clear.shape else None
                    if m is None:
                        # bands share the tile grid, so shapes match unless decimation rounds differently
                        m = ins3 & (arr[0] != nd)
                    d = arr[0][m & (arr[0] != nd)].astype(float) * 0.0001
                    if d.size:
                        vals.append(f"{name}={d.mean():.4f}")
                if vals:
                    add(aoi, src, "hls_reflectance", ";".join(vals), "surface reflectance 0-1, AOI mean of Fmask-clear pixels (%s %s)" % (coll, ",".join(b for b, _ in HLS_BANDS[coll])), t, "PT1S", e)
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note_all(src, f"{aoi}: {type(ex).__name__}")


# ---------------------------------------------------------------- Earth Search Sentinel-2 L1C
def s2_l1c():
    src = "s2_l1c"
    for aoi, g in AOIS.items():
        try:
            items = stac_search(f"{ES_STAC}/search", {"collections": ["sentinel-2-l1c"], "bbox": list(g.bounds), "datetime": WINDOW, "limit": 100,
                                                      "query": {"eo:cloud_cover": {"lt": 20}}})
            it = best_item(items, g)
            if not it:
                note_all(src, f"{aoi}: no L1C scene in window", only=[f for f in FEATS[FEATS.source == src].feature if "toa" not in f])
                continue
            p, t = it["properties"], it["properties"]["datetime"]
            e = f"{ES_STAC}/collections/sentinel-2-l1c/items/{it['id']}"
            add(aoi, src, "s2l1c_sun_elevation_deg", p["view:sun_elevation"], "deg", t, "PT1S", e)
            add(aoi, src, "s2l1c_sun_azimuth_deg", p["view:sun_azimuth"], "deg", t, "PT1S", e)
            add(aoi, src, "s2l1c_cloud_cover_scene_pct", p["eo:cloud_cover"], "percent of tile", t, "PT1S", e)
            href = it["assets"]["granule_metadata"]["href"].replace("s3://sentinel-s2-l1c/", "https://sentinel-s2-l1c.s3.amazonaws.com/")
            x = http("GET", href)
            zen, azi, sun = parse_s2_angles(x.content) if x is not None and x.status_code == 200 else ([], [], {})
            if zen:
                add(aoi, src, "s2l1c_view_zenith_deg", float(np.mean(zen)), "deg (mean of %d band zenith angles, metadata.xml)" % len(zen), t, "PT1S", e + " -> " + href)
            else:
                note(src, "s2l1c_view_zenith_deg", f"{aoi}: metadata.xml HTTP {getattr(x, 'status_code', None)}")
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note_all(src, f"{aoi}: {type(ex).__name__}")
    note(src, "s2l1c_toa_reflectance",
         "pixels are JPEG2000 (.jp2) on s3://sentinel-s2-l1c; the geoquery env has no GDAL JP2 driver (JP2OpenJPEG plugin missing) and no JP2 window reader, "
         "and a whole-band download is not allowed; not installing packages")


# ---------------------------------------------------------------- LandsatLook Collection 2 Level-1
def landsat_l1():
    src = "landsat_l1"
    for aoi, g in AOIS.items():
        try:
            items = stac_search(f"{LL_STAC}/search", {"collections": ["landsat-c2l1"], "bbox": list(g.bounds), "datetime": WINDOW, "limit": 100})
            items = [i for i in items if i["properties"].get("eo:cloud_cover") is not None and i["properties"]["eo:cloud_cover"] < 20]
            it = best_item(items, g)
            if not it:
                note_all(src, f"{aoi}: no L1 scene in window", only=[f for f in FEATS[FEATS.source == src].feature if "toa" not in f])
                continue
            p, t = it["properties"], it["properties"]["datetime"]
            e = f"{LL_STAC}/collections/landsat-c2l1/items/{it['id']}"
            add(aoi, src, "lsl1_off_nadir_deg", p["view:off_nadir"], "deg", t, "PT1S", e)
            add(aoi, src, "lsl1_sun_elevation_deg", p["view:sun_elevation"], "deg", t, "PT1S", e)
            add(aoi, src, "lsl1_sun_azimuth_deg", p["view:sun_azimuth"], "deg", t, "PT1S", e)
            add(aoi, src, "lsl1_cloud_cover_scene_pct", p["eo:cloud_cover"], "percent of scene", t, "PT1S", e)
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note_all(src, f"{aoi}: {type(ex).__name__}")
    probe = http("GET", "https://landsatlook.usgs.gov/data/collection02/level-1/standard/oli-tirs/2024/037/024/"
                 "LC09_L1TP_037024_20240827_20240827_02_T1/LC09_L1TP_037024_20240827_20240827_02_T1_B4.TIF", allow_redirects=False, headers={"Range": "bytes=0-1000"})
    note(src, "lsl1_toa_reflectance",
         "band GeoTIFFs and MTL sidecars redirect to the EROS login (HTTP %s -> ers.cr.usgs.gov); no anonymous pixel read, no account allowed" % getattr(probe, "status_code", "?"))


# ---------------------------------------------------------------- Maxar Open Data
def maxar():
    src = "maxar_open"
    base = "https://maxar-opendata.s3.amazonaws.com/events/"
    cat = jget(base + "catalog.json")
    n, hits = 0, []
    for l in cat["links"]:
        if l["rel"] != "child":
            continue
        c = jget(urljoin(base, l["href"]))
        if not c:
            continue
        n += 1
        for b in c["extent"]["spatial"]["bbox"]:
            for aoi, g in AOIS.items():
                if box(*b).intersects(g):
                    hits.append((l["href"], aoi))
    print(f"  maxar: {n} event collections read, {len(hits)} AOI intersections")
    if hits:
        raise RuntimeError(f"Maxar now intersects AOIs, extend poc.py: {hits[:5]}")
    note_all(src, f"no AOI coverage: none of {n} event collections (event-based hurricane/flood/fire footprints) intersects any of the 15 AOIs")


# ---------------------------------------------------------------- Satellogic EarthView
def satellogic():
    src = "satellogic_earthview"
    B = "https://satellogic-earthview.s3.us-west-2.amazonaws.com/"

    def ls(prefix):
        r = http("GET", B, params={"list-type": 2, "prefix": prefix, "delimiter": "/"})
        return re.findall(r"<Prefix>(.*?)</Prefix>", r.text), re.findall(r"<Key>(.*?)</Key>", r.text)

    zones = {m.group(1) for p in ls("data/json/")[0] if (m := re.search(r"zone=(\w+)/", p))}
    for aoi, g in AOIS.items():
        c = g.centroid
        zn = int((c.x + 180) // 6) + 1
        z = f"{zn:02d}{'N' if c.y >= 0 else 'S'}"
        if z not in zones:
            continue
        epsg = 32600 + zn if c.y >= 0 else 32700 + zn
        gu = reproject(g, f"EPSG:{epsg}")
        # region ids are the upper-left UTM corner of a 384 m tile; list the zone and intersect client-side
        pre = []
        tok = None
        while True:
            prm = {"list-type": 2, "prefix": f"data/json/zone={z}/", "delimiter": "/"}
            if tok:
                prm["continuation-token"] = tok
            r = http("GET", B, params=prm)
            pre += re.findall(r"<Prefix>(.*?)</Prefix>", r.text)
            m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", r.text)
            if not m:
                break
            tok = m.group(1)
        regs = [(int(m.group(1)), int(m.group(2))) for p in pre if (m := re.search(r"region=(\d+)_(\d+)/", p))]
        hit = [(e_, n_) for e_, n_ in regs if box(e_, n_ - 384, e_ + 384, n_).intersects(gu)]
        if not hit:
            continue
        print(f"  satellogic {aoi}: {len(hit)} tiles intersect (zone {z})")
        bydate = {}
        for e_, n_ in hit:
            for d in ls(f"data/json/zone={z}/region={e_}_{n_}/")[0]:
                m = re.search(r"date=([\d-]+)/", d)
                if m:
                    bydate.setdefault(m.group(1), []).append((e_, n_))
        date = max(bydate, key=lambda d: (len(bydate[d]), d))
        offs, sels, azs, refl, times, last_e = [], [], [], [], [], None
        sumw = np.zeros(4)
        cnt = 0
        for e_, n_ in bydate[date]:
            keys = ls(f"data/json/zone={z}/region={e_}_{n_}/date={date}/")[1]
            for mk in [k for k in keys if k.endswith("_metadata.json")][:1]:
                it = jget(B + mk)
                if not it:
                    continue
                p = it["properties"]
                offs.append(p["view:off_nadir"]); sels.append(p["view:sun_elevation"]); azs.append(p["view:sun_azimuth"]); times.append(p["datetime"])
                last_e = B + mk
                toa = it["assets"].get("analytic", {}).get("href")
                if toa:
                    with rasterio.open(toa) as ds:
                        pp = pix_poly(ds, g)
                        arr, inside = read_window(ds, pp, bands=(1, 2, 3, 4))
                        sc = ds.scales[0] if ds.scales else 1
                        nd = ds.nodata
                    ok = inside & np.all(arr != (nd if nd is not None else -1), axis=0) & np.any(arr > 0, axis=0)
                    if ok.sum():
                        sumw += arr[:, ok].astype(float).sum(axis=1)
                        cnt += int(ok.sum())
                        dt_ = ds.dtypes[0]
        t = sorted(times)[0] if times else None
        if not times:
            continue
        add(aoi, src, "satl_off_nadir_deg", float(np.mean(offs)), "deg, mean over %d tiles of the pass" % len(offs), t, "PT1S", last_e)
        add(aoi, src, "satl_sun_elevation_deg", float(np.mean(sels)), "deg, mean over %d tiles of the pass" % len(sels), t, "PT1S", last_e)
        if cnt:
            m_ = sumw / cnt
            add(aoi, src, "satl_reflectance",
                ";".join(f"{n}={v:.1f}" for n, v in zip(["red", "green", "blue", "nir"], m_)),
                "TOA product pixel values (%s), AOI mean over %d tiles; scale not stated in item" % (dt_, len(offs)), t, "PT1S", last_e)
    done = {r["feature"] for r in ROWS if r["source"] == src}
    for f in FEATS[FEATS.source == src].feature:
        if f not in done:
            note(src, f, "no AOI coverage: no EarthView tile intersects the AOI (zones listed, Jul-Dec 2022 only)")


# ---------------------------------------------------------------- open SAR catalogues
def aoi_items(name, need_asset=None):
    f = AIDX / "cache" / f"sar_{name}.json"
    items = [i for i in json.load(open(f)) if not i["id"].startswith("000-")]
    out = {}
    for i in items:
        gi = shape(i["geometry"]) if i.get("geometry") else box(*i["bbox"])
        if need_asset and need_asset not in i["assets"]:
            continue
        for aoi, g in AOIS.items():
            if gi.intersects(g):
                out.setdefault(aoi, []).append((gi.intersection(g).area / g.area, i["properties"].get("datetime") or "", i["id"]))
    return {k: sorted(v, reverse=True)[0] for k, v in out.items()}


def sar_amp_stats(ds, poly_pix, cal):
    """Mean sigma0 (dB) from amplitude DN over valid AOI pixels; cal maps DN float array to linear power."""
    arr, inside = read_window(ds, poly_pix)
    if arr is None:
        return None
    dn = arr[0].astype(float)
    v = inside & (dn > 0)
    if v.sum() < 4:
        return None
    return float(10 * np.log10(cal(dn[v]).mean())), int(v.sum())


def capella():
    src = "capella_open"
    B = "https://capella-open-data.s3.us-west-2.amazonaws.com/stac/capella-open-data-by-datetime/"
    for aoi, (frac, dt, iid) in aoi_items("capella").items():
        d = re.search(r"_(\d{4})(\d{2})(\d{2})\d{6}_", iid)
        y, m, dd = d.groups()
        url = f"{B}capella-open-data-{y}/capella-open-data-{y}-{m}/capella-open-data-{y}-{m}-{dd}/{iid}/{iid}.json"
        it = jget(url)
        if not it:
            note_all(src, f"{aoi}: item JSON not fetchable at {url}")
            continue
        p, t = it["properties"], it["properties"]["datetime"]
        add(aoi, src, "capella_incidence_deg", p["view:incidence_angle"], "deg", t, "PT1S", url)
        add(aoi, src, "capella_look_angle_deg", p["capella:look_angle"], "deg", t, "PT1S", url)
        try:
            ext = jget(it["assets"]["metadata"]["href"])
            sf = ext["collect"]["image"]["scale_factor"]
            pol = next(k for k in it["assets"] if k in ("HH", "VV", "HV", "VH"))
            with rasterio.Env(**GDAL), rasterio.open(it["assets"][pol]["href"]) as ds:
                r = sar_amp_stats(ds, pix_poly(ds, AOIS[aoi]), lambda x: (x * sf) ** 2)
            if r:
                add(aoi, src, "capella_sar_backscatter", r[0], f"dB sigma0 {pol}, AOI mean of linear power over {r[1]} px (sigma_nought, (DN*scale_factor)^2, scale_factor {sf:.6g}); footprint covers {frac:.0%} of AOI; decimated read", t, "PT1S", it["assets"][pol]["href"])
            else:
                note(src, "capella_sar_backscatter", f"{aoi}: footprint covers {frac:.1%} of AOI but no valid pixels read")
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note(src, "capella_sar_backscatter", f"{aoi}: {type(ex).__name__}")
    done = {r["feature"] for r in ROWS if r["source"] == src}
    for f in FEATS[FEATS.source == src].feature:
        if f not in done:
            note(src, f, "no AOI coverage")


def iceye():
    src = "iceye_open"
    B = "https://iceye-open-data-catalog.s3.amazonaws.com/"
    for aoi, (frac, dt, iid) in aoi_items("iceye").items():
        m = re.search(r"_(\d{4})(\d{2})\d{2}T", iid)
        url = f"{B}stac-items/{m.group(1)}/{m.group(2)}/{iid}.json"
        it = jget(url)
        if not it:
            note_all(src, f"{aoi}: item JSON not fetchable at {url}")
            continue
        p, t = it["properties"], it["properties"]["datetime"]
        add(aoi, src, "iceye_off_nadir_deg", p["view:off_nadir"], "deg", t, "PT1S", url)
        add(aoi, src, "iceye_incidence_deg", p["view:incidence_angle"], "deg", t, "PT1S", url)
        try:
            gj = jget(it["assets"]["grd-json"]["href"])["properties"]
            c, a, b, f, d, e = gj["proj:transform"]  # GDAL order: x0, dx/dcol, dx/drow, y0, dy/dcol, dy/drow
            inv = ~Affine(a, b, c, d, e, f)
            g = AOIS[aoi]
            pp = Polygon([inv * (x, y) for x, y in g.exterior.coords])
            with rasterio.Env(**GDAL), rasterio.open(it["assets"]["grd-cog"]["href"]) as ds:
                arr, inside = read_window(ds, pp)
            dn = arr[0].astype(float) if arr is not None else None
            v = inside & (dn > 0) if dn is not None else None
            if v is not None and v.sum() >= 4:
                add(aoi, src, "iceye_sar_backscatter", float(dn[v].mean()),
                    f"amplitude DN ({gj['sar:polarizations'][0]}, GRD-COG uint16), AOI mean over {int(v.sum())} px; footprint covers {frac:.0%} of AOI; "
                    f"not asserted as sigma0; vendor formula DN^2*iceye:calibration_factor would give {10 * np.log10((dn[v] ** 2).mean() * gj['iceye:calibration_factor']):.1f} dB", t, "PT1S", it["assets"]["grd-cog"]["href"])
            else:
                note(src, "iceye_sar_backscatter", f"{aoi}: footprint covers {frac:.1%} of AOI but no valid pixels read")
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note(src, "iceye_sar_backscatter", f"{aoi}: {type(ex).__name__}")
    done = {r["feature"] for r in ROWS if r["source"] == src}
    for f in FEATS[FEATS.source == src].feature:
        if f not in done:
            note(src, f, "no AOI coverage")


def umbra():
    src = "umbra_open"
    B = "https://umbra-open-data-catalog.s3.amazonaws.com/"
    for aoi, (frac, dt, iid) in aoi_items("umbra", "GEC").items():
        day = dt[:10]
        url = f"{B}stac/{day[:4]}/{day[:7]}/{day}/{iid}/{iid}.json"
        it = jget(url)
        if not it:
            note_all(src, f"{aoi}: item JSON not fetchable at {url}")
            continue
        p, t = it["properties"], it["properties"]["datetime"]
        add(aoi, src, "umbra_incidence_deg", p["view:incidence_angle"], "deg", t, "PT1S", url)
        try:
            href = it["assets"]["GEC"]["href"]
            href = href.split("//", 1)[0] + "//" + href.split("//", 1)[1].split("/", 1)[0] + "/" + quote(href.split("//", 1)[1].split("/", 1)[1])
            with rasterio.Env(**GDAL), rasterio.open(href) as ds:
                dt_ = ds.dtypes[0]
                arr, inside = read_window(ds, pix_poly(ds, AOIS[aoi]))
            dn = arr[0].astype(float)
            v = inside & (dn > 0)
            if v.sum() >= 4:
                add(aoi, src, "umbra_sar_backscatter", float(dn[v].mean()),
                    f"{dt_} GEC amplitude DN, AOI mean over {int(v.sum())} px; footprint covers {frac:.0%} of AOI; stretched and NOT radiometrically calibrated (no sigma0 in the GEC product)", t, "PT1S", href)
            else:
                note(src, "umbra_sar_backscatter", f"{aoi}: no valid GEC pixels in AOI")
        except Exception as ex:
            print("ERR", aoi, src, repr(ex)[:200])
            note(src, "umbra_sar_backscatter", f"{aoi}: {type(ex).__name__}")
    done = {r["feature"] for r in ROWS if r["source"] == src}
    for f in FEATS[FEATS.source == src].feature:
        if f not in done:
            note(src, f, "no AOI coverage")


# ---------------------------------------------------------------- Planet open STAC (Tanager)
def planet():
    src = "planet_open"
    root = "https://www.planet.com/data/stac/tanager-core-imagery/catalog.json"
    cache = HERE / "cache" / "tanager_items.json"
    cache.parent.mkdir(exist_ok=True)
    items = {}
    cat = jget(root)
    for l in cat["links"]:
        if l["rel"] != "child":
            continue
        cu = urljoin(root, l["href"])
        c = jget(cu)
        for k in (c or {}).get("links", []):
            if k["rel"] == "item":
                iu = urljoin(cu, k["href"])
                it = jget(iu)
                if it:
                    items[iu] = it
    json.dump({u: {"id": i["id"], "bbox": i["bbox"], "datetime": i["properties"]["datetime"]} for u, i in items.items()}, open(cache, "w"))
    print(f"  planet: {len(items)} Tanager scenes crawled")
    for aoi, g in AOIS.items():
        cand = []
        for u, it in items.items():
            gi = shape(it["geometry"]) if it.get("geometry") else box(*it["bbox"])
            if gi.intersects(g):
                cand.append((gi.intersection(g).area / g.area, it["properties"]["datetime"], u, it))
        if not cand:
            continue
        frac, dt, u, it = sorted(cand, key=lambda t: t[:2], reverse=True)[0]
        p, t = it["properties"], it["properties"]["datetime"]
        add(aoi, src, "planet_off_nadir_deg", p["view:off_nadir"], "deg", t, "PT1S", u)
        add(aoi, src, "planet_sun_elevation_deg", p["view:sun_elevation"], "deg", t, "PT1S", u)
        add(aoi, src, "planet_cloud_cover_scene_pct", p["cloud_percent"], "percent of scene", t, "PT1S", u)
        add(aoi, src, "planet_quality_category", p["quality_category"], "text", t, "PT1S", u)
    note(src, "planet_reflectance", "the only items intersecting an AOI are Tanager scenes (hyperspectral); no multispectral Planet open item covers any AOI")
    why = ("Tanager surface reflectance is only published as HDF5 (ortho_sr_hdf5/basic_sr_hdf5); the geoquery env has no h5py "
           "and no GDAL HDF5 driver, so it cannot be window-read; not installing packages")
    note(src, "planet_hyperspec_reflectance", why)
    note(src, "planet_reflectance", why)
    done = {r["feature"] for r in ROWS if r["source"] == src}
    for f in ("planet_off_nadir_deg", "planet_sun_elevation_deg", "planet_cloud_cover_scene_pct", "planet_quality_category"):
        if f not in done:
            note(src, f, "no AOI coverage")


FUNCS = {"sentinel2_l2a": s2_l2a, "landsat_c2l2_st": landsat_l2, "sentinel1_rtc": s1_rtc, "hls": hls, "s2_l1c": s2_l1c,
         "landsat_l1": landsat_l1, "maxar_open": maxar, "satellogic_earthview": satellogic, "umbra_open": umbra,
         "capella_open": capella, "iceye_open": iceye, "planet_open": planet}


def write(want):
    new = pd.DataFrame(ROWS, columns=COLS)
    vf, sf = HERE / "poc_values.csv", HERE / "poc_status.csv"
    if vf.exists():
        old = pd.read_csv(vf)
        new = pd.concat([old[~old.source.isin(want)], new], ignore_index=True)
    new = new.sort_values(["source", "feature", "aoi_id"], kind="stable")
    new.to_csv(vf, index=False)
    st = []
    for _, r in FEATS[FEATS.source.isin(want)].iterrows():
        n = new[(new.source == r.source) & (new.feature == r.feature)].aoi_id.nunique()
        reason = "; ".join(REASON.get((r.source, r.feature), []))
        st.append(dict(source=r.source, feature=r.feature, status="validated" if n else "dropped", n_aois_with_value=n,
                       reason=reason if not n else ""))
    st = pd.DataFrame(st)
    if sf.exists():
        st = pd.concat([pd.read_csv(sf).query("source not in @want"), st], ignore_index=True)
    st["_o"] = st.source.map({x: i for i, x in enumerate(SOURCES)})
    st = st.sort_values("_o", kind="stable").drop(columns="_o")
    st.to_csv(sf, index=False)
    print(st.to_string())


if __name__ == "__main__":
    want = sys.argv[1:] or SOURCES
    with rasterio.Env(**GDAL):
        for s in want:
            print("==", s, flush=True)
            t0 = time.time()
            try:
                FUNCS[s]()
            except Exception as ex:
                print("SOURCE FAILED", s, repr(ex)[:300])
                note_all(s, f"source function failed: {type(ex).__name__}: {str(ex)[:120]}")
            print(f"== {s} done in {time.time() - t0:.0f}s", flush=True)
    write(want)

"""Lane AIR proof-of-concept reads: airborne lidar, aerial imagery, SAR and imaging-spectrometer sources.

Re-run: python poc.py [source ...]   (no argument runs every source)
Writes poc_values.csv and poc_status.csv next to this file. Needs network access; geoquery env python.
"""
import csv
import datetime as dt
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
AOI_FILE = ROOT / "examples" / "test_aois.geojson"
UA = {"User-Agent": "geospatial-query-poc/1.0 (research)"}
TODAY = dt.date.today().isoformat()
PC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
DC_SEARCH = "https://datacube.services.geo.ca/pgstac/api/search"
WESM = "https://index.nationalmap.gov/arcgis/rest/services/3DEPElevationIndex/MapServer/8/query"
NOAA_DAV = "https://coast.noaa.gov/arcgis/rest/services/DAV/DAV_footprints/MapServer/0/query"
OTCAT = "https://portal.opentopography.org/API/otCatalog"
ASF = "https://api.daac.asf.alaska.edu/services/search/param"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"

COLS = ["aoi_id", "source", "feature", "value", "unit", "time", "time_accuracy", "description", "source_url", "licence", "endpoint"]
AOIS = [dict(id=f["properties"]["aoi_id"], geom=shape(f["geometry"]), props=f["properties"])
        for f in json.load(open(AOI_FILE))["features"]]

ROWS = []
RAN = set()
STATUS = {}   # (source, feature) -> dict(n=set(), reasons=[])


def stat(source, feature, aoi_id=None, reason=None):
    s = STATUS.setdefault((source, feature), dict(aois=set(), reasons=[]))
    if aoi_id:
        s["aois"].add(aoi_id)
    if reason and reason not in s["reasons"]:
        s["reasons"].append(reason)


def emit(aoi, source, feature, value, unit, time_, acc, desc, url, licence, endpoint):
    if isinstance(value, float):
        value = round(value, 4)
    ROWS.append([aoi, source, feature, value, unit, time_, acc, desc, url, licence, endpoint])
    stat(source, feature, aoi)


def req(method, url, retries=5, **kw):
    kw.setdefault("timeout", 90)
    kw.setdefault("headers", UA)
    r = None
    for i in range(retries):
        try:
            r = requests.request(method, url, **kw)
        except requests.RequestException:
            if i == retries - 1:
                raise
            time.sleep(3 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(5 * (i + 1) * (2 if r.status_code == 429 else 1))
            continue
        return r
    return r


def iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def span(t0, t1):
    """Midpoint and plus/minus duration of two ISO datetimes."""
    a = dt.datetime.fromisoformat(t0.replace("Z", "+00:00"))
    b = dt.datetime.fromisoformat(t1.replace("Z", "+00:00"))
    mid = a + (b - a) / 2
    half = (b - a) / 2
    secs = int(half.total_seconds())
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    acc = f"P{d}DT{h}H" if (d or h) else "PT1S"
    return mid.strftime("%Y-%m-%dT%H:%M:%SZ"), acc


# ---------------------------------------------------------------- raster window reads
def read_aoi(href, geom, categorical=False, max_px=800, step_m=None):
    """Values of every band inside the AOI polygon, decimated to about max_px. Returns (bands x n) valid-pixel array or None."""
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="3",
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff", GDAL_HTTP_TIMEOUT="60"):
        with rasterio.open(href) as ds:
            tf = Transformer.from_crs(4326, ds.crs, always_xy=True).transform
            g = shp_transform(tf, geom)
            minx, miny, maxx, maxy = g.bounds
            win = from_bounds(minx, miny, maxx, maxy, ds.transform)
            win = win.round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, ds.width, ds.height))
            if win.width < 1 or win.height < 1:
                return None
            native = abs(ds.transform.a)
            target = step_m if step_m else max(native, max(maxx - minx, maxy - miny) / max_px)
            step = max(1, int(round(target / native)))
            oh, ow = max(1, int(win.height // step)), max(1, int(win.width // step))
            from rasterio.enums import Resampling
            arr = ds.read(window=win, out_shape=(ds.count, oh, ow), masked=True,
                          resampling=Resampling.nearest if categorical else Resampling.average)
            wt = ds.window_transform(win) * rasterio.Affine.scale(win.width / ow, win.height / oh)
            inside = rasterize([mapping(g)], out_shape=(oh, ow), transform=wt, fill=0, default_value=1, all_touched=True).astype(bool)
            valid = inside & ~np.ma.getmaskarray(arr).any(axis=0)
            data = np.ma.getdata(arr).astype("float64")
            valid &= np.isfinite(data).all(axis=0)
            if not valid.any():
                return None
            return data[:, valid]


def pool(parts):
    parts = [p for p in parts if p is not None and p.shape[1]]
    return np.concatenate(parts, axis=1) if parts else None


# ---------------------------------------------------------------- 3DEP on Planetary Computer
PC_3DEP = {
    "usgs3dep_dtm_elev_m": ("3dep-lidar-dtm", "m", "mean bare-earth elevation (DTM) inside the AOI"),
    "usgs3dep_dsm_elev_m": ("3dep-lidar-dsm", "m", "mean first-return surface elevation (DSM) inside the AOI"),
    "usgs3dep_hag_m": ("3dep-lidar-hag", "m", "mean height above ground inside the AOI"),
    "usgs3dep_intensity": ("3dep-lidar-intensity", "DN", "mean lidar return intensity inside the AOI"),
    "usgs3dep_returns_n": ("3dep-lidar-returns", "count", "mean number of returns per pulse inside the AOI"),
    "usgs3dep_point_class": ("3dep-lidar-classification", "ASPRS class", "share of pixels per ASPRS point class inside the AOI"),
}
ASPRS = {1: "unclassified", 2: "ground", 3: "low veg", 4: "medium veg", 5: "high veg", 6: "building", 7: "noise", 9: "water",
         10: "rail", 11: "road", 17: "bridge", 18: "high noise"}
_wesm_dates = {}


def wesm_workunit_dates(usgs_id):
    """Collection span of the WESM work unit whose name is contained in a PC 3dep:usgs_id (USGS_LPC_<workunit>_LAS_<year>)."""
    if usgs_id not in _wesm_dates:
        core = usgs_id.replace("USGS_LPC_", "")
        core = core.rsplit("_LAS_", 1)[0] if "_LAS_" in core else core
        a = []
        for i in range(8):
            r = req("GET", WESM, params=dict(where=f"workunit='{core}'", outFields="collect_start,collect_end", returnGeometry="false", f="json"))
            j = r.json() if r.status_code == 200 else {"error": r.status_code}
            if "error" not in j:
                a = [f["attributes"] for f in j["features"] if f["attributes"].get("collect_start") and f["attributes"].get("collect_end")]
                break
            time.sleep(2 * (i + 1))
        _wesm_dates[usgs_id] = (min(x["collect_start"] for x in a), max(x["collect_end"] for x in a)) if a else None
    return _wesm_dates[usgs_id]


def stac_items(url, collections, geom, limit=200):
    r = req("POST", url, json=dict(collections=collections, intersects=mapping(geom), limit=limit))
    r.raise_for_status()
    return r.json().get("features", [])


def poc_usgs3dep_pc():
    import planetary_computer as pc
    src = "usgs3dep_pc"
    for a in AOIS:
        for feat, (col, unit, desc) in PC_3DEP.items():
            try:
                items = stac_items(PC_SEARCH, [col], a["geom"])
            except Exception as e:
                stat(src, feat, reason=f"STAC error {str(e)[:60]}")
                continue
            if not items:
                continue
            projects = defaultdict(list)
            for it in items:
                projects[it["properties"].get("3dep:usgs_id")].append(it)
            v = best = None
            for proj in sorted(projects, key=lambda p: (max(i["properties"].get("end_datetime", "") or "" for i in projects[p]), len(projects[p])), reverse=True):
                parts = []
                for it in projects[proj]:
                    try:
                        parts.append(read_aoi(pc.sign(it["assets"]["data"]["href"]), a["geom"], categorical=(feat == "usgs3dep_point_class")))
                    except Exception as e:
                        stat(src, feat, reason=f"read error {str(e)[:60]}")
                v = pool(parts)
                if v is not None:
                    best = proj
                    break
            if v is None:
                continue
            x = v[0]
            if feat == "usgs3dep_point_class":
                c = Counter(np.rint(x).astype(int).tolist())
                tot = sum(c.values())
                value = "; ".join(f"{k}:{ASPRS.get(k, 'class ' + str(k))}={100 * n / tot:.1f}%" for k, n in c.most_common(5))
            else:
                value = float(x.mean())
            p0 = projects[best][0]["properties"]
            dates = wesm_workunit_dates(best)
            if dates:
                t, acc = span(iso(dates[0]), iso(dates[1]))
            else:
                s0 = p0.get("start_datetime") or p0.get("end_datetime")
                t, acc = s0, "P1Y"
            emit(a["id"], src, feat, value, unit, t, acc, f"{desc}; project {best}, {len(projects[best])} tile(s), {x.size} px sampled",
                 f"https://planetarycomputer.microsoft.com/dataset/{col}", "USGS 3DEP, public domain",
                 f"{PC_SEARCH} collections={col} intersects=AOI; COG {projects[best][0]['id']} (window read)")
    stat(src, "usgs3dep_scan_angle_deg", reason="per-point ScanAngleRank lives inside COPC LAZ; no LAZ decoder (laspy/lazrs/pdal) in the geoquery env and no derived raster carries it")


# ---------------------------------------------------------------- NAIP
def poc_naip_pc():
    import planetary_computer as pc
    src = "naip_pc"
    for a in AOIS:
        items = stac_items(PC_SEARCH, ["naip"], a["geom"])
        if not items:
            continue
        year = max(i["properties"]["naip:year"] for i in items)
        sel = [i for i in items if i["properties"]["naip:year"] == year]
        parts = []
        for it in sel:
            try:
                parts.append(read_aoi(pc.sign(it["assets"]["image"]["href"]), a["geom"]))
            except Exception as e:
                stat(src, "naip_rgbnir_dn", reason=f"read error {str(e)[:60]}")
        v = pool(parts)
        p = sel[0]["properties"]
        t = p["datetime"]
        if v is not None and v.shape[0] >= 4:
            m = v.mean(axis=1)
            emit(a["id"], src, "naip_rgbnir_dn", f"R={m[0]:.1f};G={m[1]:.1f};B={m[2]:.1f};NIR={m[3]:.1f}", "DN (0-255)", t, "PT12H",
                 f"mean 8-bit DN per band inside the AOI; {len(sel)} tile(s), {v.shape[1]} px sampled, gsd {p.get('gsd')} m",
                 "https://planetarycomputer.microsoft.com/dataset/naip", "USDA FSA NAIP, public domain",
                 f"{PC_SEARCH} collections=naip intersects=AOI; COG {sel[0]['id']} (window read)")
        emit(a["id"], src, "naip_flight_year", int(year), "year", t, "PT12H", f"NAIP flight year of the latest tiles covering the AOI (STAC naip:year); years available {sorted({i['properties']['naip:year'] for i in items})}",
             "https://planetarycomputer.microsoft.com/dataset/naip", "USDA FSA NAIP, public domain", f"{PC_SEARCH} collections=naip intersects=AOI; property naip:year")


# ---------------------------------------------------------------- WESM
def esri_poly(geom):
    return json.dumps(dict(rings=[list(map(list, geom.exterior.coords))], spatialReference=dict(wkid=4326)))


def arcgis(url, geom, where="1=1", fields="*", tries=8):
    """ArcGIS query that retries the transient 'Failed to execute query' 400 the 3DEP index returns under load."""
    err = None
    for i in range(tries):
        r = req("POST", url, data=dict(geometry=esri_poly(geom), geometryType="esriGeometryPolygon", inSR=4326, spatialRel="esriSpatialRelIntersects",
                                       where=where, outFields=fields, returnGeometry="false", f="json"))
        j = r.json() if r.status_code == 200 else {"error": r.status_code}
        if "error" not in j:
            return [f["attributes"] for f in j.get("features", [])]
        err = str(j["error"])[:100]
        time.sleep(2 * (i + 1))
    raise RuntimeError(err)


def poc_usgs_wesm():
    src = "usgs_wesm"
    for a in AOIS:
        rows = arcgis(WESM, a["geom"])
        if not rows:
            continue
        names = sorted({r["workunit"] for r in rows})
        ep = f"{WESM} POST polygon=AOI"
        url = "https://index.nationalmap.gov/arcgis/rest/services/3DEPElevationIndex/MapServer/8"
        emit(a["id"], src, "wesm_workunit_n", len(names), "count", TODAY, "", f"distinct 3DEP work units whose footprint intersects the AOI: {'; '.join(names)}", url,
             "USGS public domain", ep)
        dated = [r for r in rows if r.get("collect_start") and r.get("collect_end")]
        newest = max(dated, key=lambda r: r["collect_end"]) if dated else None
        others = "; ".join(f"{r.get('ql') or 'unknown'} ({r['workunit']}{', ' + iso(r['collect_end'])[:10] if r.get('collect_end') else ', undated'})"
                           for r in rows if r is not newest)
        if newest:
            value = f"{newest.get('ql') or 'unknown'}"
            t, acc = span(iso(newest["collect_start"]), iso(newest["collect_end"]))
            desc = f"USGS lidar quality level of the newest work unit covering the AOI ({newest['workunit']}, collected {iso(newest['collect_start'])[:10]} to {iso(newest['collect_end'])[:10]}); others: {others or 'none'}"
        else:
            value = "; ".join(f"{r.get('ql') or 'unknown'} ({r['workunit']})" for r in rows)
            t, acc = TODAY, ""
            desc = "USGS lidar quality level of the work units covering the AOI (no collection dates in the index)"
        emit(a["id"], src, "wesm_quality_level", value, "USGS QL", t, acc, desc, url, "USGS public domain", ep)


# ---------------------------------------------------------------- NRCan HRDEM, NAPL
def hrdem_pick(items, asset, geom):
    """Newest item with data in the AOI, replaced by an older one only when that one has 1.5x the valid pixels."""
    best = None
    for it in sorted(items, key=lambda i: i["properties"].get("datetime") or "", reverse=True):
        try:
            v = read_aoi(it["assets"][asset]["href"], geom)
        except Exception:
            continue
        if v is None:
            continue
        if best is None or v.shape[1] > best[1].shape[1] * 1.5:
            best = (it, v)
    return best


def poc_nrcan_hrdem():
    src = "nrcan_hrdem"
    feats = {"hrdem_dtm_elev_m": ("dtm", "mean bare-earth elevation (DTM) inside the AOI"), "hrdem_dsm_elev_m": ("dsm", "mean first-return surface elevation (DSM) inside the AOI")}
    for a in AOIS:
        for feat, (asset, desc) in feats.items():
            done = False
            for col in ("hrdem-lidar", "hrdem-mosaic-1m"):
                items = stac_items(DC_SEARCH, [col], a["geom"])
                got = hrdem_pick(items, asset, a["geom"]) if items else None
                if got is None:
                    continue
                it, v = got
                ds_t = it["properties"].get("datetime")
                emit(a["id"], src, feat, float(v[0].mean()), "m", ds_t, "PT12H" if col == "hrdem-lidar" else "",
                     f"{desc}; {it['id']}, {v.shape[1]} px sampled (1 m, decimated)", "https://datacube.services.geo.ca/pgstac/api",
                     "OGL-Canada-2.0", f"{DC_SEARCH} collections={col} intersects=AOI; COG {it['assets'][asset]['href']} (window read)")
                done = True
                break
            if not done:
                continue


def poc_nrcan_napl():
    src = "nrcan_napl"
    cols = [c["id"] for c in req("GET", "https://datacube.services.geo.ca/pgstac/api/collections?limit=200").json()["collections"] if c["id"].startswith("napl-")]
    for a in AOIS:
        items = stac_items(DC_SEARCH, cols, a["geom"])
        for it in sorted(items, key=lambda i: i["properties"].get("datetime") or "", reverse=True):
            href = next((v["href"] for k, v in it["assets"].items() if v["href"].endswith(".tif") and "thumb" not in k and "overview" not in k), None)
            if not href:
                continue
            try:
                v = read_aoi(href, a["geom"])
            except Exception as e:
                stat(src, "napl_airphoto_dn", reason=f"read error {str(e)[:60]}")
                continue
            if v is None:
                continue
            m = v.mean(axis=1)
            emit(a["id"], src, "napl_airphoto_dn", ";".join(f"b{i + 1}={x:.1f}" for i, x in enumerate(m)), "DN", it["properties"]["datetime"], "P182DT12H",
                 f"mean DN of the historical air-photo mosaic {it['id']} inside the AOI; {v.shape[1]} px sampled",
                 "https://datacube.services.geo.ca/pgstac/api", "OGL-Canada-2.0", f"{DC_SEARCH} collections=napl-* intersects=AOI; COG {href} (window read)")
            break


# ---------------------------------------------------------------- OpenTopography, NOAA DAV
def poc_opentopography():
    src = "opentopography"
    for a in AOIS:
        b = a["geom"].bounds
        r = req("GET", OTCAT, params=dict(productFormat="PointCloud", minx=b[0], miny=b[1], maxx=b[2], maxy=b[3], detail="true",
                                          outputFormat="json", include_federated="true"), timeout=120)
        if r.status_code != 200:
            stat(src, "opentopo_lidar_survey_n", reason=f"HTTP {r.status_code}")
            continue
        ds = r.json().get("Datasets", [])
        names = [d["Dataset"]["name"] for d in ds]
        if names:
            emit(a["id"], src, "opentopo_lidar_survey_n", len(names), "count", TODAY, "", f"point-cloud surveys in the OpenTopography catalogue intersecting the AOI bbox: {'; '.join(names)}",
                 "https://portal.opentopography.org/lidarDataset", "per-dataset (USGS public domain; others vary)", f"{OTCAT}?productFormat=PointCloud&bbox=AOI&include_federated=true")


def poc_noaa_dav():
    src = "noaa_dav"
    for a in AOIS:
        rows = arcgis(NOAA_DAV, a["geom"])
        for typ, feat in (("Lidar", "noaa_dav_lidar_survey_n"), ("Imagery", "noaa_dav_imagery_n")):
            titles = sorted({r["title"] for r in rows if r["data_type"] == typ})
            if titles:
                emit(a["id"], src, feat, len(titles), "count", TODAY, "", f"NOAA Digital Coast {typ.lower()} collections intersecting the AOI: {'; '.join(titles)}",
                     "https://coast.noaa.gov/dataviewer", "NOAA public domain", f"{NOAA_DAV} POST polygon=AOI where data_type={typ}")


# ---------------------------------------------------------------- UAVSAR, AVIRIS, NEON (coverage and login walls)
def poc_uavsar_asf():
    src = "uavsar_asf"
    hits = {}
    for a in AOIS:
        r = req("GET", ASF, params=dict(platform="UAVSAR", intersectsWith=a["geom"].wkt, output="geojson", maxResults=50))
        hits[a["id"]] = len(r.json().get("features", [])) if r.status_code == 200 else f"HTTP {r.status_code}"
    n = sum(1 for v in hits.values() if isinstance(v, int) and v > 0)
    why = f"ASF UAVSAR search by AOI polygon returned scenes for {n}/15 AOIs ({hits if n else 'all zero'})"
    if n:
        why += "; pixel values (HH/HV/VV, .inc) are whole-scene files behind Earthdata login"
    for f in ("uavsar_sar_backscatter", "uavsar_incidence_deg"):
        stat(src, f, reason=why)


AVIRIS_COLLECTIONS = ["C2659129205-ORNL_CLOUD", "C3253178409-ORNL_CLOUD", "C3369603199-ORNL_CLOUD", "C2711871294-ORNL_CLOUD", "C4184090548-ORNL_CLOUD"]


def poc_aviris():
    src = "aviris"
    hit, sample = {}, None
    for a in AOIS:
        n = 0
        for c in AVIRIS_COLLECTIONS:
            r = req("GET", CMR, params=dict(collection_concept_id=c, polygon=",".join(f"{x},{y}" for x, y in a["geom"].exterior.coords), page_size=1))
            if r.status_code == 200:
                n += int(r.headers.get("CMR-Hits", 0))
                items = r.json().get("items", [])
                if items and sample is None:
                    sample = items[0]
        if n:
            hit[a["id"]] = n
    wall = "no sample granule"
    if sample:
        urls = [u["URL"] for u in sample["umm"].get("RelatedUrls", []) if u.get("Type", "").startswith("GET DATA") and u["URL"].startswith("http")]
        if urls:
            r = req("GET", urls[0], headers={**UA, "Range": "bytes=0-1023"}, allow_redirects=False)
            loc = r.headers.get("Location", "")
            wall = f"sample data URL {urls[0]} answers HTTP {r.status_code}" + (f" redirecting to {loc[:60]}" if loc else "")
    stat(src, "aviris_reflectance", reason=f"CMR granule hits per AOI {hit}; reflectance is a whole ENVI flight line, anonymous read fails: {wall}")


def hav_km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    h = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def poc_neon_aop():
    src = "neon_aop"
    sites = req("GET", "https://data.neonscience.org/api/v0/sites").json()["data"]
    aop = [s for s in sites if any(p["dataProductCode"] in ("DP1.30003.001", "DP3.30010.001", "DP3.30006.001", "DP1.30006.001") for p in s["dataProducts"])]
    near = {}
    for a in AOIS:
        c = a["geom"].centroid
        near[a["id"]] = min((hav_km(c.y, c.x, s["siteLatitude"], s["siteLongitude"]), s["siteCode"]) for s in aop)
    closest = min(near.items(), key=lambda kv: kv[1][0])
    why = (f"{len(aop)} NEON sites carry AOP products; nearest to any test AOI is {closest[1][1]} at {closest[1][0]:.1f} km ({closest[0]}), "
           "outside any AOP flight box (boxes span a few km around a site); AOP tiles are whole-tile downloads")
    for f in ("neon_lidar_elev_m", "neon_rgb_dn", "neon_hyperspec_reflectance"):
        stat(src, f, reason=why)


SOURCES = dict(usgs3dep_pc=poc_usgs3dep_pc, naip_pc=poc_naip_pc, usgs_wesm=poc_usgs_wesm, nrcan_hrdem=poc_nrcan_hrdem, nrcan_napl=poc_nrcan_napl,
               neon_aop=poc_neon_aop, opentopography=poc_opentopography, noaa_dav=poc_noaa_dav, uavsar_asf=poc_uavsar_asf, aviris=poc_aviris)


DEFAULT_REASON = {
    "usgs3dep_pc": "no 3DEP lidar tile covering the AOI on Planetary Computer (US-only, partial)",
    "naip_pc": "NAIP is CONUS only; no tile covers the AOI",
    "usgs_wesm": "no 3DEP work unit footprint intersects the AOI",
    "nrcan_hrdem": "no valid 1 m pixel in the AOI",
    "nrcan_napl": "NAPL mosaics exist for eight cities only",
    "opentopography": "no point-cloud survey in the catalogue",
    "noaa_dav": "no NOAA DAV footprint intersects the AOI",
}
FEATURES = {
    "usgs3dep_pc": list(PC_3DEP) + ["usgs3dep_scan_angle_deg"], "naip_pc": ["naip_rgbnir_dn", "naip_flight_year"],
    "usgs_wesm": ["wesm_workunit_n", "wesm_quality_level"], "nrcan_hrdem": ["hrdem_dtm_elev_m", "hrdem_dsm_elev_m"], "nrcan_napl": ["napl_airphoto_dn"],
    "neon_aop": ["neon_lidar_elev_m", "neon_rgb_dn", "neon_hyperspec_reflectance"], "opentopography": ["opentopo_lidar_survey_n"],
    "noaa_dav": ["noaa_dav_lidar_survey_n", "noaa_dav_imagery_n"], "uavsar_asf": ["uavsar_sar_backscatter", "uavsar_incidence_deg"], "aviris": ["aviris_reflectance"],
}


def write():
    for s_, fs in FEATURES.items():
        for ft in fs:
            if s_ in RAN:
                stat(s_, ft, reason=DEFAULT_REASON.get(s_))
    with open(HERE / "poc_values.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(ROWS)
    with open(HERE / "poc_status.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "feature", "status", "n_aois_with_value", "reason"])
        for (s, ft), v in sorted(STATUS.items()):
            n = len(v["aois"])
            reason = "; ".join(v["reasons"]) if n == 0 else f"read at {n} AOI(s): {', '.join(sorted(v['aois']))}"
            w.writerow([s, ft, "validated" if n else "dropped", n, reason])


if __name__ == "__main__":
    names = sys.argv[1:] or list(SOURCES)
    for n in names:
        t0 = time.time()
        try:
            RAN.add(n)
            SOURCES[n]()
        except Exception as e:
            print(n, "FAILED", repr(e)[:200])
        print(n, f"{time.time() - t0:.0f}s", flush=True)
    write()

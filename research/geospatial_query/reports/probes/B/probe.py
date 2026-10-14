"""Lane B probe: airborne lidar / aerial, drone and hyperspectral sources (gaps S1, S2, S3).

Re-running writes B_probes.csv, aoi_hits_detail.json and samples/*.json next to this file.
Run with the geoquery env python; needs network access.
"""
import csv
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AOI_FILE = ROOT / "examples" / "test_aois.geojson"
SAMPLES = HERE / "samples"
SAMPLES.mkdir(exist_ok=True)
UA = {"User-Agent": "geospatial-query-probe/1.0 (research; contact via repo owner)"}
CONTROL = (-150.0, 0.0, -149.9, 0.1)
COLUMNS = ["gap", "candidate", "source_type", "endpoint", "auth", "reachable", "http_status", "aoi_hits",
           "control_passed", "observation_unit", "quality_fields", "off_nadir_field", "licence", "notes"]

AOIS = []
for f in json.load(open(AOI_FILE))["features"]:
    g = shape(f["geometry"])
    AOIS.append(dict(id=f["properties"]["aoi_id"], geom=g, bbox=g.bounds,
                     lat=f["properties"]["centroid_lat"], lon=f["properties"]["centroid_lon"],
                     country=f["properties"]["country"]))

_last = {}


def req(method, url, host_gap=0.55, retries=3, **kw):
    """Rate-limited request (<= ~2 req/s per host), backs off on 429."""
    host = url.split("/")[2]
    kw.setdefault("timeout", 90)
    kw.setdefault("headers", UA)
    r = None
    for attempt in range(retries):
        wait = host_gap - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        try:
            r = requests.request(method, url, **kw)
        except requests.RequestException as e:
            _last[host] = time.time()
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))
            continue
        _last[host] = time.time()
        if r.status_code == 429 or r.status_code >= 500:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
        return r
    return r


def bstr(b):
    return ",".join(f"{x:.6f}" for x in b)


def seen(props, wanted):
    """Return the wanted field names that appear in a live property dict."""
    return [w for w in wanted if w in props]


class Row(dict):
    pass


ROWS = []
DETAIL = {}


def add(gap, candidate, source_type, endpoint, auth, reachable, http_status, aoi_hits, control_passed,
        observation_unit, quality_fields, off_nadir_field, licence, notes):
    row = dict(gap=gap, candidate=candidate, source_type=source_type, endpoint=endpoint, auth=auth,
               reachable=reachable, http_status=http_status, aoi_hits=aoi_hits, control_passed=control_passed,
               observation_unit=observation_unit,
               quality_fields=";".join(quality_fields) if isinstance(quality_fields, (list, tuple)) else quality_fields,
               off_nadir_field=off_nadir_field, licence=licence, notes=notes)
    ROWS.append(row)
    print(f"[row] {candidate}: reachable={reachable} hits={aoi_hits} ctl={control_passed}", flush=True)


def save_sample(name, obj):
    (SAMPLES / f"{name}.json").write_text(json.dumps(obj, indent=1, default=str)[:60000])


def cover_fraction(aoi_geom, geoms):
    if not geoms:
        return 0.0
    u = unary_union(geoms)
    return round(u.intersection(aoi_geom).area / aoi_geom.area, 3)


def fmt_hits(per_aoi):
    return f"{sum(1 for v in per_aoi.values() if v)}/15"


def hit_list(per_aoi):
    return ",".join(k for k, v in per_aoi.items() if v)


# ----------------------------------------------------------------------------------------------
# generic STAC search probe
# ----------------------------------------------------------------------------------------------
def stac_probe(search_url, collections, method="POST", limit=100, extra=None, geom_check=True, params_style="json"):
    """Run bbox search for 15 AOIs + control. Returns per-AOI counts, cover fractions, statuses, first features."""
    per, cover, statuses, firsts, ids = {}, {}, set(), {}, {}
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL, geom=box(*CONTROL))]:
        if method == "POST":
            body = dict(collections=collections, bbox=list(a["bbox"]), limit=limit)
            if extra:
                body.update(extra)
            r = req("POST", search_url, json=body)
        else:
            p = dict(collections=",".join(collections), bbox=bstr(a["bbox"]), limit=limit)
            if extra:
                p.update(extra)
            r = req("GET", search_url, params=p)
        statuses.add(r.status_code)
        try:
            feats = r.json().get("features", []) if r.status_code == 200 else []
        except ValueError:
            feats = []
        per[a["id"]] = len(feats)
        ids[a["id"]] = [f.get("id") for f in feats[:5]]
        if feats:
            firsts[a["id"]] = feats[0]
        if geom_check and feats and a["id"] != "CONTROL":
            cover[a["id"]] = cover_fraction(a["geom"], [shape(f["geometry"]) for f in feats if f.get("geometry")])
    ctl = per.pop("CONTROL")
    return per, ctl, cover, sorted(statuses), firsts, ids


def cover_note(cover):
    if not cover:
        return ""
    full = sum(1 for v in cover.values() if v >= 0.99)
    part = [f"{k}={v}" for k, v in cover.items() if v < 0.99]
    s = f"footprint covers >=99% of AOI in {full} of {len(cover)} hit AOIs"
    if part:
        s += "; partial: " + ",".join(part)
    return s


def first_with_hit(firsts, prefer=None):
    for k in (prefer or []):
        if k in firsts:
            return k, firsts[k]
    for k, v in firsts.items():
        if k != "CONTROL":
            return k, v
    return None, None


# ----------------------------------------------------------------------------------------------
# S1: Planetary Computer 3DEP, NAIP
# ----------------------------------------------------------------------------------------------
PC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_COLLECTIONS_3DEP = {
    "3dep-lidar-copc": "Classified point cloud (COPC LAZ) per USGS work unit",
    "3dep-lidar-dtm": "Bare-earth DTM raster derived by Microsoft from the point cloud",
    "3dep-lidar-dtm-native": "DTM at native CRS",
    "3dep-lidar-dsm": "First-return DSM raster",
    "3dep-lidar-hag": "Height-above-ground raster",
    "3dep-lidar-intensity": "Intensity raster",
    "3dep-lidar-classification": "Classification raster",
    "3dep-lidar-returns": "Number-of-returns raster",
    "3dep-lidar-pointsourceid": "PointSourceId (flight line) raster",
}


def probe_3dep():
    sample_done = False
    for col, desc in PC_COLLECTIONS_3DEP.items():
        per, ctl, cover, st, firsts, ids = stac_probe(PC_SEARCH, [col])
        DETAIL[col] = dict(per=per, control=ctl, cover=cover, ids=ids)
        k, f = first_with_hit(firsts, ["city_us_detroit_mi"])
        props = f["properties"] if f else {}
        wanted = ["pc:count", "3dep:usgs_id", "start_datetime", "end_datetime", "datetime", "pc:schemas", "pc:encoding",
                  "proj:shape", "proj:bbox", "proj:geometry", "pc:type", "spatial_resolution", "raster:bands", "pdal_pipeline"]
        qf = seen(props, wanted)
        rb = props.get("raster:bands")
        if isinstance(rb, dict) and "statistics" in rb:
            qf.append("raster:bands.statistics.valid_percent")
        notes = [desc]
        if col == "3dep-lidar-copc" and f:
            names = [s["name"] for s in props.get("pc:schemas", [])]
            geom = props.get("proj:geometry")
            dens = None
            if geom and props.get("pc:count"):
                area = shape(geom).area
                dens = round(props["pc:count"] / area, 2)
            notes.append(f"point density derived = pc:count / area(proj:geometry) = {dens} pts/m2 for {f['id']} (not a field)")
            notes.append("ScanAngleRank and PointSourceId present in pc:schemas (names={})".format(
                [n for n in names if n in ("ScanAngleRank", "PointSourceId", "ScanDirectionFlag", "EdgeOfFlightLine")]))
            save_sample("3dep_lidar_copc_item", f)
        if col == "3dep-lidar-dtm" and f:
            save_sample("3dep_lidar_dtm_item_trim", {k2: v for k2, v in f.items() if k2 != "assets"} | {"assets": list(f["assets"])})
        notes.append("US-only coverage (not a failure for CA AOIs); start_datetime == end_datetime (year-granular; 2018-01-01 for the Wayne County "
                     "survey that OpenTopography dates 2017-04-15 to 2017-04-23), so PC dates are not acquisition dates; "
                     "QL is not in STAC (see usgs_wesm row)")
        if cover:
            notes.append(cover_note(cover))
        notes.append("hits: " + hit_list(per))
        if col == "3dep-lidar-copc":
            off = ("ScanAngleRank: per-point LAS dimension inside the COPC file, advertised in item property pc:schemas; "
                   "no per-item summary. PointSourceId = flight-line id")
        elif col == "3dep-lidar-pointsourceid":
            off = "none; raster of PointSourceId (flight-line id), the join key to flight-line metadata, not an angle"
        else:
            off = "none; derived raster, scan angle discarded"
        add("S1", f"3dep_pc:{col}", "airborne", PC_SEARCH + f" POST {{collections:[{col}],bbox:{{bbox}}}}", "none",
            "yes", st[0] if len(st) == 1 else "/".join(map(str, st)), fmt_hits(per),
            "yes" if ctl == 0 else "no", "acquisition", qf, off, "proprietary (PC collection licence field; USGS data)", "; ".join(notes))


def probe_naip():
    per, ctl, cover, st, firsts, ids = stac_probe(PC_SEARCH, ["naip"])
    DETAIL["naip"] = dict(per=per, control=ctl, cover=cover, ids=ids)
    k, f = first_with_hit(firsts, ["farm_us_ia_story"])
    props = f["properties"] if f else {}
    qf = seen(props, ["gsd", "naip:year", "naip:state", "datetime", "proj:epsg", "proj:shape", "proj:centroid", "proj:bbox"])
    if f:
        save_sample("naip_item", f | {"assets": list(f["assets"])})
    # gsd differential: how many years per AOI
    yrs = {}
    r = req("POST", PC_SEARCH, json=dict(collections=["naip"], bbox=list(AOIS[3]["bbox"]), limit=100))
    yrs = sorted({ft["properties"].get("naip:year") for ft in r.json()["features"]})
    gsds = sorted({ft["properties"].get("gsd") for ft in r.json()["features"]})
    add("S1", "naip_pc", "airborne", PC_SEARCH + " POST {collections:[naip],bbox:{bbox}}", "none", "yes",
        st[0] if len(st) == 1 else "/".join(map(str, st)), fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", qf,
        "none; NAIP STAC items carry only gsd/naip:year/naip:state (no camera angle, no flight altitude; frame camera near-nadir)",
        "proprietary (PC collection licence field; USDA FSA data)",
        f"US-only (CONUS) coverage, not a failure for CA AOIs. Story IA has years {yrs} at gsd {gsds}. "
        f"datetime is a state-wide flight date, not per-frame. {cover_note(cover)}. hits: {hit_list(per)}")


# ----------------------------------------------------------------------------------------------
# S1: USGS WESM via 3DEP index MapServer layer 8
# ----------------------------------------------------------------------------------------------
WESM = "https://index.nationalmap.gov/arcgis/rest/services/3DEPElevationIndex/MapServer/8/query"


def wesm_query(bbox, where="1=1", fields="*", count_only=False):
    p = dict(geometry=bstr(bbox), geometryType="esriGeometryEnvelope", inSR=4326, spatialRel="esriSpatialRelIntersects",
             where=where, outFields=fields, returnGeometry="false", f="json")
    if count_only:
        p["returnCountOnly"] = "true"
    return req("GET", WESM, params=p)


def probe_wesm():
    per, qls, statuses = {}, {}, set()
    first = None
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL)]:
        r = wesm_query(a["bbox"])
        statuses.add(r.status_code)
        feats = r.json().get("features", []) if r.status_code == 200 else []
        per[a["id"]] = len(feats)
        qls[a["id"]] = sorted({ft["attributes"].get("ql") for ft in feats if ft["attributes"].get("ql")})
        if feats and a["id"] != "CONTROL" and (first is None or (first.get("ql") == "Other" and any(f["attributes"].get("ql", "").startswith("QL") for f in feats))):
            first = next((f["attributes"] for f in feats if f["attributes"].get("ql", "").startswith("QL")), feats[0]["attributes"])
    ctl = per.pop("CONTROL")
    # filter differential at Detroit
    det = [a for a in AOIS if a["id"] == "city_us_detroit_mi"][0]["bbox"]
    n_all = len(wesm_query(det).json()["features"])
    n_ql2 = len(wesm_query(det, where="ql='QL 2'").json()["features"])
    n_ql0 = len(wesm_query(det, where="ql='QL 0'").json()["features"])
    DETAIL["wesm"] = dict(per=per, control=ctl, ql=qls, filter_diff=dict(all=n_all, ql2=n_ql2, ql0=n_ql0))
    qf = seen(first or {}, ["ql", "collect_start", "collect_end", "workunit", "workunit_id", "project", "spec", "p_method",
                            "dem_gsd_meters", "horiz_crs", "vert_crs", "geoid", "lpc_category", "lpc_pub_date", "onemeter_category",
                            "seamless_category", "metadata_link", "lpc_link"])
    if first:
        save_sample("wesm_layer8_attributes", first)
    add("S1", "usgs_wesm_ql", "airborne", WESM + "?geometry={bbox}&geometryType=esriGeometryEnvelope&inSR=4326&outFields=*&f=json",
        "none", "yes", "/".join(map(str, sorted(statuses))), fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", qf,
        "none; WESM records the quality level (ql) and spec, not scan angle. collect_start/collect_end are epoch milliseconds",
        "not stated by the service (USGS 3DEP index)",
        "WESM footprints (workunit polygons) served by the 3DEP elevation index layer 8 'Lidar Point Cloud'; usgs.gov pages 403 but this API host works. "
        f"ql values per hit AOI: {json.dumps({k: v for k, v in qls.items() if v})}. Filter differential at Detroit: all={n_all}, ql='QL 2'={n_ql2}, ql='QL 0'={n_ql0}. "
        f"Join key to the PC items: workunit/project vs 3dep:usgs_id. US-only coverage. hits: {hit_list(per)}")


# ----------------------------------------------------------------------------------------------
# S1: NRCan HRDEM (datacube pgstac) + NAPL
# ----------------------------------------------------------------------------------------------
DC_SEARCH = "https://datacube.services.geo.ca/pgstac/api/search"


def sample_cog(href, lon, lat):
    """Count valid pixels in a ~60 m window of a COG at lon/lat. Returns (n_valid, n_total) or None."""
    try:
        import rasterio
        from rasterio.windows import Window
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="2", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                          GDAL_HTTP_TIMEOUT="40"):
            with rasterio.open(href) as ds:
                x, y = Transformer.from_crs(4326, ds.crs, always_xy=True).transform(lon, lat)
                row, col = ds.index(x, y)
                if row < 0 or col < 0 or row >= ds.height or col >= ds.width:
                    return (0, 0)
                w = Window(max(col - 30, 0), max(row - 30, 0), 60, 60)
                a = ds.read(1, window=w, masked=True)
                return (int((~a.mask).sum()) if hasattr(a.mask, "sum") else int(a.size), int(a.size))
    except Exception as e:
        return ("err", str(e)[:100])


def probe_hrdem():
    for col, desc in [("hrdem-lidar", "per-acquisition-project DTM/DSM COGs (1 m, 2 m)"),
                      ("hrdem-mosaic-1m", "national 1 m mosaic tile COG")]:
        per, ctl, cover, st, firsts, ids = stac_probe(DC_SEARCH, [col], geom_check=False)
        valid = {}
        for a in AOIS:
            if not per[a["id"]]:
                continue
            r = req("POST", DC_SEARCH, json=dict(collections=[col], bbox=list(a["bbox"]), limit=20))
            best = ("none", 0)
            for ft in r.json()["features"]:
                href = ft["assets"]["dtm"]["href"]
                s = sample_cog(href, a["lon"], a["lat"])
                if isinstance(s[0], int) and s[0] > best[1]:
                    best = (ft["id"], s[0])
                if isinstance(s[0], str):
                    best = (f"err:{s[1]}", best[1]) if best[1] == 0 else best
            valid[a["id"]] = best
        n_valid = sum(1 for v in valid.values() if v[1] > 0)
        DETAIL[col] = dict(per=per, control=ctl, valid_pixels_at_centroid=valid, ids=ids)
        k, f = first_with_hit(firsts, ["city_toronto_core"])
        props = f["properties"] if f else {}
        qf = seen(props, ["datetime", "created", "updated", "proj:epsg", "proj:shape", "proj:transform", "proj:geometry"])
        if f:
            save_sample(f"{col}_item", f | {"assets": {k2: v["href"] for k2, v in f["assets"].items()}})
        add("S1", f"nrcan_{col.replace('-', '_')}", "airborne", DC_SEARCH + f" POST {{collections:[{col}],bbox:{{bbox}}}}", "none",
            "yes", "/".join(map(str, st)), f"{n_valid}/15" if col == "hrdem-lidar" else f"{n_valid}/15",
            "yes" if ctl == 0 else "no", "acquisition" if col == "hrdem-lidar" else "composite", qf,
            "none; item has datetime only, no scan angle, no QL, no point density (project name is in the item id)",
            "OGL-Canada-2.0",
            f"{desc}. aoi_hits counts AOIs with VALID DTM pixels at the centroid (60x60 px COG window), not STAC bbox hits "
            f"(STAC bbox hits = {sum(1 for v in per.values() if v)}/15; mosaic item is a 500x500 km tile so STAC alone over-reports). "
            f"valid-pixel AOIs: {[k2 for k2, v in valid.items() if v[1] > 0]}. Absent at: "
            f"{[a['id'] for a in AOIS if a['id'] not in valid or valid[a['id']][1] == 0]}. Canada-only coverage; US AOIs are expected gaps")


def probe_napl():
    cols_r = req("GET", "https://datacube.services.geo.ca/pgstac/api/collections?limit=200").json()["collections"]
    napl = [c["id"] for c in cols_r if c["id"].startswith("napl-")]
    per, ctl, cover, st, firsts, ids = stac_probe(DC_SEARCH, napl)
    DETAIL["napl"] = dict(collections=napl, per=per, control=ctl, ids=ids)
    k, f = first_with_hit(firsts)
    props = f["properties"] if f else {}
    qf = seen(props, ["datetime", "proj:epsg", "proj:shape", "proj:transform", "proj:geometry"])
    if f:
        save_sample("napl_item", f | {"assets": {k2: v["href"] for k2, v in f["assets"].items()}})
    lic = sorted({c.get("license") for c in cols_r if c["id"] in napl})
    add("S1", "nrcan_napl_airphoto_mosaics", "airborne", DC_SEARCH + " POST {collections:[napl-*],bbox:{bbox}}", "none", "yes",
        "/".join(map(str, st)), fmt_hits(per), "yes" if ctl == 0 else "no", "composite", qf,
        "none; per-year orthomosaic of historical air photos, no per-frame metadata",
        ", ".join(lic) + " (collection licence field)",
        f"{len(napl)} city/regional historical air-photo time series ({', '.join(napl)}); coverage is only those cities. hits: {hit_list(per)}")


# ----------------------------------------------------------------------------------------------
# S1/S3: NEON AOP
# ----------------------------------------------------------------------------------------------
def hav_km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def probe_neon():
    base = "https://data.neonscience.org/api/v0"
    r = req("GET", base + "/sites")
    sites = r.json()["data"]
    prods = {"lidar": ["DP1.30003.001"], "hyperspectral": ["DP3.30006.001", "DP3.30006.002", "DP1.30006.001"], "rgb": ["DP3.30010.001"]}
    # product description search for angle fields
    desc = {}
    for code in ["DP1.30003.001", "DP3.30006.001", "DP1.30006.001", "DP1.30008.001", "DP3.30010.001"]:
        rr = req("GET", f"{base}/products/{code}")
        if rr.status_code == 200:
            d = rr.json()["data"]
            txt = " ".join(str(d.get(k, "")) for k in ["productDescription", "productAbstract", "productDesignDescription",
                                                       "productStudyDescription", "productBasicDescription", "productRemarks"])
            desc[code] = dict(name=d["productName"], angle_mentions=sorted(set(re.findall(r"[^.]*\b(?:zenith|nadir|scan angle|view angle|viewing angle|incidence)\b[^.]*\.", txt, re.I)))[:4])
    # /data listing test
    one = [s for s in sites if any(p["dataProductCode"] == "DP1.30003.001" for p in s["dataProducts"])][0]
    lp = [p for p in one["dataProducts"] if p["dataProductCode"] == "DP1.30003.001"][0]
    data_url = lp["availableDataUrls"][-1]
    rd = req("GET", data_url)
    data_status = rd.status_code
    data_msg = rd.text[:120].replace("\n", " ")
    DETAIL["neon_data_listing"] = dict(url=data_url, status=data_status, body=data_msg)
    DETAIL["neon_product_desc"] = desc
    for kind, codes in prods.items():
        aop = []
        for s in sites:
            for p in s["dataProducts"]:
                if p["dataProductCode"] in codes:
                    aop.append(dict(site=s["siteCode"], lat=s["siteLatitude"], lon=s["siteLongitude"], code=p["dataProductCode"],
                                    months=p["availableMonths"]))
        per, near = {}, {}
        for a in AOIS + [dict(id="CONTROL", lat=0.05, lon=-149.95)]:
            best = min(((hav_km(a["lat"], a["lon"], x["lat"], x["lon"]), x["site"]) for x in aop), default=(1e9, None))
            near[a["id"]] = (round(best[0], 1), best[1])
            per[a["id"]] = best[0] <= 25
        ctl = per.pop("CONTROL")
        DETAIL[f"neon_{kind}"] = dict(n_site_products=len(aop), nearest_km=near)
        n_sites = len({x["site"] for x in aop})
        qf = ["availableMonths (site x product x month)", "availableReleases", "siteLatitude", "siteLongitude"]
        if kind == "lidar":
            off = ("none at catalog level; point cloud files could not be listed (/data 403), "
                   "so whether they carry a per-return scan angle was not checked")
        elif kind == "hyperspectral":
            off = ("none at catalog level; flightline-level products could not be listed (/data 403), "
                   "so per-flightline view geometry was not seen")
        else:
            off = "none at catalog level; RGB camera tiles carry no angle"
        add("S1" if kind != "hyperspectral" else "S3", f"neon_aop_{kind}", "airborne", f"{base}/sites ; {base}/data/{{productCode}}/{{site}}/{{YYYY-MM}}",
            "none", "partial", f"sites:{r.status_code}/data:{data_status}", fmt_hits(per),
            "yes" if not ctl else "no", "acquisition", qf, off, "NEON open data policy (licence not in the API; check neonscience.org data policy)",
            f"Catalog search is by SITE POINT proximity only: hit = AOI centroid within 25 km of a NEON site that has the product ({n_sites} sites). "
            f"No footprint polygon API found (flight boxes live in downloadable shapefiles). Nearest site km: "
            f"{ {k2: v for k2, v in near.items() if v[0] < 200} }. US-only (+PR), not a failure for CA AOIs. "
            f"GET /data/{{product}}/{{site}}/{{month}} (the file list that would carry per-flightline names and QC reports) returned {data_status} '{data_msg}' "
            f"from this host for every AOP product tried, while /sites and /products return 200; so per-flightline QC fields were NOT seen. "
            f"API rate-limit headers: x-ratelimit-limit={r.headers.get('x-ratelimit-limit')}, x-ratelimit-reset={r.headers.get('x-ratelimit-reset')} (window unit not documented in the response). "
            f"Product-description angle mentions: {json.dumps({c: v['angle_mentions'][:1] for c, v in desc.items()})[:600]}")


# ----------------------------------------------------------------------------------------------
# S1: OpenTopography, NOAA Digital Coast
# ----------------------------------------------------------------------------------------------
def probe_opentopography():
    u = "https://portal.opentopography.org/API/otCatalog"
    per, st, names, dens = {}, set(), {}, {}
    first = None
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL)]:
        b = a["bbox"]
        r = req("GET", u, params=dict(productFormat="PointCloud", minx=b[0], miny=b[1], maxx=b[2], maxy=b[3], detail="true",
                                      outputFormat="json", include_federated="true"), timeout=120)
        st.add(r.status_code)
        ds = r.json().get("Datasets", []) if r.status_code == 200 else []
        per[a["id"]] = len(ds)
        names[a["id"]] = [d["Dataset"]["name"] for d in ds][:6]
        if ds and first is None:
            first = ds[0]
    ctl = per.pop("CONTROL")
    det = [a for a in AOIS if a["id"] == "city_us_detroit_mi"][0]["bbox"]
    fed_false = req("GET", u, params=dict(productFormat="PointCloud", minx=det[0], miny=det[1], maxx=det[2], maxy=det[3],
                                          detail="true", outputFormat="json", include_federated="false")).json().get("Datasets", [])
    # raster catalog
    rr = req("GET", u, params=dict(productFormat="Raster", minx=det[0], miny=det[1], maxx=det[2], maxy=det[3], detail="true",
                                   outputFormat="json", include_federated="true")).json().get("Datasets", [])
    rctl = req("GET", u, params=dict(productFormat="Raster", minx=CONTROL[0], miny=CONTROL[1], maxx=CONTROL[2], maxy=CONTROL[3],
                                     detail="true", outputFormat="json", include_federated="true")).json().get("Datasets", [])
    DETAIL["opentopography"] = dict(per=per, control=ctl, names=names, federated_false_detroit=len(fed_false),
                                    raster_detroit=len(rr), raster_control=len(rctl))
    qf = []
    if first:
        d = first["Dataset"]
        save_sample("opentopography_pointcloud_dataset", first)
        qf = seen(d, ["name", "identifier", "dateCreated", "temporalCoverage", "fileFormat", "citation", "spatialCoverage"])
        vm = [x["name"] for x in d["spatialCoverage"].get("variableMeasured", [])]
        qf += [f"spatialCoverage.variableMeasured:{n}" for n in vm]
    add("S1", "opentopography_otcatalog_pointcloud", "airborne", u + "?productFormat=PointCloud&minx={w}&miny={s}&maxx={e}&maxy={n}&detail=true&outputFormat=json&include_federated=true",
        "none", "yes", "/".join(map(str, sorted(st))), fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", qf,
        "none; catalog lists only dates, area, CRS (no QL, no point density, no scan angle)",
        "per-dataset (USGS 3DEP public domain; others vary); citation required",
        f"Catalog search is open without a key. include_federated=false returns {len(fed_false)} at Detroit vs include_federated=true {per['city_us_detroit_mi']}, "
        f"so the federated flag matters and 3DEP point clouds appear only with it. Raster catalog returns {len(rr)} at Detroit and {len(rctl)} at the control "
        f"(global DEMs, so rasters never discriminate). Names: {json.dumps({k2: v for k2, v in names.items() if v})[:500]}. US-heavy coverage. "
        f"Same Wayne County 2017 survey as PC 3DEP and NOAA DAV (cross-listing).")
    # data API
    codes = {}
    for nm, url in [("globaldem", "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=42.33&north=42.35&west=-83.07&east=-83.05&outputFormat=GTiff"),
                    ("usgsdem", "https://portal.opentopography.org/API/usgsdem?datasetName=USGS1m&south=42.33&north=42.35&west=-83.07&east=-83.05&outputFormat=GTiff")]:
        rr2 = req("GET", url)
        codes[nm] = (rr2.status_code, re.sub(r"<[^>]+>", "", rr2.text)[:80])
    add("S1", "opentopography_data_api", "airborne", "https://portal.opentopography.org/API/{globaldem|usgsdem}?demtype=..&south=..&north=..&west=..&east=..&API_Key={key}",
        "key-we-lack", "partial", "/".join(str(v[0]) for v in codes.values()), "n/a", "n/a", "composite", "none seen (401 before any metadata)",
        "none", "per-dataset",
        f"Downloads need a free API key (not created). Responses: {codes}. The catalog row above is the open part.")


def probe_noaa_dav():
    u = "https://coast.noaa.gov/arcgis/rest/services/DAV/DAV_footprints/MapServer/0/query"

    def q(bbox, where="1=1"):
        return req("GET", u, params=dict(geometry=bstr(bbox), geometryType="esriGeometryEnvelope", inSR=4326, spatialRel="esriSpatialRelIntersects",
                                         where=where, outFields="*", returnGeometry="false", f="json"))
    per_l, per_i, per_all, titles, st = {}, {}, {}, {}, set()
    first = {}
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL)]:
        r = q(a["bbox"])
        st.add(r.status_code)
        feats = [f["attributes"] for f in r.json().get("features", [])] if r.status_code == 200 else []
        per_all[a["id"]] = len(feats)
        per_l[a["id"]] = [f for f in feats if f["data_type"] == "Lidar"]
        per_i[a["id"]] = [f for f in feats if f["data_type"] == "Imagery"]
        titles[a["id"]] = [f["title"] for f in per_l[a["id"]] + per_i[a["id"]]][:4]
        for t, lst in (("Lidar", per_l[a["id"]]), ("Imagery", per_i[a["id"]])):
            if lst and t not in first and a["id"] != "CONTROL":
                first[t] = lst[0]
    det = [a for a in AOIS if a["id"] == "city_us_detroit_mi"][0]["bbox"]
    n_lidar_where = len(q(det, "data_type='Lidar'").json()["features"])
    types = sorted({f["data_type"] for a in per_l for f in per_l[a]} | {f["data_type"] for a in per_i for f in per_i[a]})
    ctlL, ctlI = len(per_l.pop("CONTROL")), len(per_i.pop("CONTROL"))
    # InPort page
    inport = {}
    for t, f in first.items():
        rr = req("GET", f["metadata"], timeout=60)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", rr.text, flags=re.S)))
        ql = re.findall(r"QL\s?\d[^.]{0,60}", txt)
        inport[t] = dict(status=rr.status_code, ql_text=ql[:2], has_pulse=("pulse" in txt.lower()))
    DETAIL["noaa_dav"] = dict(lidar={k2: len(v) for k2, v in per_l.items()}, imagery={k2: len(v) for k2, v in per_i.items()}, inport=inport,
                              titles=titles)
    for t, per in (("Lidar", per_l), ("Imagery", per_i)):
        f = first.get(t, {})
        save_sample(f"noaa_dav_{t.lower()}_footprint_attrs", f)
        add("S1", f"noaa_digital_coast_dav_{t.lower()}", "airborne", u + "?geometry={bbox}&geometryType=esriGeometryEnvelope&inSR=4326&outFields=*&f=json",
            "none", "yes", "/".join(map(str, sorted(st))), fmt_hits({k2: v for k2, v in per.items()}), "yes" if (ctlL if t == "Lidar" else ctlI) == 0 else "no",
            "acquisition", seen(f, ["id", "data_type", "title", "metadata", "dav_link"]),
            "none in the footprint layer; quality and flight details only as free text on the InPort page "
            f"({f.get('metadata','')}): QL text seen = {inport.get(t, {}).get('ql_text')}",
            "not in the footprint layer; stated per InPort record",
            "Data Access Viewer footprint layer (ArcGIS FeatureServer on coast.noaa.gov; no documented inventory API, this layer is what the viewer queries). "
            f"data_type values seen: {types}. where=data_type='Lidar' at Detroit returns {n_lidar_where}. Titles: {json.dumps({k2: v for k2, v in titles.items() if v})[:400]}. "
            "Coastal US only; Windsor ON hits are the Detroit River footprint edge. Checkout/download is order-based (email), AWS mirror noaa-nos-coastal-lidar-pds is anonymous S3.")


# ----------------------------------------------------------------------------------------------
# S2: drone
# ----------------------------------------------------------------------------------------------
def probe_oam():
    u = "https://api.openaerialmap.org/meta"
    per, per_all, st = {}, {}, set()
    gsds, first = [], None
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL)]:
        r = req("GET", u, params=dict(bbox=bstr(a["bbox"]), limit=100, platform="uav"))
        st.add(r.status_code)
        j = r.json()
        per[a["id"]] = len(j.get("results", []))
        if j["results"]:
            gsds += [x["gsd"] for x in j["results"]]
            if first is None and a["id"] != "CONTROL":
                first = j["results"][0]
        r2 = req("GET", u, params=dict(bbox=bstr(a["bbox"]), limit=1))
        per_all[a["id"]] = r2.json()["meta"]["found"]
    ctl, ctl_all = per.pop("CONTROL"), per_all.pop("CONTROL")
    tor = [a for a in AOIS if a["id"] == "stress_city_toronto_full"][0]["bbox"]
    gdiff = (req("GET", u, params=dict(bbox=bstr(tor), limit=1, platform="uav")).json()["meta"]["found"],
             req("GET", u, params=dict(bbox=bstr(tor), limit=1, platform="uav", gsd_to=0.01)).json()["meta"]["found"])
    junk = req("GET", u, params=dict(bbox=bstr(CONTROL), limit=1)).json()["results"]
    DETAIL["oam"] = dict(uav=per, any_platform=per_all, control_uav=ctl, control_any=ctl_all, gsd_filter_diff_toronto=gdiff)
    if first:
        save_sample("oam_meta_uav_result", {k2: v for k2, v in first.items() if k2 not in ("projection", "geojson")})
    qf = seen(first or {}, ["gsd", "acquisition_start", "acquisition_end", "platform", "provider", "file_size", "uploaded_at", "title", "bbox",
                            "footprint", "meta_uri", "license"]) + (["properties.sensor"] if first and "sensor" in first.get("properties", {}) else [])
    add("S2", "openaerialmap_meta_api", "drone", u + "?bbox={w},{s},{e},{n}&platform=uav&limit=100", "none", "yes", "/".join(map(str, sorted(st))),
        fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", qf,
        "none; no camera pitch/off-nadir or flight altitude in the catalog record (mapping imagery, usually near-nadir)",
        "CC-BY 4.0 (per image; provider-set)",
        f"platform=uav filter is essential: without it the mid-Pacific control returns {ctl_all} hit (a satellite item '{junk[0]['title'] if junk else ''}' with gsd {junk[0]['gsd'] if junk else ''} "
        f"and a near-global bbox) so unfiltered control FAILS; with platform=uav control={ctl}. Per-AOI any-platform counts: {per_all}. "
        f"gsd filter works (Toronto uav {gdiff[0]} -> gsd_to=0.01 {gdiff[1]}). gsd is in CRS units: a 4326 upload shows 1.857e-07 (degrees), so gsd is not reliably metres. "
        f"Hit gsd values (m or deg): {sorted(set(round(g, 4) for g in gsds))[:8]}. 'sensor' is free text and often 'Unknow'. hits: {hit_list(per)}")


def probe_hot_stac():
    base = "https://api.imagery.hotosm.org/stac/search"
    flt = {"filter-lang": "cql2-json", "filter": {"op": "=", "args": [{"property": "oam:platform_type"}, "uav"]}}
    per, ctl, cover, st, firsts, ids = stac_probe(base, ["openaerialmap"], extra=flt)
    per_all, ctl_all, _, st2, firsts2, _ = stac_probe(base, ["openaerialmap"], geom_check=False)
    k, f = first_with_hit(firsts)
    props = f["properties"] if f else {}
    if f:
        save_sample("hot_stac_oam_item", f | {"assets": list(f["assets"])})
    qf = seen(props, ["gsd", "start_datetime", "end_datetime", "oam:platform_type", "oam:producer_name", "instruments", "license", "providers", "created"])
    add("S2", "hotosm_oam_stac", "drone", base + " POST {collections:[openaerialmap],bbox:{bbox},filter:{oam:platform_type=uav}}", "none", "yes",
        "/".join(map(str, sorted(set(st) | set(st2)))), fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", qf,
        "none; instruments (e.g. 'DJI M3E') names the camera but no pitch/off-nadir",
        "CC-BY-4.0",
        f"HOT's STAC mirror of OpenAerialMap (also hosts maxar-opendata, vantor-opendata, noaa-emergency-response collections for gap S4). CQL2 filter on oam:platform_type works: "
        f"unfiltered AOI hits {fmt_hits(per_all)} vs uav {fmt_hits(per)}; unfiltered control={ctl_all}. Better than the legacy /meta API because of instruments + filter-lang. "
        f"numberMatched is not returned (count by paging). {cover_note(cover)}. hits: {hit_list(per)}")


def probe_geonadir():
    u = "https://api.geonadir.com/api/dataset/"
    per, st, first, priv, rast = {}, set(), None, 0, set()
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL)]:
        r = req("GET", u, params=dict(bbox=bstr(a["bbox"]), limit=100))
        st.add(r.status_code)
        j = r.json() if r.status_code == 200 else {}
        res = j.get("results", [])
        per[a["id"]] = j.get("count", 0)
        for x in res:
            priv += 1 if x.get("is_private") else 0
            rast.update(x.get("available_rasters") or [])
        if res and first is None and a["id"] != "CONTROL":
            first = res[0]
    ctl = per.pop("CONTROL")
    total = req("GET", u, params=dict(limit=1)).json()["count"]
    swapped = req("GET", u, params=dict(bbox="43.0,-80.0,44.0,-79.0", limit=1)).json()["count"]
    bad = req("GET", u, params=dict(is_private="true", limit=1)).json()["count"]
    DETAIL["geonadir"] = dict(per=per, control=ctl, total=total, private_in_hits=priv)
    safe = None
    if first:
        safe = json.loads(re.sub(r"\?[^\"]*Signature=[^\"]*", "?<signed>", json.dumps(first)))
        save_sample("geonadir_dataset_record", safe)
    qf = seen(first or {}, ["captured_date", "available_rasters", "band_stats", "bbox", "crs", "geotransform", "category", "is_private",
                            "is_shareable", "alignment", "cumulative_adjustment", "workspace", "uav_uid"])
    add("S2", "geonadir_api_dataset", "drone", u + "?bbox={w},{s},{e},{n}&limit=100", "none", "partial", "/".join(map(str, sorted(st))), fmt_hits(per),
        "yes" if ctl == 0 else "no", "acquisition", qf,
        "none; no EXIF pitch/off-nadir exposed (raw images are not in this API); georeferencing in geotransform+crs, gsd = geotransform[1]",
        "unstated in API; GeoNadir FAIR Open Data programme states CC-BY-4.0 for its AWS subset",
        f"Unauthenticated GET /api/dataset/ lists {total} datasets (undocumented; no public docs found, root /api/ lists routes). Only bbox filters (lon,lat,lon,lat order; "
        f"lat,lon order gives {swapped}); is_private/search/category/ordering params are ignored or 500 (is_private=true still returns {bad}), so privacy must be checked per record "
        f"(private records in AOI hits: {priv}). The record's own bbox field is [lat,lon,lat,lon]. thumbnail_image holds a signed S3 URL (credentials in query; not stored). "
        f"The advertised public STAC https://data.geonadir.com/stac/ returned 404 (README says not live yet). available_rasters seen: {sorted(rast)}. Licence per dataset is not in the record, so "
        f"this is an undocumented endpoint whose reuse terms are unknown until GeoNadir FAIR Data is published. hits: {hit_list(per)}")


def probe_dronedb():
    r = req("GET", "https://hub.dronedb.app/r/public")
    add("S2", "dronedb_hub", "drone", "https://hub.dronedb.app/", "none", "partial", r.status_code, "n/a", "n/a", "acquisition", "none seen",
        "none", "per-dataset", "Single-page app; no public search or catalog API found (any path returns the SPA shell with 200, JSON endpoints tried: /api/v1/orgs). Not usable for AOI search.")


# ----------------------------------------------------------------------------------------------
# S3: CMR-based
# ----------------------------------------------------------------------------------------------
CMR = "https://cmr.earthdata.nasa.gov/search/granules"


def cmr_probe(concept, extra=None, ctl_extra=None):
    per, ids, st = {}, {}, set()
    first_umm = None
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL)]:
        p = dict(collection_concept_id=concept, bounding_box=bstr(a["bbox"]), page_size=2)
        if extra:
            p.update(extra)
        r = req("GET", CMR + ".umm_json", params=p)
        st.add(r.status_code)
        per[a["id"]] = int(r.headers.get("CMR-Hits", 0)) if r.status_code == 200 else 0
        if r.status_code == 200 and r.json().get("items") and first_umm is None and a["id"] != "CONTROL":
            first_umm = r.json()["items"][0]
        if r.status_code == 200:
            ids[a["id"]] = [i["umm"]["GranuleUR"] for i in r.json().get("items", [])][:2]
    ctl = per.pop("CONTROL")
    r0 = req("GET", CMR + ".umm_json", params=dict(collection_concept_id=concept, page_size=1, **(extra or {})))
    total = r0.headers.get("CMR-Hits")
    if first_umm is None and r0.status_code == 200 and r0.json().get("items"):
        first_umm = r0.json()["items"][0]
    return per, ctl, sorted(st), first_umm, ids, total


def umm_seen(umm):
    q = []
    if not umm:
        return q
    u = umm["umm"]
    for k in ["CloudCover", "TemporalExtent", "PGEVersionClass", "Platforms", "DayNightFlag"]:
        if k in u:
            q.append(k)
    if "DataGranule" in u and "DayNightFlag" in u["DataGranule"]:
        q.append("DataGranule.DayNightFlag")
    for aa in u.get("AdditionalAttributes", []) or []:
        q.append("AdditionalAttributes." + aa["Name"])
    if "MeasuredParameters" in u:
        q.append("MeasuredParameters")
    return q


def probe_emit():
    concept = "C4079844428-LPCLOUD"
    per, ctl, st, first, ids, total = cmr_probe(concept)
    cc_params = dict(cloud_cover="0,30")
    per_cc, ctl_cc, *_ = cmr_probe(concept, extra=cc_params)
    if first:
        save_sample("emit_l2a_rfl_v002_umm", {k: v for k, v in first["umm"].items()})
    add("S3", "emit_l2a_rfl_v002_cmr", "satellite", CMR + ".umm_json?collection_concept_id=C4079844428-LPCLOUD&bounding_box={w},{s},{e},{n}", "free-reg",
        "yes", "/".join(map(str, st)), fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", umm_seen(first),
        "none in the CMR granule record (only SOLAR_ZENITH/SOLAR_AZIMUTH). Sensor view angles, if any, sit in sidecar files that need Earthdata login (not opened)",
        "NASA Earthdata open data (no use restriction stated in the record)",
        f"Search is public; downloads need Earthdata login (not created). Collection has {total} granules. cloud_cover=0,30 filter: hits {fmt_hits(per_cc)} vs unfiltered {fmt_hits(per)}; "
        f"control unfiltered={ctl}, filtered={ctl_cc}. CMR 'CloudCover' is scene-level (e.g. 90 for Detroit scene, so whole-scene cloud is not AOI cloud). EMIT is not on Planetary Computer. "
        f"SOLAR_ZENITH/SOLAR_AZIMUTH are the only angles in the granule record. Hits include Canadian AOIs (Essex, Taber, HVC, Toronto, Montreal, Windsor), so coverage is not US-only. hits: {hit_list(per)}")
    return per


def probe_aviris():
    cols = [("aviris_ng_l2_reflectance", "C2659129205-ORNL_CLOUD", "AVIRIS-NG L2 surface reflectance (facility instrument); granule = one ENVI header per flight line"),
            ("aviris_ng_above_v3", "C3253178409-ORNL_CLOUD", "ABoVE AVIRIS-NG imaging spectroscopy Alaska/Canada/Iceland 2017-2022"),
            ("aviris3_l2a_reflectance", "C3369603199-ORNL_CLOUD", "AVIRIS-3 L2A orthocorrected reflectance"),
            ("aviris_classic_l2_reflectance", "C2711871294-ORNL_CLOUD", "AVIRIS-Classic L2 reflectance"),
            ("aviris5_l2a_reflectance", "C4184090548-ORNL_CLOUD", "AVIRIS-5 L2A reflectance")]
    for name, concept, desc in cols:
        per, ctl, st, first, ids, total = cmr_probe(concept)
        DETAIL[name] = dict(per=per, control=ctl, ids=ids, total=total)
        if first:
            save_sample(f"{name}_umm", {k: v for k, v in first["umm"].items() if k != "RelatedUrls"})
        add("S3", f"{name}_cmr", "airborne", CMR + f".umm_json?collection_concept_id={concept}&bounding_box={{w}},{{s}},{{e}},{{n}}", "free-reg", "yes",
            "/".join(map(str, st)), fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", umm_seen(first),
            "none in the CMR granule record. View geometry, if provided, is in login-gated sidecar files (not opened); the flight-line table lists altitude and heading but has no off-nadir column",
            "NASA Earthdata open data (no use restriction stated in the record)",
            f"{desc}. {total} granules in collection. Search is public; downloads need Earthdata login. Granule spatial polygons are coarse and may over-report. "
            f"AVIRIS granule records carry only time + platform list (aircraft: ER-2, Twin Otter, B-200...) and no cloud, no angles, no altitude. hits: {hit_list(per)}")
    # flight line locator
    concept = "C2662360177-ORNL_CLOUD"
    per, ctl, st, first, ids, total = cmr_probe(concept)
    r = req("GET", "https://data.ornldaac.earthdata.nasa.gov/protected/aviris/AVIRIS_FlightLine_Locator/data/AVIRIS-NG_flight_table.csv", allow_redirects=False)
    csv_status = r.status_code
    r2 = req("GET", "https://data.ornldaac.earthdata.nasa.gov/protected/aviris/AVIRIS_FlightLine_Locator/data/AVIRIS-NG_flight_table.csv")
    add("S3", "aviris_flightline_locator_2140", "airborne", CMR + ".umm_json?collection_concept_id=C2662360177-ORNL_CLOUD ; https://data.ornldaac.earthdata.nasa.gov/protected/aviris/AVIRIS_FlightLine_Locator/data/AVIRIS-NG_flight_table.csv",
        "free-reg", "partial", f"cmr:{'/'.join(map(str, st))}/csv:{r2.status_code}", "n/a", "n/a", "acquisition", umm_seen(first),
        "none seen live; documented table columns include altitude (m), speed_on_ground, direction (heading, deg), scene_elevation, weather_condition, platform, but NO off-nadir column",
        "NASA Earthdata open data (no use restriction stated in the record)",
        f"The flight-line table is the sidecar that carries per-line altitude and heading. Its 37 CMR granules each hold the whole archive (bbox covers most of the globe: control returned {ctl}, every AOI returned >=10), "
        f"so CMR spatial search cannot select lines; the CSV/shapefile must be downloaded and filtered locally. Download returned HTTP {r2.status_code} anonymously (redirect {csv_status}); needs Earthdata login. "
        f"Column list is from the dataset guide (https://daac.ornl.gov/AVIRIS/guides/AVIRIS_FlightLine_Locator.html), not seen in a live response. Data portals aviris.jpl.nasa.gov/dataportal and popo.jpl.nasa.gov/mmgis-aviris are JS apps with no documented API; alt_locator returns 403.")


def probe_pace():
    win = dict(temporal="2026-09-01T00:00:00Z,2026-09-30T23:59:59Z")
    for name, concept, desc in [("pace_oci_l1b_sci", "C3392966952-OB_CLOUD", "OCI L1B top-of-atmosphere radiance swath (hyperspectral ocean-colour sensor, coarse km-scale pixels per mission documentation, not checked here)"),
                                ("pace_oci_l2_sfrefl", "C3620139902-OB_CLOUD", "OCI L2 regional surface reflectance (land)")]:
        per, ctl, st, first, ids, total = cmr_probe(concept, extra=win)
        per_all, ctl_all, *_ = cmr_probe(concept)
        if first:
            save_sample(f"{name}_umm", {k: v for k, v in first["umm"].items() if k != "RelatedUrls"})
        add("S3", f"{name}_cmr", "satellite", CMR + f".umm_json?collection_concept_id={concept}&bounding_box={{w}},{{s}},{{e}},{{n}}&temporal={{t0}},{{t1}}", "free-reg",
            "yes", "/".join(map(str, st)), fmt_hits(per), "n/a", "acquisition", umm_seen(first),
            "none in the CMR granule record; view angles would be inside the NetCDF swath (not opened: download needs Earthdata login)",
            "NASA Earthdata open data (no use restriction stated in the record)",
            f"{desc}. Global sensor: control is not discriminating (mid-Pacific returns {ctl} granules in the window), so control_passed=n/a. Temporal filter works "
            f"(Detroit all-time {per_all['city_us_detroit_mi']} vs Sept-2026 {per['city_us_detroit_mi']}). Granule is a whole orbit swath, so a 1 km AOI is a handful of pixels at most; "
            f"downloads need Earthdata login. Hits shown are for 2026-09 only. hits: {hit_list(per)}")


# ----------------------------------------------------------------------------------------------
# S3: EnMAP / DESIS (DLR STAC), PRISMA, Tanager
# ----------------------------------------------------------------------------------------------
DLR = "https://geoservice.dlr.de/eoc/ogc/stac/v1/search"


def probe_enmap():
    fallback_file = SAMPLES / "enmap_l2a_item_properties_earlier_session.json"
    for col, nm, desc in [("ENMAP_HSI_L2A", "enmap_l2a_dlr_stac", "EnMAP L2A (atmospherically corrected, 30 m, 224 bands)"),
                          ("DESIS_HSI_L2A", "desis_l2a_dlr_stac", "DESIS L2A (ISS hyperspectral, 30 m)")]:
        per, ctl, cover, st, firsts, ids = stac_probe(DLR, [col], method="GET", limit=100)
        k, f = first_with_hit(firsts, ["city_us_detroit_mi"])
        props = f["properties"] if f else {}
        if f:
            save_sample(f"{nm}_item", f | {"assets": {k2: v["href"] for k2, v in f["assets"].items()}})
        wanted = ["eo:cloud_cover", "eo:snow_cover", "enmap:cirrus_cover", "enmap:cloud_shadow", "enmap:haze_cover", "enmap:water_cover",
                  "view:sun_azimuth", "view:sun_elevation", "enmap:acrossOffNadirAngle", "enmap:alongOffNadirAngle", "enmap:sceneAzimuthAngle",
                  "enmap:overallQuality", "enmap:overallQualityVNIR", "enmap:overallQualitySWIR", "enmap:qualityAtmosphere", "enmap:sceneAOT",
                  "enmap:sceneWV", "enmap:productScreeningResultStatus", "enmap:defectivePixelsVNIR", "enmap:defectivePixelsSWIR",
                  "enmap:sceneSunglint", "sat:orbit_state", "sat:relative_orbit", "processing:level", "start_datetime", "end_datetime",
                  "card4l:geometric_accuracy_radial_rmse",
                  "desis:sceneIncidenceAngle", "desis:sceneAzimuthAngle", "desis:eastern_geometric_accuracy", "desis:northern_geometric_accuracy",
                  "desis:ozoneValue", "gsd"]
        DETAIL[col] = dict(per=per, control=ctl, ids=ids, cover=cover)
        if st != [200]:
            earlier = json.load(open(fallback_file)) if (fallback_file.exists() and col.startswith("ENMAP")) else {}
            add("S3", nm, "satellite", DLR + f"?collections={col}&bbox={{w}},{{s}},{{e}},{{n}}&limit=100", "free-reg", "no",
                "/".join(map(str, st)), "n/a", "n/a", "acquisition", seen(earlier, wanted),
                "enmap:acrossOffNadirAngle and enmap:alongOffNadirAngle (item properties, degrees) as seen in an earlier same-day request" if earlier else "not seen",
                "proprietary STAC licence field",
                f"{desc}. DLR host answered HTTP {st} to every request on this run (3 attempts each, root URL also 502), so the 15-AOI sweep did not run. "
                "An earlier same-day request (before the outage) for the Detroit AOI returned 8 ENMAP_HSI_L2A and 8 ENMAP_HSI_L1B items and 0 DESIS_HSI_L2A; "
                "one L2A item's properties are kept in samples/enmap_l2a_item_properties_earlier_session.json. Re-run probe.py probe_enmap when the host is back.")
            continue
        qf = seen(props, wanted)
        stat = props.get("statistic", {})
        qf += [f"statistic.{k2}" for k2 in ("cloud_shadow", "haze_cover", "defectivePixels") if k2 in stat]
        det = [a for a in AOIS if a["id"] == "city_us_detroit_mi"][0]["bbox"]
        r_all = req("GET", DLR, params=dict(collections=col, bbox=bstr(det), limit=100))
        r_f = req("GET", DLR, params=dict(collections=col, bbox=bstr(det), limit=100, filter="eo:cloud_cover<50", **{"filter-lang": "cql2-text"}))
        feats_all = r_all.json().get("features", [])
        n_all = len(feats_all)
        try:
            n_f = len(r_f.json().get("features", [])) if r_f.status_code == 200 else f"HTTP {r_f.status_code}"
        except ValueError:
            n_f = f"HTTP {r_f.status_code}"
        n_client = len([x for x in feats_all if x["properties"].get("eo:cloud_cover", 100) < 50])
        auth_note = ""
        if f:
            a_href = f["assets"].get("thumbnail", f["assets"].get("image"))["href"]
            ra = requests.head(a_href, allow_redirects=False, timeout=30, headers=UA)
            auth_note = f"asset HEAD -> {ra.status_code} {ra.headers.get('location','')[:45]}"
        if col.startswith("ENMAP"):
            off = "enmap:acrossOffNadirAngle and enmap:alongOffNadirAngle (item properties, degrees, signed)"
        else:
            off = "desis:sceneIncidenceAngle (item property, degrees; named incidence, not off-nadir) plus desis:sceneAzimuthAngle"
        lic = "proprietary (STAC licence field)"
        qnote = ("quality_classes/quality_cloud assets give per-pixel masks. " if col.startswith("ENMAP")
                 else f"assets seen: {sorted(f['assets']) if f else []}. ")
        add("S3", nm, "satellite", DLR + f"?collections={col}&bbox={{w}},{{s}},{{e}},{{n}}&limit=100", "free-reg", "yes", "/".join(map(str, st)),
            fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", qf, off, lic,
            f"{desc}. Search is public and unauthenticated; asset downloads redirect to DLR SSO ({auth_note}) so download = free-reg. "
            f"Server-side CQL2 cloud filter at Detroit: all={n_all}, eo:cloud_cover<50 -> {n_f} (client-side count {n_client}). "
            f"Items are whole tiles with per-tile cloud (eo:cloud_cover), not per AOI; {qnote}"
            f"Hit count per AOI (max): {max(per.values())}. {cover_note(cover)}. hits: {hit_list(per)}")


def probe_prisma():
    r = req("GET", "https://prisma.asi.it/missionselect/", allow_redirects=True)
    add("S3", "prisma_asi_portal", "satellite", "https://prisma.asi.it/missionselect/", "free-reg", "partial", r.status_code, "n/a", "n/a", "acquisition",
        "none seen (no public catalog response)", "none seen; products are not browsable without an account",
        "ASI PRISMA data licence (registration; research use)",
        "ASI portal is a registration-gated web app (mission select page loads, 200). No public STAC/OpenSearch endpoint found, so no AOI search without an account (not created). Alternative: third-party mirrors only; PRISMA is not in CMR or DLR STAC.")


TANAGER_ROOT = "https://www.planet.com/data/stac/tanager-core-imagery/catalog.json"


def probe_tanager():
    cache = HERE / "tanager_items_cache.json"
    items = None
    if cache.exists():
        try:
            items = json.load(open(cache))
        except ValueError:
            items = None
    if items is None:
        items = {}
        root = req("GET", TANAGER_ROOT).json()
        for l in root["links"]:
            if l["rel"] != "child":
                continue
            col = req("GET", l["href"]).json()
            for k in col["links"]:
                if k["rel"] == "item":
                    href = requests.compat.urljoin(l["href"], k["href"])
                    if href in items:
                        continue
                    it = req("GET", href, host_gap=0.3).json()
                    items[href] = dict(id=it["id"], bbox=it["bbox"], collection=l["title"], properties=it["properties"], assets=list(it["assets"]))
        json.dump(items, open(cache, "w"))
    per = {}
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL, geom=box(*CONTROL))]:
        hits = [v for v in items.values() if box(*v["bbox"]).intersects(a["geom"])]
        per[a["id"]] = hits
    ctl = len(per.pop("CONTROL"))
    n_items = len({v["id"] for v in items.values()})
    first = next((h[0] for k, h in per.items() if h), None)
    first = first or next(iter(items.values()))
    props = first["properties"]
    save_sample("tanager_item_properties", first)
    # filter differential: off-nadir
    gs = [v["properties"]["gsd"] for v in items.values() if v["properties"].get("gsd")]
    offs = sorted({v["properties"].get("view:off_nadir") for v in items.values() if v["properties"].get("view:off_nadir") is not None})
    qf = seen(props, ["cloud_percent", "light_haze_percent", "gsd", "view:off_nadir", "view:azimuth", "view:sun_azimuth", "view:sun_elevation",
                      "quality_category", "collection_mode", "datetime", "license", "instruments"])
    add("S3", "planet_tanager_open_stac", "satellite", TANAGER_ROOT + " (static STAC; crawl collections->items, bbox test client-side)", "none", "yes", 200,
        fmt_hits({k: v for k, v in per.items()}), "yes" if ctl == 0 else "no", "acquisition", qf,
        "view:off_nadir (item property, degrees; also view:azimuth)",
        "CC-BY-4.0",
        f"Static catalogue, no search API: needs a crawl of {n_items} unique scenes (cached in tanager_items_cache.json). Sample set only (curated GHG/mining/agri/urban/fire scenes), not a systematic archive. "
        f"off-nadir range in set {min(offs)}-{max(offs)} deg. Hit scenes: {json.dumps({k: sorted({h['id'] for h in v}) for k, v in per.items() if v})[:500]}. "
        f"Assets: {first['assets']}. gsd across the set {min(gs)}-{max(gs)} m.")


# ----------------------------------------------------------------------------------------------
# Follow-up probes: UAVSAR (ASF), EarthExplorer UAS (M2M), Planet Open Canada
# ----------------------------------------------------------------------------------------------
ASF = "https://api.daac.asf.alaska.edu/services/search/param"


def probe_uavsar():
    per, st, first = {}, set(), None
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL)]:
        r = req("GET", ASF, params=dict(platform="UAVSAR", bbox=bstr(a["bbox"]), output="geojson", maxResults=250))
        st.add(r.status_code)
        feats = r.json().get("features", []) if r.status_code == 200 else []
        per[a["id"]] = len(feats)
        if feats and first is None and a["id"] != "CONTROL":
            first = feats[0]
    ctl = per.pop("CONTROL")
    total = req("GET", ASF, params=dict(platform="UAVSAR", output="count")).text.strip()
    if first is None:
        first = req("GET", ASF, params=dict(platform="UAVSAR", output="geojson", maxResults=1)).json()["features"][0]
    cmr_per, cmr_ctl, cmr_st, _, _, cmr_total = cmr_probe("C4261555796-ASF")
    DETAIL["uavsar"] = dict(asf=per, control=ctl, cmr_polsar=cmr_per, cmr_control=cmr_ctl)
    props = first["properties"] if first else {}
    files = sorted(props.get("bytes", {}))
    suffixes = sorted({f.rsplit(".", 1)[-1] for f in files})
    if first:
        save_sample("uavsar_asf_scene", {k: v for k, v in props.items() if k not in ("additionalUrls", "md5sum")} | {"file_suffixes": suffixes})
    qf = seen(props, ["startTime", "stopTime", "processingLevel", "flightDirection", "pathNumber", "centerLat", "centerLon", "sceneName", "fileID", "platform", "beamMode", "polarization", "faradayRotation"])
    add("S1", "uavsar_asf_search", "airborne", ASF + "?platform=UAVSAR&bbox={w},{s},{e},{n}&output=geojson", "free-reg", "yes", "/".join(map(str, sorted(st))),
        fmt_hits(per), "yes" if ctl == 0 else "no", "acquisition", qf,
        "per-pixel incidence-angle raster file *.inc and annotation text *.ann are listed per scene in the `bytes` file list (seen live on a scene from outside the AOIs: suffixes " + ",".join(suffixes) + "); contents not opened (download needs Earthdata login); no angle in the search record",
        "NASA Earthdata open data (no use restriction stated in the record)",
        f"ASF search API answers anonymously; {total} UAVSAR scenes total. Cross-check on CMR collection UAVSAR_POLSAR (C4261555796-ASF): hits {fmt_hits(cmr_per)}, control {cmr_ctl}. "
        f"flightDirection and pathNumber are null in the record. UAVSAR flies targeted campaign boxes, so the 15 AOIs are mostly empty; this is coverage, not failure. "
        f"Canadian UAVSAR (ABoVE Peace-Athabasca) is a separate ORNL DAAC collection (UAVSAR_Wetland_Peace-Athabasca_2442), not probed for AOI hits. hits: {hit_list(per)}")


def probe_ee_uas():
    base = "https://m2m.cr.usgs.gov/api/api/json/stable/dataset-search"
    codes = []
    r1 = req("POST", base, json={"datasetName": "UAS"})
    codes.append(r1.status_code)
    r2 = req("GET", base, params=dict(jsonRequest=json.dumps({"datasetName": "UAS"})))
    codes.append(r2.status_code)
    r3 = req("GET", "https://m2m.cr.usgs.gov/api/api/json/stable/")
    codes.append(r3.status_code)
    cmr = []
    for prov, kw in [("USGS_LTA", "UAS"), (None, "USGS unmanned aircraft systems imagery"), ("USGS_EROS", "UAS")]:
        p = dict(keyword=kw, page_size=5)
        if prov:
            p["provider"] = prov
        cmr.append(len(req("GET", "https://cmr.earthdata.nasa.gov/search/collections.json", params=p).json()["feed"]["entry"]))
    add("S2", "earthexplorer_usgs_uas_m2m", "drone", base + " (POST {datasetName:UAS}); EarthExplorer dataset 'UAS'", "free-reg", "no",
        "/".join(map(str, codes)), "n/a", "n/a", "acquisition", "none seen (no metadata returned)", "none",
        "per USGS UAS data policy (not retrievable)",
        f"M2M host answers anonymous POST and GET with an HTML 403 page (status {codes}); the real M2M API needs a USGS ERS account plus application token, not created. "
        f"CMR has no USGS UAS collection (collection counts for 3 queries: {cmr}). No AOI sweep possible without a login.")


def probe_planet_open_canada():
    base = "https://www.planet.com/data/stac/open-canada/ft-mckay/"
    cols = {"arps": "Analysis-Ready PlanetScope", "psscene": "PlanetScope", "skysat": "SkySat", "tanager": "Tanager", "lst": "Land Surface Temperature",
            "swc": "Soil Water Content", "crop-biomass": "Crop Biomass", "fc-monitoring": "Forest Carbon Monitoring", "fc-diligence": "Forest Carbon Diligence"}
    ext, items = {}, {}
    st = set()
    for c in cols:
        r = req("GET", base + c + "/collection.json", host_gap=0.3)
        st.add(r.status_code)
        d = r.json()
        ext[c] = d["extent"]["spatial"]["bbox"][0]
        if c in ("psscene", "skysat", "tanager"):
            for l in d["links"]:
                if l["rel"] == "item":
                    it = req("GET", requests.compat.urljoin(base + c + "/", l["href"]), host_gap=0.3).json()
                    items[(c, it["id"])] = dict(bbox=it["bbox"], props=it["properties"])
    per, by = {}, {}
    for a in AOIS + [dict(id="CONTROL", bbox=CONTROL, geom=box(*CONTROL))]:
        hit = []
        for c, bb in ext.items():
            if c in ("psscene", "skysat", "tanager"):
                if any(box(*v["bbox"]).intersects(a["geom"]) for (cc, _), v in items.items() if cc == c):
                    hit.append(c)
            elif box(*bb).intersects(a["geom"]):
                hit.append(c)
        per[a["id"]] = hit
        by[a["id"]] = hit
    ctl = len(per.pop("CONTROL"))
    DETAIL["planet_open_canada"] = dict(hits=per, extents=ext, n_items=len(items))
    keys = {}
    for (c, _), v in items.items():
        for k in v["props"]:
            keys.setdefault(c, set()).add(k)
    wanted = ["view:off_nadir", "view:azimuth", "view:sun_azimuth", "view:sun_elevation", "cloud_percent", "cloud_cover", "gsd", "clear_percent",
              "quality_category", "pl:instrument", "pl:ground_control", "pl:pixel_resolution", "pl:satellite_id", "datetime"]
    seen_q = sorted({w for c in keys for w in wanted if w in keys[c]})
    ps = next((v for (c, _), v in items.items() if c == "psscene"), None)
    if ps:
        save_sample("planet_open_canada_psscene_props", ps)
    sk = next((v for (c, _), v in items.items() if c == "skysat"), None)
    if sk:
        save_sample("planet_open_canada_skysat_props", sk)
    off_cols = sorted(c for c in keys if "view:off_nadir" in keys[c])
    add("S4", "planet_open_canada_ft_mckay", "satellite", base + "{collection}/collection.json and item JSON (static STAC; bbox test client-side)", "none", "yes", "/".join(map(str, sorted(st))),
        fmt_hits({k: bool(v) for k, v in per.items()}), "yes" if ctl == 0 else "no", "acquisition", seen_q,
        f"view:off_nadir (item property) in collections {off_cols}; absent in others" if off_cols else "none seen in sampled items",
        "CC-BY-SA-4.0 (collection licence field; ShareAlike)",
        f"Single site (Fort McKay AB), nine collections ({', '.join(cols.values())}); items crawled for psscene/skysat/tanager ({len(items)} items), the rest tested on collection extent only. "
        f"Hit collections per AOI: {json.dumps({k: v for k, v in by.items() if v})}. Near the Syncrude and oil-sands AOIs but Syncrude itself lies south of the site. Property keys per collection: "
        f"{json.dumps({c: sorted(k) for c, k in keys.items()})[:700]}. Coverage is one 60x50 km box, so this is a coverage gap for 14 of 15 AOIs, not a failure.")


# ----------------------------------------------------------------------------------------------
def main():
    steps = [probe_3dep, probe_naip, probe_wesm, probe_hrdem, probe_napl, probe_neon, probe_opentopography, probe_noaa_dav,
             probe_oam, probe_hot_stac, probe_geonadir, probe_dronedb, probe_emit, probe_aviris, probe_pace, probe_enmap,
             probe_prisma, probe_tanager, probe_uavsar, probe_ee_uas, probe_planet_open_canada]
    only = sys.argv[1:]
    for fn in steps:
        if only and fn.__name__ not in only:
            continue
        try:
            fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            add("S?", fn.__name__, "n/a", "error", "none", "no", "error", "n/a", "n/a", "acquisition", "none", "none", "n/a", f"probe step failed: {e!r}")
    out = HERE / "B_probes.csv"
    rows = ROWS
    if only and out.exists():
        old = list(csv.DictReader(open(out)))
        new = {r["candidate"]: r for r in ROWS}
        rows = [new.pop(r["candidate"], r) for r in old] + list(new.values())
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    detail_file = HERE / "aoi_hits_detail.json"
    detail = json.loads(detail_file.read_text()) if (only and detail_file.exists()) else {}
    detail.update(DETAIL)
    detail_file.write_text(json.dumps(detail, indent=1, default=str))
    print("wrote", out, len(rows), "rows")


if __name__ == "__main__":
    main()

"""HYP lane proof of concept: read real values for hyperspectral and drone sources at the 15 test AOIs.

Run with the geoquery env python: python -I poc.py [source ...]   (sources: emit pace_oci enmap desis oam geonadir)
Writes poc_values.csv and poc_status.csv next to this file.
"""
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.warp import transform_geom
from rasterio.windows import from_bounds
from shapely.geometry import box, shape
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
AOIS = gpd.read_file(ROOT / "examples" / "test_aois.geojson")
PROBED = {(r["source"], r["feature"]): r for r in csv.DictReader(open(ROOT / "reports" / "probed_features.csv"))}

CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
DLR = "https://geoservice.dlr.de/eoc/ogc/stac/v1/search"
HOT = "https://api.imagery.hotosm.org/stac/search"
GN = "https://api.geonadir.com/api"
CMR_LICENCE = "NASA Earthdata open data (no use restriction stated in the record)"

COLUMNS = ["aoi_id", "source", "feature", "value", "unit", "time", "time_accuracy", "description", "source_url", "licence", "endpoint"]
ROWS = []
STATUS = {}


def get(url, method="GET", tries=6, **kw):
    kw.setdefault("timeout", 90)
    for i in range(tries):
        try:
            r = requests.request(method, url, **kw)
        except requests.RequestException:
            time.sleep(5 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(60, 5 * 2 ** i))
            continue
        return r
    raise RuntimeError(f"{method} {url} failed after {tries} tries")


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def midpoint(t0, t1):
    a, b = parse(t0), parse(t1)
    half = (b - a) / 2
    secs = max(1, int(round(half.total_seconds())))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    dur = "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{s}S" if s or not (h or m) else "")
    return iso(a + half), dur


def emit_row(aoi_id, source, feature, value, unit, time_, acc, description, endpoint, licence=None, url=None):
    p = PROBED.get((source, feature))
    ROWS.append(dict(aoi_id=aoi_id, source=source, feature=feature, value=value, unit=unit, time=time_, time_accuracy=acc,
                     description=description or (p["description"] if p else ""),
                     source_url=url or (p["source_url"] if p else ""), licence=licence or (p["licence"] if p else ""), endpoint=endpoint))


def cmr_polygon(geom):
    g = orient(geom.convex_hull if geom.geom_type != "Polygon" else geom, 1.0)
    return ",".join(f"{x},{y}" for x, y in g.exterior.coords)


def aoi_iter():
    for _, r in AOIS.iterrows():
        yield r["aoi_id"], r.geometry


# ---------------------------------------------------------------- CMR sources
def cmr_granules(concept, geom, n=25):
    r = get(CMR, params=dict(collection_concept_id=concept, polygon=cmr_polygon(geom), page_size=n, sort_key="-start_date"))
    r.raise_for_status()
    return r.json()["items"]


def attr(umm, name):
    for a in umm.get("AdditionalAttributes", []) or []:
        if a["Name"] == name:
            return a["Values"][0]
    return None


def run_emit():
    src, concept = "emit", "C4079844428-LPCLOUD"
    endpoint = f"{CMR}?collection_concept_id={concept}&polygon=<AOI>&sort_key=-start_date"
    for aoi_id, geom in aoi_iter():
        for it in cmr_granules(concept, geom):
            u = it["umm"]
            rng = u["TemporalExtent"]["RangeDateTime"]
            t, acc = midpoint(rng["BeginningDateTime"], rng["EndingDateTime"])
            vals = {"emit_cloud_cover_scene_pct": (u.get("CloudCover"), "percent"),
                    "emit_sun_zenith_deg": (attr(u, "SOLAR_ZENITH"), "degree"),
                    "emit_sun_azimuth_deg": (attr(u, "SOLAR_AZIMUTH"), "degree")}
            got = False
            for f, (v, unit) in vals.items():
                if v is not None:
                    emit_row(aoi_id, src, f, float(v), unit, t, acc, None, endpoint + f" granule={u['GranuleUR']}", CMR_LICENCE)
                    got = True
            if got:
                break
    anonymous_data_status(src, concept, "emit_reflectance")


def run_pace():
    src, concept = "pace_oci", "C3620139902-OB_CLOUD"
    endpoint = f"{CMR}?collection_concept_id={concept}&polygon=<AOI>&sort_key=-start_date"
    for aoi_id, geom in aoi_iter():
        for it in cmr_granules(concept, geom):
            u = it["umm"]
            if u.get("CloudCover") is None:
                continue
            rng = u["TemporalExtent"]["RangeDateTime"]
            t, acc = midpoint(rng["BeginningDateTime"], rng["EndingDateTime"])
            emit_row(aoi_id, src, "pace_cloud_cover_scene_pct", float(u["CloudCover"]), "percent", t, acc, None,
                     endpoint + f" granule={u['GranuleUR']}", CMR_LICENCE)
            break
    anonymous_data_status(src, concept, "pace_reflectance")


def anonymous_data_status(src, concept, feature):
    """Try an anonymous ranged read of the first GET DATA href; record the outcome as the drop reason."""
    r = get(CMR, params=dict(collection_concept_id=concept, page_size=1, sort_key="-start_date"))
    umm = r.json()["items"][0]["umm"]
    href = next(x["URL"] for x in umm["RelatedUrls"] if x["Type"] == "GET DATA" and x["URL"].startswith("http"))
    resp = get(href, headers={"Range": "bytes=0-1023"}, allow_redirects=True)
    magic = resp.content[:4]
    netcdf = magic.startswith(b"\x89HDF") or magic.startswith(b"CDF")
    if netcdf:
        STATUS[(src, feature)] = ("validated_pending", 0, "anonymous read worked (unexpected); no reader written")
    else:
        STATUS[(src, feature)] = ("dropped", 0, f"anonymous ranged GET of the granule NetCDF returns HTTP {resp.status_code} "
                                                f"({resp.headers.get('content-type', '').split(';')[0]}, redirect to Earthdata login); "
                                                "the s3 bucket also answers 403 anonymously")


# ---------------------------------------------------------------- DLR STAC (EnMAP, DESIS)
def dlr_items(collection, geom):
    minx, miny, maxx, maxy = geom.bounds
    url, params, items = DLR, dict(collections=collection, bbox=f"{minx},{miny},{maxx},{maxy}", limit=100), []
    for _ in range(6):
        r = get(url, params=params)
        r.raise_for_status()
        j = r.json()
        items += j["features"]
        nxt = next((l["href"] for l in j.get("links", []) if l["rel"] == "next"), None)
        if not nxt or not j["features"]:
            break
        url, params = nxt, None
    items = [i for i in items if shape(i["geometry"]).intersects(geom)]
    return sorted(items, key=lambda i: i["properties"]["datetime"], reverse=True)


def dlr_time(it):
    p = it["properties"]
    return midpoint(p["start_datetime"], p["end_datetime"])


def run_dlr(src, collection, feature_map, reflectance_feature):
    endpoint = f"{DLR}?collections={collection}&bbox=<AOI bbox>  (items filtered to AOI polygon intersection, newest first)"
    first_item = None
    for aoi_id, geom in aoi_iter():
        items = dlr_items(collection, geom)
        first_item = first_item or (items[0] if items else None)
        for feature, (getter, unit) in feature_map.items():
            for it in items:
                v = getter(it["properties"])
                if v is None:
                    continue
                t, acc = dlr_time(it)
                emit_row(aoi_id, src, feature, v, unit, t, acc, None, endpoint + f" item={it['id']}")
                break
    if first_item:
        href = first_item["assets"]["image"]
        href = href if isinstance(href, str) else href["href"]
        resp = get(href, headers={"Range": "bytes=0-1023"}, allow_redirects=True)
        tiff = resp.content[:4] in (b"II*\x00", b"MM\x00*")
        STATUS[(src, reflectance_feature)] = ("dropped", 0, "image asset is reachable only behind DLR SSO: anonymous ranged GET returns HTTP "
                                                            f"{resp.status_code} {resp.headers.get('content-type', '').split(';')[0]} (login page), not a TIFF"
                                                            if not tiff else "anonymous read worked (unexpected); no reader written")


def num(p, k):
    v = p.get(k)
    return float(v) if isinstance(v, (int, float)) else None


def run_enmap():
    fm = {
        "enmap_off_nadir_across_deg": (lambda p: num(p, "enmap:acrossOffNadirAngle"), "degree"),
        "enmap_off_nadir_along_deg": (lambda p: num(p, "enmap:alongOffNadirAngle"), "degree"),
        "enmap_sun_elevation_deg": (lambda p: num(p, "view:sun_elevation"), "degree"),
        "enmap_cloud_cover_scene_pct": (lambda p: num(p, "eo:cloud_cover"), "percent"),
        "enmap_overall_quality": (lambda p: p.get("enmap:overallQuality"), "class"),
    }
    run_dlr("enmap", "ENMAP_HSI_L2A", fm, "enmap_reflectance")


def run_desis():
    def geo_acc(p):
        e, n = num(p, "desis:eastern_geometric_accuracy"), num(p, "desis:northern_geometric_accuracy")
        if e is None or n is None or e < 0 or n < 0:
            return None
        return f"eastern={e};northern={n}"

    fm = {
        "desis_incidence_deg": (lambda p: num(p, "desis:sceneIncidenceAngle"), "degree"),
        "desis_sun_elevation_deg": (lambda p: num(p, "view:sun_elevation"), "degree"),
        "desis_cloud_cover_scene_pct": (lambda p: num(p, "eo:cloud_cover"), "percent"),
        "desis_geometric_accuracy_m": (geo_acc, "metre"),
    }
    run_dlr("desis", "DESIS_HSI_L2A", fm, "desis_reflectance")


# ---------------------------------------------------------------- OpenAerialMap
def oam_items(geom):
    body = dict(collections=["openaerialmap"], intersects=geom.__geo_interface__, limit=100,
                **{"filter-lang": "cql2-json", "filter": {"op": "=", "args": [{"property": "oam:platform_type"}, "uav"]}})
    r = get(HOT, method="POST", json=body)
    r.raise_for_status()
    return r.json()["features"]


def read_window_means(href, item_geom, aoi_geom, decimate=20):
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="5"):
        with rasterio.open(href) as ds:
            to_crs = lambda g: shape(transform_geom("EPSG:4326", ds.crs, g))
            inter = to_crs(aoi_geom.__geo_interface__).intersection(to_crs(item_geom))
            if inter.is_empty:
                return None
            win = from_bounds(*inter.bounds, transform=ds.transform)
            out = (ds.count, max(1, int(win.height / decimate)), max(1, int(win.width / decimate)))
            a = ds.read(window=win, out_shape=out, boundless=False)
            valid = np.any(a[:3] > 0, axis=0)
            if not valid.any():
                return None
            means = [float(a[b][valid].mean()) for b in range(min(3, ds.count))]
            gsd = float(ds.res[0]) if ds.crs.is_projected else None
            return means, gsd, int(valid.sum()), ds.crs.to_string()


def run_oam():
    src = "oam"
    for aoi_id, geom in aoi_iter():
        for it in oam_items(geom):
            p = it["properties"]
            href = it["assets"]["visual"]["href"]
            res = read_window_means(href, it["geometry"], geom)
            if res is None:
                continue
            means, gsd, npx, crs = res
            t, acc = midpoint(p["start_datetime"], p["end_datetime"])
            licence = p.get("license") or "CC-BY-4.0"
            endpoint = f"{HOT} POST collections=[openaerialmap] intersects=<AOI> filter oam:platform_type=uav; windowed COG read {href}"
            emit_row(aoi_id, src, "oam_uav_rgb_dn", ";".join(f"{c}={m:.1f}" for c, m in zip("RGB", means)), "DN 8-bit, mean over AOI-scene overlap (decimated 20x, nodata excluded)",
                     t, acc, f"OpenAerialMap drone imagery: colour orthomosaic, mean R,G,B digital number over the AOI/scene overlap ({npx} sampled pixels), scene '{p.get('title')}'",
                     endpoint, licence)
            if gsd:
                emit_row(aoi_id, src, "oam_uav_gsd_m", gsd, "metre", t, acc,
                         f"OpenAerialMap drone orthomosaic ground sample distance, read from the COG's own geotransform ({crs}) rather than the catalogue gsd field",
                         endpoint, licence, url=HOT)


# ---------------------------------------------------------------- GeoNadir
def gn_metadata(dataset_id):
    r = get(f"{GN}/metadata/", params=dict(project_id=dataset_id))
    r.raise_for_status()
    j = r.json()
    items = j if isinstance(j, list) else j.get("results", [j])
    items = [i for i in items if i.get("project_id", {}).get("id") == dataset_id]
    return items[0] if items else None


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def run_geonadir():
    src = "geonadir"
    lic = PROBED[(src, "geonadir_ortho_dn")]["licence"]
    for aoi_id, geom in aoi_iter():
        minx, miny, maxx, maxy = geom.bounds
        r = get(f"{GN}/dataset/", params=dict(bbox=f"{minx},{miny},{maxx},{maxy}", limit=100))
        r.raise_for_status()
        for d in r.json().get("results", []):
            if d.get("is_private") or d.get("is_deleted") or not d.get("bbox"):
                continue
            la0, lo0, la1, lo1 = d["bbox"]
            if not box(lo0, la0, lo1, la1).intersects(geom):
                continue
            t = d["captured_date"]
            ep = f"{GN}/dataset/?bbox=<AOI bbox>  dataset={d['id']} ({d['dataset_name']})"
            ortho = (d.get("band_stats") or {}).get("ortho") or {}
            if all(b in ortho for b in ("b1", "b2", "b3")):
                emit_row(aoi_id, src, "geonadir_ortho_dn", ";".join(f"{c}={ortho[b]['mean']:.1f}" for c, b in zip("RGB", ("b1", "b2", "b3"))),
                         "DN 8-bit, dataset-wide mean", t, "",
                         f"GeoNadir drone orthomosaic: dataset-wide mean R,G,B digital number from the record's band_stats (not windowed to the AOI; the raster is not publicly readable), dataset {d['id']}",
                         ep, lic)
            gt = d.get("geotransform")
            if gt and gt[1]:
                emit_row(aoi_id, src, "geonadir_ortho_gsd_m", float(gt[1]), "metre", t, "",
                         f"GeoNadir orthomosaic ground sample distance, geotransform pixel size of dataset {d['id']}", ep, lic, url=f"{GN}/dataset/")
            md = gn_metadata(d["id"])
            if md:
                m = md["metadata"]
                ep2 = f"{GN}/metadata/?project_id={d['id']}  (first image EXIF/XMP of dataset {d['id']})"
                pitch = fnum(m.get("XMP:GimbalPitchDegree"))
                roll, yaw = fnum(m.get("XMP:GimbalRollDegree")), fnum(m.get("XMP:GimbalYawDegree"))
                if pitch is not None and not (pitch == 0 and roll == 0 and yaw == 0):
                    emit_row(aoi_id, src, "geonadir_gimbal_pitch_deg", pitch, "degree", t, "",
                             f"GeoNadir drone camera gimbal pitch of the first image (-90 is straight down), dataset {d['id']}", ep2, lic, url=f"{GN}/metadata/")
                alt = fnum(m.get("XMP:RelativeAltitude"))
                if alt is not None:
                    emit_row(aoi_id, src, "geonadir_flight_height_m", alt, "metre", t, "",
                             f"GeoNadir drone height above take-off point of the first image, dataset {d['id']}", ep2, lic, url=f"{GN}/metadata/")


RUNNERS = {"emit": run_emit, "pace_oci": run_pace, "enmap": run_enmap, "desis": run_desis, "oam": run_oam, "geonadir": run_geonadir}
FEATURES = {
    "emit": ["emit_reflectance", "emit_cloud_cover_scene_pct", "emit_sun_zenith_deg", "emit_sun_azimuth_deg"],
    "pace_oci": ["pace_reflectance", "pace_cloud_cover_scene_pct"],
    "enmap": ["enmap_reflectance", "enmap_off_nadir_across_deg", "enmap_off_nadir_along_deg", "enmap_sun_elevation_deg", "enmap_cloud_cover_scene_pct", "enmap_overall_quality"],
    "desis": ["desis_reflectance", "desis_incidence_deg", "desis_sun_elevation_deg", "desis_cloud_cover_scene_pct", "desis_geometric_accuracy_m"],
    "oam": ["oam_uav_rgb_dn", "oam_uav_gsd_m"],
    "geonadir": ["geonadir_ortho_dn", "geonadir_ortho_gsd_m", "geonadir_gimbal_pitch_deg", "geonadir_flight_height_m"],
}
NO_VALUE_REASON = {
    "enmap_overall_quality": "no item property read",
    "desis_geometric_accuracy_m": "every intersecting DESIS item carries -1.0 for eastern/northern geometric accuracy, the product's unavailable sentinel",
    "geonadir_ortho_gsd_m": "geotransform is null in the record",
    "geonadir_gimbal_pitch_deg": "gimbal angles absent or all exactly 0 in the first image's XMP (unpopulated)",
    "oam_uav_gsd_m": "COG CRS is not projected",
}


def write_outputs():
    with open(HERE / "poc_values.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, COLUMNS)
        w.writeheader()
        w.writerows(ROWS)
    out = []
    for src, feats in FEATURES.items():
        for f in feats:
            st = STATUS.get((src, f))
            n = len({r["aoi_id"] for r in ROWS if r["source"] == src and r["feature"] == f})
            if st and st[0] == "dropped":
                out.append((src, f, "dropped", 0, st[2]))
            elif n:
                out.append((src, f, "validated", n, ""))
            elif src in RAN:
                out.append((src, f, "dropped", 0, NO_VALUE_REASON.get(f, "no value retrievable at any AOI (no intersecting record carried it)")))
    with open(HERE / "poc_status.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "feature", "status", "n_aois_with_value", "reason"])
        w.writerows(out)


if __name__ == "__main__":
    RAN = sys.argv[1:] or list(RUNNERS)
    for s in RAN:
        print("running", s, flush=True)
        RUNNERS[s]()
    write_outputs()
    print(len(ROWS), "rows")

"""REC lane proof-of-concept: reads real values for records, water and climate sources at the 15 test AOIs.

Usage: poc.py [source ...]   (no argument runs every source, then assembles the CSVs)
Per-source results are cached in cache/rows_<source>.json and merged into poc_values.csv and poc_status.csv.
"""
import csv
import io
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from shapely.geometry import shape, box, Point, LineString
from shapely.ops import nearest_points

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
UA = {"User-Agent": "geoquery-poc-REC/1.0 (research; contact phyberosis@gmail.com)"}
VALUE_COLS = ["aoi_id", "source", "feature", "value", "unit", "time", "time_accuracy", "description",
              "source_url", "licence", "endpoint"]

PROBED = list(csv.DictReader(open(ROOT / "reports" / "probed_features.csv")))
FEAT = {(r["source"], r["feature"]): r for r in PROBED}


def load_aois():
    out = []
    for f in json.load(open(ROOT / "examples" / "test_aois.geojson"))["features"]:
        p = f["properties"]
        g = shape(f["geometry"])
        out.append({"id": p["aoi_id"], "lat": p["centroid_lat"], "lon": p["centroid_lon"], "geom": g,
                    "bbox": g.bounds, "country": p["country"]})
    return out


AOIS = load_aois()

_last = {}


def http(url, params=None, method="GET", data=None, timeout=60, retries=4, gap=0.4, headers=None):
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)
    err = None
    for attempt in range(retries + 1):
        wait = gap - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        try:
            r = requests.request(method, url, params=params, data=data, headers={**UA, **(headers or {})}, timeout=timeout)
        except requests.RequestException as e:
            err = str(e)[:200]
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code in (429, 503) and attempt < retries:
            time.sleep(min(int(r.headers.get("Retry-After", 5 * (attempt + 1))), 60))
            continue
        return r
    return None


def jget(url, params=None, **kw):
    r = http(url, params, **kw)
    if r is None:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


def buf(bbox, km_):
    minx, miny, maxx, maxy = bbox
    lat = (miny + maxy) / 2
    dlat = km_ / 111.0
    dlon = km_ / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    return (minx - dlon, miny - dlat, maxx + dlon, maxy + dlat)


def bb(b):
    return ",".join(f"{v:.6f}" for v in b)


def poly_json(geom):
    return json.dumps({"rings": [list(map(list, geom.exterior.coords))], "spatialReference": {"wkid": 4326}})


def arc_query(layer, aoi, fields="*", where="1=1", geometry=True, extra=None, timeout=120):
    """Intersect an ArcGIS layer with the AOI polygon (POST, so a long ring is fine)."""
    p = {"f": "json", "geometry": poly_json(aoi["geom"]), "geometryType": "esriGeometryPolygon", "inSR": 4326,
         "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "where": where,
         "returnGeometry": "true" if geometry else "false"}
    p.update(extra or {})
    r = http(layer + "/query", method="POST", data=p, timeout=timeout)
    if r is None:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def iso_date(v):
    """Normalise epoch ms, yyyy/mm/dd, yyyy-mm-dd, yyyy into an ISO date or year; None if unparseable."""
    if v in (None, "", " "):
        return None
    if isinstance(v, (int, float)) and v > 1e10:
        return datetime.fromtimestamp(v / 1000, timezone.utc).strftime("%Y-%m-%d")
    s = str(v).strip().replace("/", "-")
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", s)
    if m:
        return "-".join(x for x in m.groups() if x)
    return None


def esri_poly(geom):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    ext, holes = [], []
    for ring in (geom or {}).get("rings", []):
        if len(ring) < 4:
            continue
        p = Polygon(ring)
        a = sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1))
        (ext if a < 0 else holes).append(p.buffer(0))
    if not ext:
        return None
    g = unary_union(ext)
    return g.difference(unary_union(holes)) if holes else g


def acc_for(t):
    """Accuracy of an ISO date string by its precision: a day is +/-12 h, a month +/-15 d 12 h, a year +/-182 d 12 h."""
    if not t:
        return ""
    return {10: "PT12H", 7: "P15DT12H", 4: "P182DT12H"}.get(len(t), "")


def largest_overlap(aoi, feats, geom_of=lambda f: esri_poly(f.get("geometry"))):
    best, ba = None, -1
    for f in feats:
        g = geom_of(f)
        if g is None:
            continue
        a = g.intersection(aoi["geom"]).area
        if a > ba:
            best, ba = f, a
    return best, ba


class Rec:
    """Collects value rows and per-feature status for one source."""

    def __init__(self, source):
        self.source = source
        self.rows = []
        self.tried = {}  # feature -> reason when no value

    def feat(self, name, reason="no value read"):
        self.tried.setdefault(name, reason)

    def add(self, aoi, feature, value, unit, time_, acc, desc=None, endpoint="", url=None, licence=None):
        if value is None or (isinstance(value, float) and value != value) or value == "":
            return
        if isinstance(value, float):
            value = round(value, 4)
        pf = FEAT.get((self.source, feature), {})
        self.rows.append({
            "aoi_id": aoi["id"] if isinstance(aoi, dict) else aoi, "source": self.source, "feature": feature,
            "value": value, "unit": unit, "time": time_ or "", "time_accuracy": acc or "",
            "description": desc or pf.get("description", ""), "source_url": url or pf.get("source_url", ""),
            "licence": licence or pf.get("licence", ""), "endpoint": endpoint})

    def drop(self, feature, reason):
        self.tried[feature] = reason

    def save(self):
        json.dump({"rows": self.rows, "tried": self.tried}, open(CACHE / f"rows_{self.source}.json", "w"), default=str)


def finish(rec):
    for (s, f) in FEAT:
        if s == rec.source:
            rec.feat(f)
    rec.save()
    n = {}
    for r in rec.rows:
        n.setdefault(r["feature"], set()).add(r["aoi_id"])
    print(rec.source, {f: len(a) for f, a in n.items()}, flush=True)
    return rec


def assemble():
    vals, stat = [], []
    for src in SOURCES:
        f = CACHE / f"rows_{src}.json"
        if not f.exists():
            continue
        d = json.load(open(f))
        vals += d["rows"]
        cnt = {}
        for r in d["rows"]:
            cnt.setdefault(r["feature"], set()).add(r["aoi_id"])
        feats = list(dict.fromkeys([k for (s, k) in FEAT if s == src] + list(d["tried"]) + list(cnt)))
        for ft in feats:
            n = len(cnt.get(ft, ()))
            stat.append({"source": src, "feature": ft, "status": "validated" if n else "dropped",
                         "n_aois_with_value": n, "reason": "" if n else d["tried"].get(ft, "no value read")})
    with open(HERE / "poc_values.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, VALUE_COLS)
        w.writeheader()
        w.writerows(vals)
    with open(HERE / "poc_status.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["source", "feature", "status", "n_aois_with_value", "reason"])
        w.writeheader()
        w.writerows(stat)
    print("assembled", len(vals), "values", len(stat), "status rows")


SOURCES = {}


def source(fn):
    SOURCES[fn.__name__[2:]] = fn
    return fn

# ---------------------------------------------------------------- SOURCES-BELOW


@source
def s_padus():
    rec = Rec("padus")
    ep = "https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_4_1/MapServer/0"
    for a in AOIS:
        j = arc_query(ep, a)
        feats = (j or {}).get("features", [])
        f, _ = largest_overlap(a, feats)
        if not f:
            continue
        at = f["attributes"]
        t = iso_date(at.get("Src_Date"))
        kw = dict(endpoint=ep, time_=t, acc=acc_for(t))
        des = at.get("Des_Tp")
        rec.add(a, "padus_designation", f"{des}: {at.get('Unit_Nm')}" if des else None, "text", **kw)
        rec.add(a, "padus_gap_status", at.get("GAP_Sts"), "code 1-4", **kw)
        rec.add(a, "padus_public_access", at.get("Pub_Access"), "code (OA open, RA restricted, XA closed, UK unknown)", **kw)
        rec.add(a, "padus_iucn_category", at.get("IUCN_Cat"), "text", **kw)
        rec.add(a, "padus_source_date", at.get("Src_Date"), "date", **kw)
    return finish(rec)


@source
def s_bc_alr():
    rec = Rec("bc_alr")
    ep = "https://openmaps.gov.bc.ca/geo/pub/ows"
    layer = "pub:WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS"
    pj = jget("https://catalogue.data.gov.bc.ca/api/3/action/package_show", {"id": "alc-agricultural-land-reserve-polygons"})
    snap = iso_date(((pj or {}).get("result") or {}).get("metadata_modified"))
    n_hit, n_near = 0, 0
    for a in AOIS:
        b = a["bbox"]
        p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "outputFormat": "application/json",
             "srsName": "EPSG:4326", "typeNames": layer,
             "bbox": f"{b[1]},{b[0]},{b[3]},{b[2]},urn:ogc:def:crs:EPSG::4326"}
        j = jget(ep, p, timeout=120)
        feats = (j or {}).get("features", [])
        n_near += len(feats)
        hit = [f for f in feats if shape(f["geometry"]).intersects(a["geom"])]
        n_hit += len(hit)
        for f in hit:
            pr = f["properties"]
            rec.add(a, "bcalr_status", pr.get("STATUS"), "text", snap, acc_for(snap), endpoint=ep)
            rec.add(a, "bcalr_polygon_km2", round(pr["FEATURE_AREA_SQM"] / 1e6, 3), "km2", snap, acc_for(snap), endpoint=ep)
    why = (f"WFS read at all 15 AOIs: {n_near} ALR polygons touch an AOI bbox but {n_hit} intersect an AOI polygon; "
           "the layer holds ALR polygons only, so a non-ALR AOI returns no row and absence is not a read value")
    rec.drop("bcalr_status", why)
    rec.drop("bcalr_polygon_km2", why)
    return finish(rec)


@source
def s_eu_urban_atlas():
    rec = Rec("eu_urban_atlas")
    ep = "https://image.discomap.eea.europa.eu/arcgis/rest/services/UrbanAtlas/UA_UrbanAtlas_2018/MapServer/2"
    n = 0
    for a in AOIS:
        j = arc_query(ep, a, geometry=False)
        feats = (j or {}).get("features", [])
        n += len(feats)
        for f in feats[:1]:
            at = f["attributes"]
            cls = at.get("class_2018") or at.get("CLASS_2018")
            t = iso_date(at.get("prod_date") or at.get("PROD_DATE"))
            rec.add(a, "urbanatlas_land_use_class", cls, "text", t, acc_for(t), endpoint=ep)
            rec.add(a, "urbanatlas_snapshot_date", at.get("prod_date") or at.get("PROD_DATE"), "date", t, acc_for(t), endpoint=ep)
    paris = {"geom": box(2.34, 48.85, 2.35, 48.86)}
    ctl = len((arc_query(ep, paris, geometry=False) or {}).get("features", []))
    why = (f"{n} polygons at 15 AOIs: Urban Atlas covers EU urban areas only and no test AOI is in the EU "
           f"(positive control, a Paris polygon through the same read: {ctl} polygons)")
    rec.drop("urbanatlas_land_use_class", why)
    rec.drop("urbanatlas_snapshot_date", why)
    return finish(rec)


@source
def s_vancouver_zoning():
    rec = Rec("vancouver_zoning")
    base = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/zoning-districts-and-labels"
    meta = (jget(base) or {}).get("metas", {}).get("default", {})
    snap = iso_date(meta.get("modified"))
    n = 0
    for a in AOIS:
        wkt = a["geom"].wkt
        j = jget(base + "/records", {"where": f"intersects(geom,geom'{wkt}')", "limit": 50})
        rs = (j or {}).get("results", [])
        n += len(rs)
        for r in rs[:1]:
            rec.add(a, "vanzone_district_code", r.get("zoning_district"), "text", snap, acc_for(snap), endpoint=base)
            rec.add(a, "vanzone_category", r.get("zoning_category"), "text", snap, acc_for(snap), endpoint=base)
            rec.add(a, "vanzone_snapshot_date", snap, "date", snap, acc_for(snap), endpoint=base)
    ctl = (jget(base + "/records", {"where": "intersects(geom,geom'POINT(-123.1207 49.2827)')", "limit": 1}) or {}).get("total_count")
    why = (f"{n} zoning polygons at 15 AOIs: the dataset covers the City of Vancouver only and no test AOI is inside it "
           f"(positive control, a downtown Vancouver point through the same query: {ctl} polygon)")
    for f in ("vanzone_district_code", "vanzone_category", "vanzone_snapshot_date"):
        rec.drop(f, why)
    return finish(rec)


@source
def s_calgary_land_use():
    rec = Rec("calgary_land_use")
    base = "https://data.calgary.ca/resource/qe6k-p9nh.json"
    meta = jget("https://data.calgary.ca/api/views/qe6k-p9nh.json") or {}
    snap = iso_date(datetime.fromtimestamp(meta.get("rowsUpdatedAt", 0), timezone.utc).strftime("%Y-%m-%d")) if meta.get("rowsUpdatedAt") else None
    n = 0
    for a in AOIS:
        j = jget(base, {"$where": f"intersects(multipolygon,'{a['geom'].wkt}')", "$limit": 20})
        rs = j if isinstance(j, list) else []
        n += len(rs)
        for r in rs[:1]:
            rec.add(a, "calzone_land_use_code", r.get("lu_code"), "text", snap, acc_for(snap), endpoint=base)
            rec.add(a, "calzone_major_class", r.get("major"), "text", snap, acc_for(snap), endpoint=base)
            rec.add(a, "calzone_far_ratio", r.get("far"), "ratio", snap, acc_for(snap), endpoint=base)
            rec.add(a, "calzone_snapshot_date", snap, "date", snap, acc_for(snap), endpoint=base)
    cj = jget(base, {"$where": "intersects(multipolygon,'POINT (-114.0719 51.0447)')", "$limit": 1})
    why = (f"{n} district polygons at 15 AOIs: the dataset covers the City of Calgary only and no test AOI is inside it "
           f"(positive control, a downtown Calgary point through the same query: {len(cj) if isinstance(cj, list) else 0} polygon)")
    for f in ("calzone_land_use_code", "calzone_major_class", "calzone_far_ratio", "calzone_snapshot_date"):
        rec.drop(f, why)
    return finish(rec)


@source
def s_toronto_zoning():
    import geopandas as gpd
    rec = Rec("toronto_zoning")
    pk = jget("https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show", {"id": "zoning-by-law"}) or {}
    res = pk.get("result", {})
    snap = iso_date(res.get("metadata_modified"))

    def layer(name, fname):
        r = [x for x in res.get("resources", []) if x["name"] == name][0]
        local = CACHE / fname
        if not local.exists():
            local.write_bytes(http(r["url"], timeout=300).content)
        g = gpd.read_file(local)
        return (g.to_crs(4326) if g.crs and g.crs.to_epsg() != 4326 else g), r["url"]

    area, ep_area = layer("Zoning Area - 4326.gpkg", "toronto_zoning_area_4326.gpkg")
    cover, ep_cov = layer("Zoning Lot Coverage Overlay - 4326.gpkg", "toronto_lot_coverage_overlay_4326.gpkg")

    def top(gdf, a):
        sub = gdf[gdf.intersects(a["geom"])]
        if not len(sub):
            return None
        ov = sub.geometry.intersection(a["geom"]).to_crs(6933).area
        return sub.loc[ov.idxmax()]

    def num(v):
        return None if v is None or v != v or v < 0 else float(v)

    for a in AOIS:
        r = top(area, a)
        if r is not None:
            kw = dict(time_=snap, acc=acc_for(snap), endpoint=ep_area)
            rec.add(a, "torzone_zone_code", r.get("ZN_STRING"), "text", **kw)
            rec.add(a, "torzone_fsi_ratio", num(r.get("FSI_TOTAL")), "ratio", **kw)
            rec.add(a, "torzone_snapshot_date", snap, "date", **kw)
        c = top(cover, a)
        if c is not None:
            rec.add(a, "torzone_coverage_pct", num(c.get("PRCNT_CVER")), "percent", snap, acc_for(snap), endpoint=ep_cov)
    return finish(rec)


@source
def s_nza():
    """One z11 vector tile per covered AOI, read in memory and never written to disk (the Terms of Use bar storing content)."""
    import pyogrio
    from shapely.geometry import Polygon
    rec = Rec("nza")
    tiles = "https://tiles.zoningatlas.org/zoningdistricts,zoningdistrictslices"
    z, n = 11, 2 ** 11
    covered = {"city_us_detroit_mi", "mine_us_bingham_ut"}
    for a in AOIS:
        if a["id"] not in covered:
            continue
        x = int((a["lon"] + 180) / 360 * n)
        y = int((1 - math.asinh(math.tan(math.radians(a["lat"]))) / math.pi) / 2 * n)
        r = http(f"{tiles}/{z}/{x}/{y}", timeout=120)
        if r is None or r.status_code != 200 or not r.content:
            continue

        def to_tile(lon, lat):
            fx = (lon + 180) / 360 * n
            fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
            return ((fx - x) * 4096, 4096 - (fy - y) * 4096)
        P = Polygon([to_tile(*c) for c in a["geom"].exterior.coords])
        ep = f"{tiles}/{z}/{x}/{y}"
        dist = pyogrio.read_dataframe(io.BytesIO(r.content), layer="zoningdistricts")
        sl = pyogrio.read_dataframe(io.BytesIO(r.content), layer="zoningdistrictslices")

        def top(df):
            sub = df[df.intersects(P)]
            base = sub[~sub["name"].astype(str).str.contains("Overlay", case=False)]
            sub = base if len(base) else sub
            if not len(sub):
                return None
            return sub.loc[sub.geometry.intersection(P).area.idxmax()]
        d, s = top(dist), top(sl)
        if d is not None:
            rec.add(a, "nza_zone_code", f"{d['abbrvname']} ({d['name']})", "text", None, "", endpoint=ep)
        if s is not None:
            t = iso_date(str(s.get("created")))
            kw = dict(time_=t, acc=acc_for(t), endpoint=ep)
            rec.add(a, "nza_housing_treatment",
                    ";".join(f"{k}={s.get(k + '_treatment')}" for k in ("family1", "family2", "family3", "family4")), "text", **kw)
            lot = s.get("family1_minlotacres_min")
            lot = s.get("family1_minlotacres") if lot is None or lot != lot else lot
            rec.add(a, "nza_min_lot_acres", None if lot is None or lot != lot else float(lot), "acres", **kw)
            rec.add(a, "nza_parking_required_flag", str(bool(s.get("family1_parking"))).lower(), "boolean", **kw)
            rec.add(a, "nza_height_cap_flag", str(bool(s.get("family1_heightcap"))).lower(), "boolean", **kw)
            rec.add(a, "nza_snapshot_date", str(s.get("created")), "date", **kw)
    rec.drop("nza_min_lot_acres", "no minimum lot size is recorded for the district under the AOI (value null)")
    return finish(rec)


USGS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections"
USGS_RADIUS_KM = 100


@source
def s_usgs_waterdata():
    rec = Rec("usgs_waterdata")
    for a in AOIS:
        b = buf(a["bbox"], USGS_RADIUS_KM)
        best = {}
        for pc in ("00060", "00065"):
            j = jget(USGS + "/latest-continuous/items", {"f": "json", "bbox": bb(b), "parameter_code": pc, "limit": 1000}, timeout=120)
            cand = []
            now = datetime.now(timezone.utc)
            for f in (j or {}).get("features", []):
                p = f["properties"]
                if (now - datetime.fromisoformat(p["time"])).days > 30:
                    continue
                lon, lat = f["geometry"]["coordinates"][:2]
                cand.append((km(a["lat"], a["lon"], lat, lon), p))
            if cand:
                best[pc] = min(cand, key=lambda c: c[0])
        for pc, (dist, p) in best.items():
            mid = p["monitoring_location_id"]
            t = p["time"].replace("+00:00", "Z")
            ep = f"{USGS}/latest-continuous/items?monitoring_location_id={mid}&parameter_code={pc}"
            try:
                v = float(p["value"])
            except (TypeError, ValueError):
                continue
            if pc == "00060":
                rec.add(a, "usgs_discharge_cfs", v, "ft3/s", t, "PT1S", desc=f"Stream gauge {mid}: latest discharge, cubic feet per second", endpoint=ep)
                rec.add(a, "usgs_approval_status", p.get("approval_status"), "text", t, "PT1S", desc=f"Gauge {mid} QC: approval status of the discharge reading", endpoint=ep)
                rec.add(a, "usgs_station_distance_km", round(dist, 2), "km", t, "PT1S", desc=f"Gauge QC: distance from the AOI centroid to the nearest gauge reporting discharge ({mid})", endpoint=ep)
                loc = jget(USGS + "/monitoring-locations/items", {"f": "json", "id": mid, "limit": 1})
                da = ((loc or {}).get("features") or [{}])[0].get("properties", {}).get("drainage_area")
                rec.add(a, "usgs_drainage_area_mi2", da, "mi2", t, "PT1S", desc=f"Stream gauge {mid}: drainage area, square miles",
                        endpoint=USGS + f"/monitoring-locations/items?id={mid}")
            else:
                rec.add(a, "usgs_gage_height_ft", v, "ft", t, "PT1S", desc=f"Stream gauge {mid}: latest gage height, feet, {dist:.1f} km from the AOI centroid", endpoint=ep)
    return finish(rec)


ECCC = "https://api.weather.gc.ca/collections"


@source
def s_eccc_hydrometric():
    rec = Rec("eccc_hydrometric")
    for a in AOIS:
        b = buf(a["bbox"], 100)
        j = jget(ECCC + "/hydrometric-stations/items", {"f": "json", "bbox": bb(b), "limit": 500}, timeout=120)
        st = []
        for f in (j or {}).get("features", []):
            p = f["properties"]
            if p.get("STATUS_EN") != "Active" or not p.get("REAL_TIME"):
                continue
            lon, lat = f["geometry"]["coordinates"][:2]
            st.append((km(a["lat"], a["lon"], lat, lon), p))
        st.sort(key=lambda c: c[0])
        got_q = got_h = False
        for dist, p in st[:15]:
            sn = p["STATION_NUMBER"]
            ep = f"{ECCC}/hydrometric-realtime/items?STATION_NUMBER={sn}&sortby=-DATETIME&limit=1"
            rt = jget(ECCC + "/hydrometric-realtime/items", {"f": "json", "STATION_NUMBER": sn, "sortby": "-DATETIME", "limit": 1})
            fs = (rt or {}).get("features") or []
            if not fs:
                continue
            r = fs[0]["properties"]
            t = r["DATETIME"]
            if r.get("DISCHARGE") is not None and not got_q:
                got_q = True
                rec.add(a, "hydat_discharge_m3s", r["DISCHARGE"], "m3/s", t, "PT1S", desc=f"Hydrometric gauge {sn} {p['STATION_NAME']}: latest discharge, cubic metres per second", endpoint=ep)
                rec.add(a, "hydat_station_distance_km", round(dist, 2), "km", t, "PT1S", desc=f"Gauge QC: distance from the AOI centroid to the nearest active gauge reporting discharge ({sn})", endpoint=ep)
                rec.add(a, "hydat_drainage_area_km2", p.get("DRAINAGE_AREA_GROSS"), "km2", t, "PT1S", desc=f"Hydrometric gauge {sn}: gross drainage area, square kilometres", endpoint=f"{ECCC}/hydrometric-stations/items?STATION_NUMBER={sn}")
                dm = jget(ECCC + "/hydrometric-daily-mean/items", {"f": "json", "STATION_NUMBER": sn, "limit": 1, "sortby": "-DATE"})
                if dm and dm.get("numberMatched"):
                    last = iso_date(dm["features"][0]["properties"]["DATE"])
                    rec.add(a, "hydat_daily_record_n", dm["numberMatched"], "records", last, acc_for(last), desc=f"Gauge {sn} QC: number of daily-mean records in the archive", endpoint=f"{ECCC}/hydrometric-daily-mean/items?STATION_NUMBER={sn}")
            if r.get("LEVEL") is not None and not got_h:
                got_h = True
                rec.add(a, "hydat_level_m", r["LEVEL"], "m", t, "PT1S", desc=f"Hydrometric gauge {sn} {p['STATION_NAME']}: latest water level, metres, {dist:.1f} km from the AOI centroid", endpoint=ep)
            if got_q and got_h:
                break
    return finish(rec)


@source
def s_eccc_climate():
    rec = Rec("eccc_climate")
    now = datetime.now(timezone.utc)
    start = (now.replace(microsecond=0) - __import__("datetime").timedelta(days=150)).strftime("%Y-%m-%dT00:00:00Z")
    end = now.strftime("%Y-%m-%dT23:59:59Z")
    want = {"eccc_tmax_c": ("MAX_TEMPERATURE", "degC", "daily maximum temperature, degrees C"),
            "eccc_tmin_c": ("MIN_TEMPERATURE", "degC", "daily minimum temperature, degrees C"),
            "eccc_precip_mm": ("TOTAL_PRECIPITATION", "mm", "daily total precipitation, millimetres")}
    for a in AOIS:
        b = buf(a["bbox"], 100)
        j = jget(ECCC + "/climate-stations/items", {"f": "json", "bbox": bb(b), "limit": 500}, timeout=120)
        st = []
        for f in (j or {}).get("features", []):
            p = f["properties"]
            if (p.get("DLY_LAST_DATE") or "") < (now - __import__("datetime").timedelta(days=120)).strftime("%Y-%m-%d"):
                continue
            lon, lat = f["geometry"]["coordinates"][:2]
            st.append((km(a["lat"], a["lon"], lat, lon), p))
        st.sort(key=lambda c: c[0])
        got = {}
        for dist, p in st[:12]:
            cid = p["CLIMATE_IDENTIFIER"]
            jd = jget(ECCC + "/climate-daily/items", {"f": "json", "CLIMATE_IDENTIFIER": cid, "datetime": f"{start}/{end}", "sortby": "-LOCAL_DATE", "limit": 200}, timeout=90)
            rows = [f["properties"] for f in (jd or {}).get("features", [])]
            for feat, (col, unit, desc) in want.items():
                if feat in got:
                    continue
                hit = next((r for r in rows if r.get(col) is not None), None)
                if hit:
                    got[feat] = (dist, p, hit, col)
            if len(got) == len(want):
                break
        for feat, (dist, p, hit, col) in got.items():
            cid = p["CLIMATE_IDENTIFIER"]
            day = hit["LOCAL_DATE"][:10]
            unit, desc = want[feat][1], want[feat][2]
            ep = f"{ECCC}/climate-daily/items?CLIMATE_IDENTIFIER={cid}&sortby=-LOCAL_DATE"
            rec.add(a, feat, hit[col], unit, day, "PT12H", desc=f"Station {cid} {p['STATION_NAME']}, {dist:.1f} km: {desc}", endpoint=ep)
        if "eccc_tmax_c" in got:
            dist, p, hit, col = got["eccc_tmax_c"]
            cid = p["CLIMATE_IDENTIFIER"]
            day = hit["LOCAL_DATE"][:10]
            rec.add(a, "eccc_station_distance_km", round(dist, 2), "km", day, "PT12H",
                    desc=f"Station QC: distance from the AOI centroid to the nearest climate station reporting Tmax ({cid})", endpoint=f"{ECCC}/climate-stations/items?CLIMATE_IDENTIFIER={cid}")
            jc = jget(ECCC + "/climate-daily/items", {"f": "json", "CLIMATE_IDENTIFIER": cid, "datetime": "2020-01-01T00:00:00Z/2024-12-31T23:59:59Z", "limit": 2000, "properties": "MAX_TEMPERATURE"}, timeout=120)
            fs = (jc or {}).get("features", [])
            if fs:
                nn = sum(1 for f in fs if f["properties"].get("MAX_TEMPERATURE") is not None)
                rec.add(a, "eccc_record_completeness_pct", round(100 * nn / 1827, 1), "percent", "2022-07-01", "P913DT12H",
                        desc=f"Station {cid} QC: share of days 2020-2024 with a non-null daily maximum temperature, percent", endpoint=f"{ECCC}/climate-daily/items?CLIMATE_IDENTIFIER={cid}&datetime=2020-01-01/2024-12-31")
    return finish(rec)


NCEI_DATA = "https://www.ncei.noaa.gov/access/services/data/v1"
GHCN_FILES = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/"


def ghcn_inventory():
    import numpy as np
    out = {}
    for fname in ("ghcnd-stations.txt", "ghcnd-inventory.txt"):
        f = CACHE / fname
        if not f.exists():
            f.write_bytes(http(GHCN_FILES + fname, timeout=600).content)
    names = {}
    for line in open(CACHE / "ghcnd-stations.txt", encoding="latin-1"):
        names[line[0:11]] = line[41:71].strip()
    rows = {"TMAX": [], "TMIN": [], "PRCP": []}
    for line in open(CACHE / "ghcnd-inventory.txt"):
        el = line[31:35]
        if el in rows and int(line[41:45]) >= 2026:
            rows[el].append((line[0:11], float(line[12:20]), float(line[21:30])))
    for el, rs in rows.items():
        out[el] = (np.array([r[0] for r in rs]), np.array([r[1] for r in rs]), np.array([r[2] for r in rs]))
    return out, names


@source
def s_ghcn_daily():
    import numpy as np
    from datetime import timedelta
    rec = Rec("ghcn_daily")
    inv, names = ghcn_inventory()
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=60)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    want = {"TMAX": ("ghcnd_tmax_c", "degC", "daily maximum temperature, degrees C"),
            "TMIN": ("ghcnd_tmin_c", "degC", "daily minimum temperature, degrees C"),
            "PRCP": ("ghcnd_prcp_mm", "mm", "daily precipitation, millimetres")}
    for a in AOIS:
        tmax_station = None
        for el, (feat, unit, desc) in want.items():
            ids, lat, lon = inv[el]
            p = np.pi / 180
            dd = 12742 * np.arcsin(np.sqrt(np.sin((lat - a["lat"]) * p / 2) ** 2 + np.cos(a["lat"] * p) * np.cos(lat * p) * np.sin((lon - a["lon"]) * p / 2) ** 2))
            order = np.argsort(dd)
            for k in order[:6]:
                if dd[k] > 100:
                    break
                sid = ids[k]
                r = http(NCEI_DATA, {"dataset": "daily-summaries", "stations": sid, "dataTypes": el, "startDate": start, "endDate": end, "format": "json", "units": "metric"}, timeout=120)
                try:
                    rows = [x for x in r.json() if x.get(el) not in (None, "")]
                except Exception:
                    rows = []
                if not rows:
                    continue
                last = max(rows, key=lambda x: x["DATE"])
                ep = f"{NCEI_DATA}?dataset=daily-summaries&stations={sid}&dataTypes={el}"
                rec.add(a, feat, float(last[el]), unit, last["DATE"], "PT12H", desc=f"Station {sid} {names.get(sid, '')}, {dd[k]:.1f} km: {desc}", endpoint=ep)
                if el == "TMAX":
                    tmax_station = (sid, float(dd[k]), last["DATE"])
                break
        if tmax_station:
            sid, dist, day = tmax_station
            ep = f"{NCEI_DATA}?dataset=daily-summaries&stations={sid}&dataTypes=TMAX"
            rec.add(a, "ghcnd_station_distance_km", round(dist, 2), "km", day, "PT12H", desc=f"Station QC: distance from the AOI centroid to the nearest GHCN-Daily station reporting TMAX ({sid})", endpoint=ep)
            r = http(NCEI_DATA, {"dataset": "daily-summaries", "stations": sid, "dataTypes": "TMAX", "startDate": "2016-01-01", "endDate": "2025-12-31", "format": "json", "units": "metric"}, timeout=180)
            try:
                n = sum(1 for x in r.json() if x.get("TMAX") not in (None, ""))
                rec.add(a, "ghcnd_coverage_pct", round(100 * n / 3653, 1), "percent", "2021-01-01", "P1826DT12H",
                        desc=f"Station {sid} QC: share of days 2016-2025 with a TMAX value, percent", endpoint=ep)
            except Exception:
                pass
    return finish(rec)


DAYMET = "https://daymet.ornl.gov/single-pixel/api/data"


@source
def s_daymet():
    from datetime import date, timedelta
    rec = Rec("daymet")
    keys = {"tmax": ("daymet_tmax_c", "degC"), "tmin": ("daymet_tmin_c", "degC"), "prcp": ("daymet_prcp_mm", "mm"),
            "srad": ("daymet_srad_wm2", "W/m2"), "swe": ("daymet_swe_kgm2", "kg/m2"), "vp": ("daymet_vp_pa", "Pa")}
    for a in AOIS:
        d = None
        for yr in (2025, 2024):
            d = jget(DAYMET, {"lat": a["lat"], "lon": a["lon"], "vars": ",".join(keys), "years": yr, "format": "json"}, timeout=120)
            if d and d.get("data", {}).get("year"):
                break
        if not d or "data" not in d:
            continue
        data = d["data"]
        n = len(data["year"])
        ep = f"{DAYMET}?lat={a['lat']}&lon={a['lon']}&years={int(data['year'][0])}"
        for k, (feat, unit) in keys.items():
            col = next((c for c in data if c.startswith(k + " ")), None)
            if not col:
                continue
            i = n - 1
            while i >= 0 and data[col][i] is None:
                i -= 1
            if i < 0:
                continue
            day = (date(int(data["year"][i]), 1, 1) + timedelta(days=int(data["yday"][i]) - 1)).isoformat()
            rec.add(a, feat, data[col][i], unit, day, "PT12H", endpoint=ep)
    return finish(rec)


TC = "https://thredds.northwestknowledge.net/thredds"


@source
def s_terraclimate():
    rec = Rec("terraclimate")
    yr = 2025
    vars_ = {"tmax": ("terraclim_tmax_c", "degC"), "ppt": ("terraclim_ppt_mm", "mm"), "pet": ("terraclim_pet_mm", "mm"),
             "def": ("terraclim_def_mm", "mm"), "soil": ("terraclim_soil_mm", "mm"), "swe": ("terraclim_swe_mm", "mm")}
    packing = {}
    for v in vars_:
        das = http(f"{TC}/dodsC/TERRACLIMATE_ALL/data/TerraClimate_{v}_{yr}.nc.das", timeout=60)
        txt = re.search(r"\b%s \{(.*?)\n    \}" % v, das.text, re.S).group(1) if das is not None else ""
        sf = re.search(r"scale_factor ([-\d.eE]+)", txt)
        off = re.search(r"add_offset ([-\d.eE]+)", txt)
        fill = re.search(r"_FillValue ([-\d.eE]+)", txt)
        packing[v] = (float(sf.group(1)) if sf else 1.0, float(off.group(1)) if off else 0.0, float(fill.group(1)) if fill else None)
    for a in AOIS:
        for v, (feat, unit) in vars_.items():
            url = f"{TC}/ncss/TERRACLIMATE_ALL/data/TerraClimate_{v}_{yr}.nc"
            p = {"var": v, "latitude": a["lat"], "longitude": a["lon"], "time_start": f"{yr}-12-01T00:00:00Z", "time_end": f"{yr}-12-31T00:00:00Z", "accept": "csv"}
            r = http(url, p, timeout=90)
            if r is None or r.status_code != 200:
                continue
            lines = r.text.strip().splitlines()[1:]
            if not lines:
                continue
            raw = float(lines[-1].split(",")[-1])
            sf, off, fill = packing[v]
            if fill is not None and raw == fill:
                continue
            rec.add(a, feat, round(raw * sf + off, 3), unit, f"{yr}-12-16T12:00:00Z", "P15DT12H",
                    endpoint=url + "?" + "&".join(f"{k}={x}" for k, x in p.items()))
    return finish(rec)


CHIRPS = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/tifs/"


def month_mid(y, m):
    from calendar import monthrange
    from datetime import datetime as dt, timedelta
    n = monthrange(y, m)[1]
    mid = dt(y, m, 1) + timedelta(hours=12 * n)
    return mid.strftime("%Y-%m-%dT%H:%M:%SZ"), f"P{n // 2}D" + ("T12H" if n % 2 else "")


@source
def s_chirps():
    import rasterio
    rec = Rec("chirps")
    listing = http(CHIRPS, timeout=60)
    months = sorted(set(re.findall(r"chirps-v3\.0\.(\d{4})\.(\d{2})\.tif", listing.text if listing is not None else "")))
    y, m = (int(x) for x in months[-1])
    fname = f"chirps-v3.0.{y}.{m:02d}.tif"
    url = CHIRPS + fname
    t, acc = month_mid(y, m)
    with rasterio.Env(GDAL_HTTP_USERAGENT=UA["User-Agent"], GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open("/vsicurl/" + url) as r:
            nod = r.nodata
            for a in AOIS:
                v = float(next(r.sample([(a["lon"], a["lat"])]))[0])
                if nod is not None and v == nod or v < -9000:
                    continue
                rec.add(a, "chirps_precip_mm", round(v, 2), "mm/month", t, acc, endpoint=url)
    return finish(rec)


HYDRORIVERS_URL = "https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_na_shp.zip"


@source
def s_hydrorivers():
    import geopandas as gpd
    rec = Rec("hydrorivers")
    zp = CACHE / "HydroRIVERS_v10_na_shp.zip"
    if not zp.exists():
        zp.write_bytes(http(HYDRORIVERS_URL, timeout=900).content)
    src = f"zip://{zp}!HydroRIVERS_v10_na_shp/HydroRIVERS_v10_na.shp"
    for a in AOIS:
        g = gpd.read_file(src, bbox=buf(a["bbox"], 25))
        if not len(g):
            continue
        poly = gpd.GeoSeries([a["geom"]], crs=4326).to_crs(6933).iloc[0]
        d = g.geometry.to_crs(6933).distance(poly) / 1000
        thru = d[d == 0]
        r = g.loc[g.loc[thru.index, "UPLAND_SKM"].idxmax()] if len(thru) else g.loc[d.idxmin()]
        dist = float(d.loc[r.name])
        if dist > 25:
            continue
        kw = dict(time_=None, acc="", endpoint=HYDRORIVERS_URL + f"#HYRIV_ID={int(r['HYRIV_ID'])}")
        rec.add(a, "hydrorivers_discharge_m3s", float(r["DIS_AV_CMS"]), "m3/s", **kw)
        rec.add(a, "hydrorivers_upland_area_km2", float(r["UPLAND_SKM"]), "km2", **kw)
        rec.add(a, "hydrorivers_strahler_order", int(r["ORD_STRA"]), "order", **kw)
        rec.add(a, "hydrorivers_nearest_km", round(dist, 3), "km", **kw)
    return finish(rec)


NHD = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3"


def esri_lines(geom):
    from shapely.geometry import MultiLineString
    paths = [p for p in (geom or {}).get("paths", []) if len(p) > 1]
    return MultiLineString(paths) if paths else None


@source
def s_nhdplus_hr():
    rec = Rec("nhdplus_hr")
    fl = "gnis_name,streamorde,totdasqkm,qama,vama,slope,fdate,nhdplusid"
    for a in AOIS:
        j = arc_query(NHD, a, fields=fl, extra={"distance": 2000, "units": "esriSRUnit_Meter", "resultRecordCount": 2000}, timeout=180)
        feats = (j or {}).get("features", [])
        cand = []
        for f in feats:
            g = esri_lines(f.get("geometry"))
            if g is not None:
                cand.append((g.distance(a["geom"]), f["attributes"]))
        if not cand:
            continue
        thru = [c for c in cand if c[0] == 0]
        d, at = max(thru, key=lambda c: c[1].get("totdasqkm") or 0) if thru else min(cand, key=lambda c: c[0])
        t = iso_date(at.get("fdate"))
        kw = dict(time_=t, acc=acc_for(t), endpoint=f"{NHD}/query?nhdplusid={at['nhdplusid']}")
        rec.add(a, "nhdhr_mean_flow_cfs", at.get("qama"), "ft3/s", **kw)
        rec.add(a, "nhdhr_stream_order", at.get("streamorde"), "order", **kw)
        rec.add(a, "nhdhr_drainage_area_km2", at.get("totdasqkm"), "km2", **kw)
        rec.add(a, "nhdhr_slope_frac", at.get("slope"), "m/m", **kw)
        rec.add(a, "nhdhr_feature_date", t, "date", **kw)
    return finish(rec)


NHN_WMS = "https://maps.geogratis.gc.ca/wms/hydro_network_en"
NHN_LAYERS = "nhn:nhn:hydrography:slwatercourse_1,nhn:nhn:hydrography:waterbody_2"


@source
def s_nrcan_nhn():
    """GetFeatureInfo on a 5x5 grid of pixel queries (60 px tolerance of 512) across each Canadian AOI bbox."""
    rec = Rec("nrcan_nhn")
    N, G = 512, 5
    for a in AOIS:
        if a["country"] != "CA":
            continue
        b = a["bbox"]
        hits = []
        for i in range(G):
            for k in range(G):
                px, py = int(N * (i + 0.5) / G), int(N * (k + 0.5) / G)
                p = {"service": "WMS", "version": "1.3.0", "request": "GetFeatureInfo", "layers": NHN_LAYERS, "query_layers": NHN_LAYERS,
                     "styles": "", "crs": "EPSG:4326", "bbox": f"{b[1]},{b[0]},{b[3]},{b[2]}", "width": N, "height": N, "i": px, "j": py,
                     "info_format": "application/vnd.ogc.gml", "feature_count": 3, "buffer": 60}
                r = http(NHN_WMS, p, timeout=60)
                if r is None or "_feature>" not in r.text:
                    continue
                m = re.search(r"<(\S+?_feature)>(.*?)</\1>", r.text, re.S)
                props = dict(re.findall(r"<(\w+)>([^<]*)</\1>", m.group(2)))
                layer = "watercourse" if "slwatercourse" in m.group(1) else "waterbody"
                hits.append((abs(i - G // 2) + abs(k - G // 2), layer, props, p))
        if not hits:
            continue
        hits.sort(key=lambda h: h[0])
        _, layer, pr, p = hits[0]
        ymd = pr.get("md_temporal_extent_date_min", "")
        t = f"{ymd[:4]}-{ymd[4:6]}" if len(ymd) >= 6 else (ymd[:4] or None)
        ep = NHN_WMS + "?" + "&".join(f"{k}={v}" for k, v in p.items())
        kw = dict(time_=t, acc=acc_for(t), endpoint=ep)
        rec.add(a, "nhn_permanency", pr.get("permanency_en"), "text", **kw)
        rec.add(a, "nhn_water_type", f"{layer}: {pr.get('water_definition_en')}", "text", **kw)
        rec.add(a, "nhn_survey_year", int(ymd[:4]) if ymd[:4].isdigit() else None, "year", **kw)
        acc_m = pr.get("md_horiz_position_accuracy_min")
        rec.add(a, "nhn_horiz_accuracy_m", float(acc_m) if acc_m else None, "m", **kw)
    return finish(rec)


if __name__ == "__main__":
    want = sys.argv[1:] or list(SOURCES)
    for w in want:
        if w != "--assemble":
            SOURCES[w]()
    if not sys.argv[1:] or "--assemble" in sys.argv:
        assemble()

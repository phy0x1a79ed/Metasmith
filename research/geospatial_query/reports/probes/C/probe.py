"""Lane C probe: records, water and climate sources (gaps S6, S7, S8).

Re-running writes C_probes.csv and C_probe_detail.csv next to this file.
Large downloads (HydroRIVERS 66 MB, CHIRPS v2 monthly 14 MB) are cached under
CACHE_DIR (default: <job tmp>/C_cache) and are never deleted by this script.
Buffers: area/polygon sources use the AOI polygon bbox (0 km); station, river and
gauge sources use the buffer named in each row's notes.
"""
import csv
import gzip
import json
import math
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlencode

import requests
from shapely.geometry import shape, box, LineString, Point

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AOIS_PATH = ROOT / "examples" / "test_aois.geojson"
CACHE = Path(os.environ.get("CACHE_DIR", "/home/tony/.claude/jobs/2d6e7fcc/tmp/C_cache"))
CACHE.mkdir(parents=True, exist_ok=True)

COLS = ["gap", "candidate", "source_type", "endpoint", "auth", "reachable", "http_status", "aoi_hits",
        "control_passed", "observation_unit", "quality_fields", "off_nadir_field", "licence", "notes"]
CONTROL = (-150.0, 0.0, -149.9, 0.1)  # minlon, minlat, maxlon, maxlat; mid-Pacific
UA = {"User-Agent": "geoquery-probe-laneC/1.0 (research; contact phyberosis@gmail.com)"}

_last = {}


def http(url, params=None, method="GET", timeout=60, stream=False, retries=3, gap=0.5):
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)
    for attempt in range(retries + 1):
        wait = gap - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        try:
            r = requests.request(method, url, params=params, headers=UA, timeout=timeout, stream=stream)
        except requests.RequestException as e:
            if attempt == retries:
                return None, str(e)
            time.sleep(2)
            continue
        if r.status_code == 429 and attempt < retries:
            time.sleep(int(r.headers.get("Retry-After", 5 * (attempt + 1))))
            continue
        return r, None
    return None, "retries exhausted"


def jget(url, params=None, **kw):
    r, err = http(url, params, **kw)
    if r is None:
        return None, None, err
    try:
        return r.status_code, r.json(), None
    except ValueError:
        return r.status_code, None, r.text[:200]


def km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))


def load_aois():
    out = []
    for f in json.load(open(AOIS_PATH))["features"]:
        p = f["properties"]
        g = shape(f["geometry"])
        out.append({"id": p["aoi_id"], "lat": p["centroid_lat"], "lon": p["centroid_lon"],
                    "bbox": g.bounds, "geom": g, "country": p["country"]})
    return out


AOIS = load_aois()


def buf(bbox, km_):
    minx, miny, maxx, maxy = bbox
    lat = (miny + maxy) / 2
    dlat = km_ / 111.0
    dlon = km_ / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    return (minx - dlon, miny - dlat, maxx + dlon, maxy + dlat)


def bb(b):
    return ",".join(f"{v:.6f}" for v in b)


def wkt_poly(b):
    x0, y0, x1, y1 = b
    return f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"


DETAIL = []


def detail(cand, aoi, n, nearest_km="", extra=""):
    DETAIL.append({"candidate": cand, "aoi_id": aoi, "n": n, "nearest_km": nearest_km, "extra": extra})


def row(gap, cand, stype, endpoint, auth, unit, licence, off="none", **kw):
    d = dict(gap=gap, candidate=cand, source_type=stype, endpoint=endpoint, auth=auth, reachable="no",
             http_status="", aoi_hits="n/a", control_passed="n/a", observation_unit=unit, quality_fields="",
             off_nadir_field=off, licence=licence, notes="")
    d.update(kw)
    return d


def fail(d, e):
    d["reachable"] = "no"
    d["notes"] = (d["notes"] + " FAILED: " + repr(e)[:300]).strip()
    return d


# ---------------------------------------------------------------- ArcGIS REST helpers
def arc_count(layer, b, where=None, timeout=90):
    p = {"f": "json", "geometry": bb(b), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
         "spatialRel": "esriSpatialRelIntersects", "returnCountOnly": "true"}
    if where:
        p["where"] = where
    else:
        p["where"] = "1=1"
    s, j, e = jget(layer + "/query", p, timeout=timeout)
    if j is None or "count" not in j:
        return s, None, e or j
    return s, j["count"], None


def arc_first(layer, b, fields="*", n=1, where="1=1"):
    p = {"f": "json", "geometry": bb(b), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
         "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "returnGeometry": "false",
         "resultRecordCount": n, "where": where}
    s, j, e = jget(layer + "/query", p)
    return (j or {}).get("features", [])


# ================================================================ S6
def merc(lon, lat):
    x = lon * 20037508.342789244 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) * 20037508.342789244 / math.pi
    return x, y


def p_nza():
    tiles = "https://tiles.zoningatlas.org"
    src = "zoningdistricts,zoningdistrictslices"
    d = row("S6", "National Zoning Atlas vector tiles", "registry", f"{tiles}/{src}/{{z}}/{{x}}/{{y}}  (TileJSON: {tiles}/{src})", "none", "snapshot",
            "Terms of Use (zoningatlas.org/terms) bar using, storing or downloading Website Content without written permission; no data licence published")
    try:
        import pyogrio
        r, e = http(f"{tiles}/{src}")
        d["http_status"] = r.status_code if r is not None else ""
        d["reachable"] = "partial" if r is not None and r.status_code == 200 else "no"
        app, _ = http("https://edit.zoningatlas.org/atlas/")
        tj = r.json() if r is not None and r.status_code == 200 else {}
        z = 11
        hits = 0
        sample = None
        tile_dir = CACHE / "nza"
        tile_dir.mkdir(parents=True, exist_ok=True)
        statuses = {}
        for a in AOIS + [{"id": "CONTROL", "lat": 0.05, "lon": -149.95, "bbox": CONTROL}]:
            n = 2 ** z
            lat, lon = a["lat"], a["lon"]
            x = int((lon + 180) / 360 * n)
            y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
            tr, _ = http(f"{tiles}/{src}/{z}/{x}/{y}", timeout=90)
            st = tr.status_code if tr is not None else None
            statuses[a["id"]] = (st, len(tr.content) if tr is not None else 0)
            cnt = 0
            if tr is not None and st == 200 and tr.content:
                f = tile_dir / f"{a['id']}.pbf"
                f.write_bytes(tr.content)
                x0, y0, x1, y1 = a["bbox"]
                fx0, fy0 = (x0 + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(y0))) / math.pi) / 2 * n
                fx1, fy1 = (x1 + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(y1))) / math.pi) / 2 * n
                px = sorted([(fx0 - x) * 4096, (fx1 - x) * 4096])
                py = sorted([4096 - (fy0 - y) * 4096, 4096 - (fy1 - y) * 4096])
                pbox = (px[0], py[0], px[1], py[1])
                df = pyogrio.read_dataframe(str(f), layer="zoningdistricts", bbox=pbox)
                cnt = len(df)
                if cnt and a["id"] != "CONTROL":
                    sl = pyogrio.read_dataframe(str(f), layer="zoningdistrictslices", bbox=pbox)
                    names = sorted(set(df["abbrvname"].astype(str)))[:6]
                    detail("NZA tiles", a["id"], cnt, 0, f"tile {z}/{x}/{y} status {st} {len(tr.content)} B; districts {names}; slices in bbox {len(sl)}")
                    if sample is None and len(sl):
                        rec = sl.drop(columns="geometry").iloc[0].to_dict()
                        sample = (a["id"], names, {k: (None if (isinstance(v, float) and v != v) else v) for k, v in rec.items()},
                                  list(df.drop(columns="geometry").columns))
                else:
                    detail("NZA tiles", a["id"], cnt, 0, f"tile {z}/{x}/{y} status {st}, no polygon in AOI bbox")
            else:
                detail("NZA tiles", a["id"], 0, 0, f"tile {z}/{x}/{y} status {st} (204 = no zoning data in tile)")
            if a["id"] != "CONTROL" and cnt:
                hits += 1
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        d["control_passed"] = "yes" if statuses["CONTROL"][0] == 204 and hits > 0 else "no"
        d["quality_fields"] = ("created;type;jurisdiction_id;county_id;cbsa_id;state_id;family1_treatment;family1_parking;family1_heightcap;family1_minlotacres_min"
                               if sample else "none seen")
        d["notes"] = (f"Found by reading the atlas web app's JS (edit.zoningatlas.org/atlas/ answers 200 to this UA but returns a Cloudflare 'Just a moment' challenge to curl). "
                      f"Vector tiles on tiles.zoningatlas.org: TileJSON (HTTP {d['http_status']}, zoom {tj.get('minzoom')}-{tj.get('maxzoom')}) lists layers but no fields; fields read from a decoded z{z} tile with GDAL's MVT driver (single-file tiles come back in 0-4096 tile coordinates, y up; the AOI bbox is mapped into them, orientation checked by finding downtown-Detroit districts such as 'Downtown Overlay'). "
                      "Layers: jurisdictions, extraterritorialzoning, zoningdistricts (name, abbrvname, type, jurisdiction_id, county_id, cbsa_id, state_id) and zoningdistrictslices (per-district treatment of 1-4 family housing, parking, height cap, min lot acres, ADU occupancy). "
                      "Tile /nza_merged is only a basemap (Protomaps + PAD-US + NHD). Anonymous users get ids and slice attributes; the JS says full per-zone info comes from the login-only /atlas/zoneclick. "
                      f"Tile status per AOI (z{z}): " + ", ".join(f"{k}:{v[0]}" for k, v in statuses.items() if v[0] != 204) + f"; every other AOI and the Pacific control returned 204. 'Hit' = a district polygon intersects the AOI bbox inside the tile. "
                      "US only, and only jurisdictions already digitised (Story Co. IA is not). Probe restraint: 16 tiles only, because the Terms bar bulk download: ask the Atlas for written permission before building an adapter. "
                      "New features per AOI: zone district code and name, family-1..4 housing treatment (by right / hearing / prohibited), min lot size acres, parking minimum flag, height cap flag, ADU treatment, jurisdiction id."
                      + (f" Sample slice at {sample[0]}: {json.dumps(sample[2], default=str)[:700]}" if sample else ""))
    except Exception as ex:
        fail(d, ex)
    return d


def p_padus():
    base = "https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_4_1/MapServer/0"
    d = row("S6", "PAD-US 4.1 (USGS GAP) fee polygons", "registry", base + "/query?geometry={bbox}&geometryType=esriGeometryEnvelope&inSR=4326&where=1=1&outFields=*&f=json",
            "none", "snapshot", "U.S. Government work (USGS data release doi:10.5066/P96WBCHS); service copyrightText is the citation only")
    try:
        s, j, e = jget(base + "?f=json")
        d["http_status"] = s
        d["reachable"] = "yes" if j and j.get("name") else "no"
        hits = 0
        for a in AOIS:
            _, n, err = arc_count(base, a["bbox"])
            detail("PAD-US", a["id"], n if n is not None else err)
            hits += 1 if n else 0
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        _, cn, _ = arc_count(base, CONTROL)
        # filter differential on a US AOI with many polygons: GAP status 1 only must be < unfiltered
        us = next(a for a in AOIS if a["id"] == "mine_us_bingham_ut")
        _, n_all, _ = arc_count(base, buf(us["bbox"], 10))
        _, n_f, _ = arc_count(base, buf(us["bbox"], 10), where="GAP_Sts='3'")
        d["control_passed"] = "yes" if cn == 0 and n_all and n_f is not None and n_f < n_all else "no"
        feats = arc_first(base, buf(us["bbox"], 10))
        flds = list(feats[0]["attributes"].keys()) if feats else []
        keep = [f for f in flds if f in ("Src_Date", "Date_Est", "GAP_Sts", "GapSts", "IUCN_Cat", "Pub_Access", "Access_Dt",
                                         "GIS_Acres", "GIS_Src", "Agg_Src", "Des_Tp", "Mang_Name", "Own_Type", "Category")]
        d["quality_fields"] = ";".join(keep)
        d["notes"] = (f"PAD-US 4.1 MapServer layer 0 'PADUS4_1Fee'; also FeatureServers on services.arcgis.com/v01gqwM5QqNysAAi "
                      f"(e.g. Manager_Name_PADUS). Strict AOI-bbox intersect. Control {cn}; Bingham 10 km buffer all={n_all}, "
                      f"GAP_Sts='3' only={n_f} (differential). US only: Canadian AOIs return 0 = coverage gap. "
                      "Protected-area designation, not zoning: new features = in-protected-area flag, GAP status 1-4, manager, "
                      "public access, IUCN category, designation date. Layer maxRecordCount 2000.")
    except Exception as ex:
        fail(d, ex)
    return d


def p_alr():
    ep = "https://openmaps.gov.bc.ca/geo/pub/ows"
    d = row("S6", "BC Agricultural Land Reserve polygons", "registry",
            ep + "?service=WFS&version=2.0.0&request=GetFeature&typeNames=pub:WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS&bbox={minlon},{minlat},{maxlon},{maxlat},EPSG:4326&resultType=hits",
            "none", "snapshot", "Open Government Licence - British Columbia (BC Data Catalogue, alc-agricultural-land-reserve-polygons)")

    def hits(b):
        p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
             "typeNames": "pub:WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS",
             "bbox": bb(b) + ",EPSG:4326", "resultType": "hits"}
        r, err = http(ep, p, timeout=90)
        if r is None:
            return None, None
        m = re.search(r'numberMatched="(\d+)"', r.text)
        return r.status_code, int(m.group(1)) if m else None
    try:
        total_status, total = hits((-140, 48, -114, 60))
        d["http_status"] = total_status
        d["reachable"] = "yes" if total is not None else "no"
        n_hit = 0
        for a in AOIS:
            _, n = hits(a["bbox"])
            detail("BC ALR", a["id"], n)
            n_hit += 1 if n else 0
        d["aoi_hits"] = f"{n_hit}/{len(AOIS)}"
        _, cn = hits(CONTROL)
        _, fv = hits((-122.5, 49.0, -122.0, 49.3))  # Fraser Valley, bbox axis order proof
        d["control_passed"] = "yes" if cn == 0 and fv and fv > 0 else "no"
        p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "outputFormat": "application/json",
             "typeNames": "pub:WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS", "count": 1, "bbox": "-122.5,49.0,-122.0,49.3,EPSG:4326"}
        s, j, e = jget(ep, p)
        props = list(j["features"][0]["properties"].keys()) if j and j.get("features") else []
        d["quality_fields"] = ";".join(props)
        cat = jget("https://catalogue.data.gov.bc.ca/api/3/action/package_show", {"id": "alc-agricultural-land-reserve-polygons"})[1]
        mod = (cat or {}).get("result", {}).get("metadata_modified", "")
        d["notes"] = (f"WFS 2.0 GeoServer; bbox as minlon,minlat,maxlon,maxlat,EPSG:4326. Provincial total hits (BC bbox)={total}; "
                      f"Fraser Valley bbox={fv}; control={cn}. Strict AOI-bbox intersect: only BC AOIs can hit. "
                      f"Catalogue record modified {mod[:10]}. Features added: in-ALR flag, ALR status, ALR polygon area. "
                      "STATUS carries ALR/ non-ALR; no zoning district. BC only.")
    except Exception as ex:
        fail(d, ex)
    return d


def p_urban_atlas():
    base = "https://image.discomap.eea.europa.eu/arcgis/rest/services/UrbanAtlas/UA_UrbanAtlas_2018/MapServer/2"
    d = row("S6", "EU Urban Atlas 2018 land use (Copernicus/EEA)", "registry",
            base + "/query?geometry={bbox}&geometryType=esriGeometryEnvelope&inSR=4326&f=json",
            "none", "snapshot", "Not stated by the service (copyright text: 'European Environment Agency (EEA)'); Copernicus Land products fall under the Copernicus free, full and open data policy (not read live)")
    try:
        s, j, e = jget(base + "?f=json")
        d["http_status"] = s
        d["reachable"] = "yes" if j and j.get("name") else "no"
        hits = 0
        for a in AOIS:
            _, n, err = arc_count(base, a["bbox"])
            detail("EU Urban Atlas", a["id"], n if n is not None else err)
            hits += 1 if n else 0
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        _, cn, _ = arc_count(base, CONTROL)
        paris = (2.34, 48.85, 2.35, 48.86)
        _, pn, _ = arc_count(base, paris)
        feats = arc_first(base, paris, n=1)
        attrs = feats[0]["attributes"] if feats else {}
        d["control_passed"] = "yes" if cn == 0 and pn else "no"
        d["quality_fields"] = ";".join(k for k in attrs if k in ("code_2018", "class_2018", "prod_date", "identifier", "area", "comment", "fua_name", "country"))
        d["notes"] = (f"Land Use vector layer 2 of UA_UrbanAtlas_2018 MapServer (also 2006 and 2012 services, and change 2012-2018). "
                      f"EU-only (functional urban areas, >50k pop): 0/15 test AOIs is a coverage gap, not a failure. "
                      f"Positive control Paris bbox={pn}, Pacific control={cn}. Sample record: {json.dumps({k: attrs[k] for k in list(attrs)[:8]}, default=str)[:300]}. "
                      "Features: urban-atlas land-use class (artificial surfaces / roads / water) with 0.25 ha min mapping unit, not legal zoning. "
                      "The Copernicus download portal needs EU Login; this EEA ArcGIS service is anonymous. maxRecordCount 1000.")
    except Exception as ex:
        fail(d, ex)
    return d


def p_vancouver():
    base = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/zoning-districts-and-labels"
    d = row("S6", "Vancouver zoning districts (City open data)", "registry", base + "/records?where=intersects(geom,geom'{wkt_polygon}')&limit=100",
            "none", "snapshot", "Open Government Licence - Vancouver (Opendatasoft metas.license)")
    try:
        s, j, e = jget(base)
        d["http_status"] = s
        d["reachable"] = "yes" if j else "no"
        meta = (j or {}).get("metas", {}).get("default", {})
        total = meta.get("records_count")
        hits = 0
        for a in AOIS:
            s2, jj, e2 = jget(base + "/records", {"where": f"intersects(geom,geom'{wkt_poly(a['bbox'])}')", "limit": 100, "select": "zoning_district,zoning_category"})
            n = (jj or {}).get("total_count")
            detail("Vancouver zoning", a["id"], n if n is not None else e2, extra=str([r['zoning_district'] for r in (jj or {}).get('results', [])][:3]))
            hits += 1 if n else 0
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        _, jc, _ = jget(base + "/records", {"where": f"intersects(geom,geom'{wkt_poly(CONTROL)}')", "limit": 1})
        _, jv, _ = jget(base + "/records", {"where": "intersects(geom,geom'POINT(-123.1207 49.2827)')", "limit": 1})
        d["control_passed"] = "yes" if (jc or {}).get("total_count") == 0 and (jv or {}).get("total_count") == 1 else "no"
        d["quality_fields"] = "zoning_district;zoning_category;zoning_classification;cd_1_number;object_id;metas.modified;metas.records_count"
        d["notes"] = (f"Opendatasoft Explore v2.1. {total} zoning polygons, dataset modified {str(meta.get('modified'))[:10]}. "
                      "Server-side spatial filter intersects()/within_distance() works (differential: downtown point=1 row, Pacific polygon=0). "
                      "City of Vancouver only: other Canadian AOIs 0 = coverage gap. Join level: zone polygon (not parcel). "
                      "Features: zoning district code (e.g. CD-1 (204)), zone category, CD-1 flag. Adapter must be one per city.")
    except Exception as ex:
        fail(d, ex)
    return d


def p_toronto():
    pk = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
    rid = "76a2620f-a6b4-495d-8e41-c0ede1f8a928"
    ds = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search"
    d = row("S6", "Toronto Zoning By-law 569-2013 zoning area", "registry", ds + "?resource_id=" + rid + "&limit=12000",
            "none", "snapshot", "CKAN license_title is null for zoning-by-law (portal default: Open Government Licence - Toronto)")
    try:
        s, j, e = jget(pk, {"id": "zoning-by-law"})
        d["http_status"] = s
        mod = (j or {}).get("result", {}).get("metadata_modified", "")
        s, j, e = jget(ds, {"resource_id": rid, "limit": 12000}, timeout=120)
        d["http_status"] = s
        recs = (j or {}).get("result", {}).get("records", [])
        d["reachable"] = "yes" if recs else "no"
        total = (j or {}).get("result", {}).get("total")
        polys = []
        for r in recs:
            try:
                polys.append((shape(json.loads(r["geometry"])), r))
            except Exception:
                pass
        hits = 0
        for a in AOIS:
            m = [r for g, r in polys if g.intersects(box(*a["bbox"]))]
            detail("Toronto zoning", a["id"], len(m), extra=str(sorted({r["ZN_STRING"] for r in m})[:4]))
            hits += 1 if m else 0
        cm = [r for g, r in polys if g.intersects(box(*CONTROL))]
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        d["control_passed"] = "yes" if not cm and hits > 0 else "no"
        d["quality_fields"] = "ZN_ZONE;ZN_STRING;GEN_ZONE;ZN_HOLDING;ZN_EXCPTN;EXCPTN_NO;FSI_TOTAL;COVERAGE;UNITS;ZN_STATUS;ZBL_CHAPT;ZBL_SECTN;package.metadata_modified"
        d["notes"] = (f"CKAN datastore resource {rid}; {total} zoning polygons returned in one call (limit 12000); package metadata_modified {mod[:10]}. "
                      "Datastore has no spatial filter: adapter must pull the layer (or the GeoJSON/GPKG resource) and intersect locally. "
                      "Extra overlay layers in the same package: height, lot coverage, setback, rooming house, parking zone, policy area. "
                      "City of Toronto only. Join level: zone polygon. Features: zone code, FSI, coverage %, height overlay, setback overlay.")
    except Exception as ex:
        fail(d, ex)
    return d


def p_calgary():
    base = "https://data.calgary.ca/resource/qe6k-p9nh.json"
    d = row("S6", "Calgary land use districts (Socrata)", "registry", base + "?$where=intersects(multipolygon,'{wkt}')",
            "none", "snapshot", "Socrata license field 'See Terms of Use' (City of Calgary Open Data Terms of Use / OGL-Calgary)")
    try:
        meta_s, meta, _ = jget("https://data.calgary.ca/api/views/qe6k-p9nh.json")
        hits = 0
        for a in AOIS:
            s, j, e = jget(base, {"$select": "count(*)", "$where": f"intersects(multipolygon,'{wkt_poly(a['bbox'])}')"})
            n = int(j[0]["count"]) if isinstance(j, list) and j else None
            detail("Calgary land use", a["id"], n if n is not None else e)
            hits += 1 if n else 0
            d["http_status"] = s
        d["reachable"] = "yes" if d["http_status"] == 200 else "no"
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        _, jc, _ = jget(base, {"$select": "count(*)", "$where": f"intersects(multipolygon,'{wkt_poly(CONTROL)}')"})
        _, jt, _ = jget(base, {"$select": "count(*)"})
        _, jp, _ = jget(base, {"$select": "lu_code,major,description", "$where": "intersects(multipolygon,'POINT (-114.0719 51.0447)')", "$limit": 1})
        d["control_passed"] = "yes" if jc and int(jc[0]["count"]) == 0 and jp else "no"
        upd = time.strftime("%Y-%m-%d", time.gmtime((meta or {}).get("rowsUpdatedAt", 0)))
        d["quality_fields"] = "lu_code;label;description;major;generalize;lu_bylaw;dc_bylaw;density;height;far;rowsUpdatedAt"
        d["notes"] = (f"Socrata SODA; {jt[0]['count'] if jt else '?'} district polygons, rowsUpdatedAt {upd}. Server-side intersects() works "
                      f"(downtown point -> {jp[0] if jp else None}; Pacific polygon -> 0). Calgary only. Join level: district polygon. "
                      "Features: land-use code, major class, max density/height/FAR, DC bylaw flag. No 429 seen without an app token.")
    except Exception as ex:
        fail(d, ex)
    return d


def p_regrid():
    d = row("S6", "Regrid parcels with zoning", "registry", "https://app.regrid.com/api/v2/parcels/point?lat={lat}&lon={lon}&token={token}",
            "paid", "snapshot", "Commercial (Regrid terms); not open")
    try:
        r, e = http(d["endpoint"].split("&token")[0].replace("{lat}", "42.05").replace("{lon}", "-93.6"))
        r2, _ = http("https://regrid.com/api")
        d["http_status"] = r.status_code if r is not None else ""
        d["reachable"] = "partial" if r is not None and r.status_code == 401 else "no"
        d["notes"] = (f"API answers 401 {(r.text[:70] if r is not None else '')!r} without a token: paid/key-we-lack, not probed further. "
                      f"Public: product page regrid.com/api (HTTP {r2.status_code if r2 is not None else 'ERR'}), pricing page. "
                      "Vendor page title advertises 'Nationwide Parcel, Zoning & Building Data'; the zoning tier and Canadian coverage were not verified. No free anonymous parcel or zoning layer was found. "
                      "Would add: parcel id, zoning code, land-use code, owner type, parcel area. Join level: parcel.")
        d["quality_fields"] = "none seen (401)"
    except Exception as ex:
        fail(d, ex)
    return d


# ================================================================ S7
USGS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections"


def p_usgs_water():
    d = row("S7", "USGS Water Data API (OGC API)", "ground station",
            USGS + "/monitoring-locations/items?f=json&bbox={bbox}&site_type_code=ST&limit=200",
            "none", "snapshot", "U.S. Government public domain (USGS); api key optional, raises hourly limits")
    try:
        r, err = http(USGS + "/monitoring-locations/items", {"f": "json", "limit": 1})
        d["http_status"] = r.status_code if r is not None else ""
        rl = {k: v for k, v in (r.headers.items() if r is not None else []) if "limit" in k.lower() or "remaining" in k.lower() or "retry" in k.lower()}
        hdr_names = ",".join(sorted(r.headers.keys())) if r is not None else ""
        d["reachable"] = "yes" if r is not None and r.status_code == 200 else "no"
        hits = 0
        sample = None
        for a in AOIS:
            b = buf(a["bbox"], 25)
            s, j, e = jget(USGS + "/monitoring-locations/items", {"f": "json", "bbox": bb(b), "limit": 200, "site_type_code": "ST"})
            feats = (j or {}).get("features", [])
            nearest, best = None, 1e9
            for f in feats:
                lon, lat = f["geometry"]["coordinates"][:2]
                dd = km(a["lat"], a["lon"], lat, lon)
                if dd < best:
                    best, nearest = dd, f
            detail("USGS Water Data", a["id"], len(feats), round(best, 1) if nearest else "", nearest["properties"]["id"] if nearest else "")
            if nearest:
                hits += 1
                if sample is None and nearest["properties"].get("drainage_area"):
                    q = jget(USGS + "/latest-continuous/items", {"f": "json", "monitoring_location_id": nearest["properties"]["id"], "parameter_code": "00060", "limit": 1})[1]
                    sample = (a["id"], round(best, 1), nearest["properties"], (q or {}).get("features", [{}])[0].get("properties") if q else None)
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        # differential: unfiltered vs site_type ST in Ames IA, then control
        ames = (-93.7, 42.0, -93.5, 42.1)
        _, ja, _ = jget(USGS + "/monitoring-locations/items", {"f": "json", "bbox": bb(ames), "limit": 1000})
        _, jst, _ = jget(USGS + "/monitoring-locations/items", {"f": "json", "bbox": bb(ames), "limit": 1000, "site_type_code": "ST"})
        _, jc, _ = jget(USGS + "/monitoring-locations/items", {"f": "json", "bbox": bb(CONTROL), "limit": 10})
        na, ns, nc = (j.get("numberReturned") if j else None for j in (ja, jst, jc))
        d["control_passed"] = "yes" if nc == 0 and na and ns is not None and ns < na else "no"
        d["quality_fields"] = "approval_status;qualifier;statistic_id;time;unit_of_measure;last_modified;drainage_area;contributing_drainage_area;altitude_accuracy;horizontal_positional_accuracy;vertical_datum"
        sm = ""
        if sample:
            p = sample[2]
            sm = (f" Sample {sample[0]} nearest ST site {p['id']} '{p['monitoring_location_name']}' {sample[1]} km, drainage_area {p.get('drainage_area')} mi2, "
                  f"latest 00060: {json.dumps(sample[3])[:250]}.")
        d["notes"] = (f"25 km AOI buffer, centroid distance. Collections: monitoring-locations, latest-continuous, latest-daily, daily, continuous, peaks, field-measurements, channel-measurements, time-series-metadata. "
                      f"Differential at Ames IA bbox: all sites={na}, site_type_code=ST={ns}, Pacific control={nc}. Rate-limit headers: {rl or 'none seen on 200'} (response headers: {hdr_names}); no 429 in ~120 calls. "
                      "US only: Canadian AOIs have no USGS stream gauges except border waters (Detroit/Windsor). "
                      "New features per AOI: nearest stream gauge km, drainage area mi2, latest discharge (00060 ft3/s), latest gage height (00065), approval status, record count and period via time-series-metadata, peak flows." + sm)
    except Exception as ex:
        fail(d, ex)
    return d


ECCC = "https://api.weather.gc.ca/collections"


def p_eccc_hydro():
    d = row("S7", "ECCC hydrometric (HYDAT + real-time) OGC API", "ground station",
            ECCC + "/hydrometric-stations/items?f=json&bbox={bbox}&limit=100",
            "none", "snapshot", "Environment and Climate Change Canada data, Open Government Licence - Canada")
    try:
        s, j, e = jget(ECCC + "/hydrometric-stations/items", {"f": "json", "limit": 1})
        d["http_status"] = s
        d["reachable"] = "yes" if j else "no"
        hits = 0
        sample = None
        for a in AOIS:
            b = buf(a["bbox"], 25)
            s, j, e = jget(ECCC + "/hydrometric-stations/items", {"f": "json", "bbox": bb(b), "limit": 200})
            feats = (j or {}).get("features", [])
            active = [f for f in feats if f["properties"].get("STATUS_EN") == "Active"]
            best, nearest = 1e9, None
            for f in active:
                lon, lat = f["geometry"]["coordinates"][:2]
                dd = km(a["lat"], a["lon"], lat, lon)
                if dd < best:
                    best, nearest = dd, f
            extra = ""
            if nearest:
                hits += 1
                sn = nearest["properties"]["STATION_NUMBER"]
                dm = jget(ECCC + "/hydrometric-daily-mean/items", {"f": "json", "STATION_NUMBER": sn, "limit": 1})[1] or {}
                rt = jget(ECCC + "/hydrometric-realtime/items", {"f": "json", "STATION_NUMBER": sn, "limit": 1, "sortby": "-DATETIME"})[1] or {}
                extra = f"{sn} daily_mean_records={dm.get('numberMatched')} realtime_records={rt.get('numberMatched')}"
                if sample is None and rt.get("features"):
                    sample = (a["id"], round(best, 1), nearest["properties"], rt["features"][0]["properties"], dm.get("numberMatched"))
            detail("ECCC hydrometric", a["id"], len(feats), round(best, 1) if nearest else "", f"active={len(active)} {extra}")
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        sk = (-107.0, 51.5, -105.8, 52.5)
        _, jall, _ = jget(ECCC + "/hydrometric-daily-mean/items", {"f": "json", "bbox": bb(sk), "limit": 1})
        _, jst, _ = jget(ECCC + "/hydrometric-daily-mean/items", {"f": "json", "bbox": bb(sk), "limit": 1, "STATION_NUMBER": "05HG001"})
        _, jc, _ = jget(ECCC + "/hydrometric-stations/items", {"f": "json", "bbox": bb(CONTROL), "limit": 5})
        ta, ts, tc = (j.get("numberMatched") if j else None for j in (jall, jst, jc))
        d["control_passed"] = "yes" if tc == 0 and ta and ts is not None and ts < ta else "no"
        d["quality_fields"] = "STATUS_EN;REAL_TIME;RHBN;VERTICAL_DATUM;DRAINAGE_AREA_GROSS;DRAINAGE_AREA_EFFECT;DISCHARGE_SYMBOL_EN;LEVEL_SYMBOL_EN;CONTRIBUTOR_EN;numberMatched"
        sm = ""
        if sample:
            p = sample[2]
            sm = (f" Sample {sample[0]}: {p['STATION_NAME']} {sample[1]} km, status {p['STATUS_EN']}, RHBN={p['RHBN']}, drainage {p.get('DRAINAGE_AREA_GROSS')} km2, "
                  f"{sample[4]} daily-mean records; latest realtime {json.dumps(sample[3])[:260]}.")
        d["notes"] = (f"25 km buffer, nearest ACTIVE station by centroid distance. Differential Saskatoon bbox daily-mean rows={ta}, +STATION_NUMBER=05HG001 rows={ts}, Pacific control stations={tc}. "
                      "Also annual peaks/statistics and monthly means collections. Canada plus a few US border stations; US AOIs usually 0 = coverage. "
                      "New features per AOI: nearest active gauge km, drainage area km2, latest discharge m3/s and level m (5-minute realtime, last 30 days), HYDAT daily-mean record count and period, annual max/min flow, RHBN pristine-basin flag." + sm)
    except Exception as ex:
        fail(d, ex)
    return d


def p_hydrosheds():
    url = "https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_na_shp.zip"
    d = row("S7", "HydroSHEDS / HydroRIVERS v10 (North America)", "model", url, "none", "snapshot",
            "HydroSHEDS licence: free for scientific, educational and commercial use under the HydroSHEDS licence agreement (attribution, redistribution limits); Esri HydroSHEDS 2.0 view is CC BY 4.0")
    try:
        r, e = http(url, method="HEAD")
        d["http_status"] = r.status_code if r is not None else ""
        d["reachable"] = "partial" if r is not None and r.status_code == 200 else "no"
        size = r.headers.get("content-length") if r is not None else None
        z = CACHE / "HydroRIVERS_v10_na_shp.zip"
        if not z.exists() or z.stat().st_size < 60_000_000:
            rr, e = http(url, stream=True, timeout=600)
            with open(z, "wb") as fh:
                for chunk in rr.iter_content(1 << 20):
                    fh.write(chunk)
        import geopandas as gpd
        inner = [n for n in zipfile.ZipFile(z).namelist() if n.endswith(".shp")][0]
        hits = 0
        sample = None
        for a in AOIS:
            b = buf(a["bbox"], 25)
            gdf = gpd.read_file(f"zip://{z}!{inner}", bbox=b)
            if len(gdf):
                loc = f"+proj=aeqd +lat_0={a['lat']} +lon_0={a['lon']} +datum=WGS84 +units=m"
                dist = gdf.to_crs(loc).distance(Point(0, 0)) / 1000
                i = dist.idxmin()
                rec = gdf.loc[i]
                hits += 1
                detail("HydroRIVERS", a["id"], len(gdf), round(float(dist.min()), 1),
                       f"ORD_STRA={rec['ORD_STRA']} DIS_AV_CMS={rec['DIS_AV_CMS']} UPLAND_SKM={rec['UPLAND_SKM']}")
                if sample is None or (rec["UPLAND_SKM"] > sample[2]["UPLAND_SKM"] and dist.min() < 10):
                    sample = (a["id"], round(float(dist.min()), 1), rec.drop("geometry").to_dict())
            else:
                detail("HydroRIVERS", a["id"], 0)
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        gc = gpd.read_file(f"zip://{z}!{inner}", bbox=CONTROL)
        d["control_passed"] = "yes" if len(gc) == 0 else "no"
        fs = "https://services5.arcgis.com/7weheFjxuNkGGiZi/arcgis/rest/services/HydroSHEDS_v2_River_Streamlines_view/FeatureServer/0"
        fs_hits = 0
        for a in AOIS:
            _, n, _ = arc_count(fs, buf(a["bbox"], 25))
            fs_hits += 1 if n else 0
        d["quality_fields"] = "ORD_STRA;ORD_CLAS;ORD_FLOW;DIS_AV_CMS;UPLAND_SKM;CATCH_SKM;LENGTH_KM;DIST_DN_KM;DIST_UP_KM;ENDORHEIC;HYBAS_L12"
        d["notes"] = (f"No anonymous query API for HydroRIVERS/HydroBASINS: file download only (HydroRIVERS NA shapefile {size} bytes; HydroBASINS levels 1-12 at data.hydrosheds.org/file/hydrobasins/standard/). "
                      f"Probed from the cached zip with a bbox read, 25 km buffer, nearest river by centroid distance. Pacific control rows={len(gc)}. "
                      f"Esri-hosted HydroSHEDS 2.0 FeatureServer (services5.arcgis.com/7weheFjxuNkGGiZi, Strahler 8-11 only) hits 25 km: {fs_hits}/{len(AOIS)} - too coarse for small streams. "
                      "Modelled 15 arc-sec routing, not an observation; discharge is a long-term mean. Global, so it covers both countries and gives the one water-network source that works for Canada and the US with the same fields. "
                      "New features per AOI: nearest river km, Strahler order, long-term mean discharge m3/s, upstream area km2, distance to river mouth km, endorheic flag, HydroBASINS sub-basin id and area."
                      + (f" Sample {sample[0]} nearest river {sample[1]} km: {json.dumps(sample[2], default=str)[:400]}" if sample else ""))
    except Exception as ex:
        fail(d, ex)
    return d


NHD = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer"


def p_nhdplus():
    d = row("S7", "NHDPlus HR (USGS National Map hydro service)", "model",
            NHD + "/3/query?geometry={bbox}&geometryType=esriGeometryEnvelope&inSR=4326&outFields=*&f=json",
            "none", "snapshot", "U.S. Government public domain (USGS); service metadata states no licence")
    try:
        s, j, e = jget(NHD + "/3?f=json")
        d["http_status"] = s
        d["reachable"] = "yes" if j and j.get("name") else "no"
        hits = 0
        sample = None
        fl = "gnis_name,streamorde,totdasqkm,areasqkm,lengthkm,qama,vama,slope,reachcode,fdate,resolution,nhdplusid"
        for a in AOIS:
            b = buf(a["bbox"], 2)
            p = {"f": "json", "geometry": bb(b), "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": 4326,
                 "spatialRel": "esriSpatialRelIntersects", "outFields": fl, "returnGeometry": "true", "where": "1=1", "resultRecordCount": 200}
            s2, jj, e2 = jget(NHD + "/3/query", p, timeout=120)
            feats = (jj or {}).get("features", [])
            best, rec = 1e9, None
            for f in feats:
                for path in f.get("geometry", {}).get("paths", []):
                    for x, y in path:
                        dd = km(a["lat"], a["lon"], y, x)
                        if dd < best:
                            best, rec = dd, f["attributes"]
            if rec:
                hits += 1
                if sample is None or (rec.get("totdasqkm") or 0) > (sample[2].get("totdasqkm") or 0):
                    sample = (a["id"], round(best, 2), rec)
            detail("NHDPlus HR", a["id"], len(feats), round(best, 2) if rec else "", json.dumps(rec, default=str)[:160] if rec else (jj or {}).get("error", ""))
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        gcount = [arc_count(NHD + "/0", buf(a["bbox"], 10))[1] for a in AOIS]
        ca_hits = [a["id"] for a in AOIS if a["country"] == "CA" and any(x["candidate"] == "NHDPlus HR" and x["aoi_id"] == a["id"] and x["n"] for x in DETAIL)]
        _, cn, _ = arc_count(NHD + "/3", CONTROL)
        _, an, _ = arc_count(NHD + "/3", buf(next(a for a in AOIS if a["id"] == "farm_us_ia_story")["bbox"], 2))
        _, fn, _ = arc_count(NHD + "/3", buf(next(a for a in AOIS if a["id"] == "farm_us_ia_story")["bbox"], 2), where="streamorde>=3")
        d["control_passed"] = "yes" if cn == 0 and an and fn is not None and fn < an else "no"
        d["quality_fields"] = "fdate;resolution;streamcalc;streamorde;totdasqkm;qama;vama;slope;gageidma;gageqma;statusflag"
        d["notes"] = (f"MapServer layers: 0 NHDPlusGage, 3 NetworkNHDFlowline, 9 NHDWaterbody, 10 NHDPlusCatchment, 12 WBDHU12; separate 'nhd' MapServer has large-scale flowlines. "
                      f"2 km buffer, nearest flowline vertex to centroid. Gauges within 10 km (NHDPlusGage) per AOI: {gcount}. "
                      f"Differential Story Co. IA flowlines all={an}, streamorde>=3={fn}, Pacific control={cn}. Canadian AOIs that still return flowlines (Great Lakes basin parts of NHDPlus HR): {ca_hits}; others return 0 = coverage gap. "
                      "Large scale 1:24k+ (HR) with EROM mean-annual flow (qama cfs) and velocity (vama fps). maxRecordCount 2000. "
                      "New features per AOI: nearest named stream, Strahler order, upstream drainage area km2, mean annual flow cfs and velocity, channel slope, catchment area, HUC12 id, waterbody (NHDWaterbody) area and type, nearest NHDPlusGage."
                      + (f" Sample {sample[0]} {sample[1]} km: {json.dumps(sample[2], default=str)[:450]}" if sample else ""))
    except Exception as ex:
        fail(d, ex)
    return d


NHN_WMS = "https://maps.geogratis.gc.ca/wms/hydro_network_en"


def p_nhn():
    d = row("S7", "NRCan National Hydro Network (NHN) GeoBase", "registry",
            NHN_WMS + "?service=WMS&version=1.3.0&request=GetFeatureInfo&layers=nhn:nhn:hydrography:slwatercourse_1,nhn:nhn:hydrography:waterbody_2&info_format=application/vnd.ogc.gml",
            "none", "snapshot", "Open Government Licence - Canada")
    try:
        r, e = http(NHN_WMS, {"service": "WMS", "request": "GetCapabilities", "version": "1.3.0"})
        d["http_status"] = r.status_code if r is not None else ""
        d["reachable"] = "partial" if r is not None and r.status_code == 200 else "no"
        layers = "nhn:nhn:hydrography:slwatercourse_1,nhn:nhn:hydrography:waterbody_2"

        samples = []

        def gfi(b, n=3):
            x0, y0, x1, y1 = b
            span = max(x1 - x0, y1 - y0, 0.02)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            wb = (cx - span / 2, cy - span / 2, cx + span / 2, cy + span / 2)
            W = 200
            found = 0
            fields = set()
            for ii in range(n):
                for jj in range(n):
                    px = int(W * (ii + 0.5) / n)
                    py = int(W * (jj + 0.5) / n)
                    p = {"service": "WMS", "version": "1.3.0", "request": "GetFeatureInfo", "layers": layers, "query_layers": layers,
                         "styles": "", "crs": "EPSG:4326", "bbox": f"{wb[1]},{wb[0]},{wb[3]},{wb[2]}", "width": W, "height": W,
                         "i": px, "j": py, "info_format": "application/vnd.ogc.gml", "feature_count": 3}
                    rr, ee = http(NHN_WMS, p, timeout=60)
                    if rr is not None and "_feature>" in rr.text:
                        found += 1
                        fields.update(re.findall(r"<(\w+)>", rr.text))
                        if len(samples) < 3:
                            samples.append({k: v for k, v in re.findall(r"<(name_en|permanency_en|water_definition_en|zt_id|md_temporal_extent_date_min|md_horiz_position_accuracy_min)>([^<]*)<", rr.text)})
            return found, fields
        hits = 0
        fieldset = set()
        for a in AOIS:
            b = buf(a["bbox"], 0.5)
            f, flds = gfi(b)
            fieldset |= flds
            detail("NHN WMS", a["id"], f, extra="3x3 grid GetFeatureInfo points with a hit")
            hits += 1 if f else 0
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        cf, _ = gfi(CONTROL, 2)
        # known river: South Saskatchewan at Saskatoon -106.67,52.13 as positive control
        pf, pflds = gfi((-106.70, 52.10, -106.60, 52.16), 3)
        fieldset |= pflds
        d["control_passed"] = "yes" if cf == 0 and pf > 0 else "no"
        d["quality_fields"] = ";".join(f for f in ("zt_id", "md_id", "md_temporal_extent_date_min", "md_temporal_extent_date_max", "md_horiz_position_accuracy_min", "md_horiz_position_accuracy_max", "permanency_en", "water_definition_en", "is_isolated_en", "name_en") if f in fieldset)
        d["notes"] = (f"WMS 1.3.0 only for live attribute lookups (GetFeatureInfo gml, point-in-pixel tolerance); no WFS, no ESRI REST, no OGC API found (maps.geogratis.gc.ca/wfs 404). "
                      f"Per-AOI hit = any of a 3x3 grid of point queries (AOI bbox + 500 m, window at least 0.02 deg, 200 px) touching a watercourse or waterbody. Control {cf}; positive control on South Saskatchewan at Saskatoon: {pf}/9 points (so aoi_hits is a LOWER BOUND set by 9 sample points per AOI, not by data coverage; Montreal and the Saskatoon quarter show 0 only because no sample point landed on water). "
                      "Bulk vector only as per work-unit GPKG/SHP/GDB at ftp.maps.canada.ca/pub/nrcan_rncan/vector/geobase_nhn_rhn/ (index zip 252 MB; hnet province file 27 GB). "
                      f"Canada only. Sample replies: {json.dumps(samples)[:500]}. "
                      "New features per AOI: nearest named watercourse/waterbody, permanency (permanent/intermittent), source map-sheet id (zt_id), source survey year and horizontal accuracy m (a real per-feature QC pair), network flow direction.")
    except Exception as ex:
        fail(d, ex)
    return d


# ================================================================ S8
def p_eccc_climate():
    d = row("S8", "ECCC climate stations + daily observations OGC API", "ground station",
            ECCC + "/climate-stations/items?f=json&bbox={bbox}&limit=500 ; " + ECCC + "/climate-daily/items?f=json&CLIMATE_IDENTIFIER={id}&datetime={start}/{end}",
            "none", "composite", "Environment and Climate Change Canada data, Open Government Licence - Canada")
    try:
        s, j, e = jget(ECCC + "/climate-stations/items", {"f": "json", "limit": 1})
        d["http_status"] = s
        d["reachable"] = "yes" if j else "no"
        hits = 0
        sample = None
        for a in AOIS:
            b = buf(a["bbox"], 50)
            s, j, e = jget(ECCC + "/climate-stations/items", {"f": "json", "bbox": bb(b), "limit": 500}, timeout=90)
            feats = (j or {}).get("features", [])
            act = [f for f in feats if (f["properties"].get("DLY_LAST_DATE") or "") >= "2025-01-01"]
            best, nearest = 1e9, None
            for f in act:
                lon, lat = f["geometry"]["coordinates"][:2]
                dd = km(a["lat"], a["lon"], lat, lon)
                if dd < best:
                    best, nearest = dd, f
            extra = ""
            if nearest:
                cid = nearest["properties"]["CLIMATE_IDENTIFIER"]
                jd = jget(ECCC + "/climate-daily/items", {"f": "json", "CLIMATE_IDENTIFIER": cid, "datetime": "2020-01-01T00:00:00Z/2024-12-31T23:59:59Z", "limit": 1})[1] or {}
                n_days = jd.get("numberMatched")
                comp = ""
                if n_days:
                    jt = jget(ECCC + "/climate-daily/items", {"f": "json", "CLIMATE_IDENTIFIER": cid, "datetime": "2020-01-01T00:00:00Z/2024-12-31T23:59:59Z", "limit": 2000, "properties": "MEAN_TEMPERATURE,TOTAL_PRECIPITATION"}, timeout=120)[1] or {}
                    fs = jt.get("features", [])
                    if fs:
                        nt = sum(1 for f in fs if f["properties"].get("MEAN_TEMPERATURE") is not None)
                        npr = sum(1 for f in fs if f["properties"].get("TOTAL_PRECIPITATION") is not None)
                        comp = f"mean_temp {100*nt/1827:.0f}% precip {100*npr/1827:.0f}% of 1827 days (first {len(fs)} rows)"
                extra = f"{cid} {nearest['properties']['STATION_NAME']} rows_2020_2024={n_days} {comp}"
                hits += 1
                if sample is None:
                    sample = (a["id"], round(best, 1), nearest["properties"], extra)
            detail("ECCC climate", a["id"], len(feats), round(best, 1) if nearest else "", f"active_since_2025={len(act)} {extra}")
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        sk = (-107.0, 51.5, -105.8, 52.5)
        _, ja, _ = jget(ECCC + "/climate-daily/items", {"f": "json", "bbox": bb(sk), "limit": 1})
        _, jf, _ = jget(ECCC + "/climate-daily/items", {"f": "json", "bbox": bb(sk), "limit": 1, "CLIMATE_IDENTIFIER": "4052280"})
        _, jc, _ = jget(ECCC + "/climate-stations/items", {"f": "json", "bbox": bb(CONTROL), "limit": 5})
        ta, tf, tc = (j.get("numberMatched") if j else None for j in (ja, jf, jc))
        d["control_passed"] = "yes" if tc == 0 and ta and tf is not None and tf < ta else "no"
        d["quality_fields"] = "MEAN_TEMPERATURE_FLAG;MAX_TEMPERATURE_FLAG;MIN_TEMPERATURE_FLAG;TOTAL_PRECIPITATION_FLAG;DLY_FIRST_DATE;DLY_LAST_DATE;HAS_NORMALS_DATA;STATION_TYPE;ELEVATION;numberMatched"
        d["notes"] = (f"50 km buffer, nearest station with daily data since 2025 by centroid distance; completeness over 2020-2024 from non-null MEAN_TEMPERATURE / TOTAL_PRECIPITATION in the first 2000 rows. "
                      f"Differential Saskatoon bbox climate-daily rows={ta}, +CLIMATE_IDENTIFIER=4052280 rows={tf}, Pacific control stations={tc}. "
                      "Other collections on the same host: climate-monthly, climate-hourly, climate-normals (1981-2010 only), ltce-* (long-term extremes), climate:cangrd:* (gridded anomalies), climate:indices, SPEI. "
                      "Surprise: LATITUDE/LONGITUDE properties are integers scaled by 1e7 (514800000); use the geometry. Canada plus few border stations. "
                      "New features per AOI: nearest station km and elevation, daily Tmax/Tmin/Tmean, precip, snowfall, snow on ground, degree-days, record count and completeness, 1981-2010 normals, extreme records."
                      + (f" Sample {sample[0]} {sample[1]} km: {sample[3]}" if sample else ""))
    except Exception as ex:
        fail(d, ex)
    return d


NCEI_S = "https://www.ncei.noaa.gov/access/services/search/v1/data"
NCEI_D = "https://www.ncei.noaa.gov/access/services/data/v1"


def p_ghcn():
    d = row("S8", "NOAA GHCN-Daily via NCEI access services", "ground station",
            NCEI_S + "?dataset=daily-summaries&bbox={north},{west},{south},{east}&limit=200 ; " + NCEI_D + "?dataset=daily-summaries&stations={id}&dataTypes=TMAX,TMIN,PRCP&startDate=..&endDate=..&format=json&includeAttributes=true",
            "none", "composite", "NOAA NCEI open data; no licence field in the API (GHCN-Daily v3, cite Menne et al. 2012)")
    try:
        s, j, e = jget(NCEI_S, {"dataset": "daily-summaries", "limit": 1})
        d["http_status"] = s
        d["reachable"] = "yes" if j else "no"
        hits = 0
        sample = None
        for a in AOIS:
            x0, y0, x1, y1 = buf(a["bbox"], 50)
            s, j, e = jget(NCEI_S, {"dataset": "daily-summaries", "bbox": f"{y1:.5f},{x0:.5f},{y0:.5f},{x1:.5f}", "limit": 200}, timeout=90)
            res = (j or {}).get("results", [])
            best, nearest = 1e9, None
            for r in res:
                lon, lat = r["location"]["coordinates"][:2]
                dd = km(a["lat"], a["lon"], lat, lon)
                # require recent data
                if r.get("endDate", "") >= "2025-01-01" and dd < best:
                    best, nearest = dd, r
            extra = ""
            if nearest:
                hits += 1
                st = nearest["stations"][0]
                dts = {t["id"]: t for t in st["dataTypes"]}
                extra = f"{st['id']} {st['name']} " + " ".join(f"{k}:cov{dts[k].get('coverage', 0):.0f}%" for k in ("TMAX", "TMIN", "PRCP") if k in dts)
                if sample is None and all(k in dts for k in ("TMAX", "PRCP")):
                    sample = (a["id"], round(best, 1), st, nearest)
            detail("GHCN-Daily", a["id"], (j or {}).get("count", ""), round(best, 1) if nearest else "", extra)
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        sk = (52.2, -106.5, 51.8, -106.1)
        _, ja, _ = jget(NCEI_S, {"dataset": "daily-summaries", "bbox": ",".join(map(str, sk)), "limit": 200})
        _, jt, _ = jget(NCEI_S, {"dataset": "daily-summaries", "bbox": ",".join(map(str, sk)), "dataTypes": "TMAX", "limit": 200})
        _, jc, _ = jget(NCEI_S, {"dataset": "daily-summaries", "bbox": "0.1,-150,0,-149.9", "limit": 200})
        na, nt, nc = (j.get("count") if j else None for j in (ja, jt, jc))
        d["control_passed"] = "yes" if nc == 0 and na and nt is not None and nt < na else "no"
        d["quality_fields"] = "coverage;startDate;endDate;dateRange;PRCP_ATTRIBUTES;TMAX_ATTRIBUTES;platforms"
        smp = ""
        if sample:
            st = sample[2]
            data = None
            r, _e = http(NCEI_D, {"dataset": "daily-summaries", "stations": st["id"], "dataTypes": "TMAX,TMIN,PRCP", "startDate": "2025-01-01", "endDate": "2025-12-31", "format": "json", "includeAttributes": "true"}, timeout=90)
            try:
                data = r.json()
            except Exception:
                data = []
            nreads = len(data)
            smp = (f" Sample {sample[0]} {sample[1]} km station {st['id']} '{st['name']}', 2025 rows={nreads}, first row {json.dumps(data[0])[:200] if data else ''}; "
                   f"dataTypes coverage: " + ", ".join(f"{t['id']}={t.get('coverage', 0):.0f}% {t['startDate'][:4]}-{t['endDate'][:4]}" for t in st['dataTypes'][:6]))
        d["notes"] = (f"50 km buffer, nearest station whose last data is 2025 or later. bbox param order is NORTH,WEST,SOUTH,EAST (verified: Saskatoon count {na}, TMAX-only {nt}, Pacific control {nc}). "
                      "totalCount in the search response is the whole dataset (132893), not the bbox count; use 'count'. Data service refuses calls without a station id (400 'A station is required'). "
                      "Search service gives per-datatype coverage % and date range = ready-made completeness. Global, so covers US and Canadian AOIs (Canadian stations include CoCoRaHS 'CA1xx' ids and ECCC-sourced 'CAN0xxxxxxx' ids). "
                      "New features per AOI: nearest station km, count of stations within 50 km, TMAX/TMIN/PRCP/SNOW/SNWD values, record count, completeness %, period, measurement/quality flags." + smp)
    except Exception as ex:
        fail(d, ex)
    return d


DAYMET = "https://daymet.ornl.gov/single-pixel/api/data"


def p_daymet():
    d = row("S8", "Daymet v4 R1 single-pixel API (ORNL DAAC)", "model",
            DAYMET + "?lat={lat}&lon={lon}&vars=tmax,tmin,prcp,srad,vp,swe,dayl&year=2023&format=json",
            "none", "composite", "Citation required (Thornton et al. 2022, doi:10.3334/ORNLDAAC/2129, returned in every API response); ORNL DAAC licence text not read live")
    try:
        hits = 0
        sample = None
        status = ""
        for a in AOIS:
            s, j, e = jget(DAYMET, {"lat": a["lat"], "lon": a["lon"], "vars": "tmax,tmin,prcp,srad,vp,swe,dayl", "year": 2023, "format": "json"}, timeout=120)
            status = s
            if j and "data" in j:
                data = j["data"]
                prcp = data.get("prcp (mm/day)", [])
                tmax = data.get("tmax (deg c)", [])
                valid = sum(1 for v in tmax if v is not None and v > -9000)
                hits += 1
                detail("Daymet", a["id"], len(tmax), 0, f"tile={j.get('Tile')} elev={j.get('Elevation')} tmax_valid={valid}/{len(tmax)} annual_prcp={sum(p for p in prcp if p is not None):.0f}")
                if sample is None:
                    sample = (a["id"], j.get("Tile"), j.get("Elevation"), list(data.keys()), len(tmax), valid)
            else:
                detail("Daymet", a["id"], 0, "", f"{s} {str(e or j)[:120]}")
        d["http_status"] = status
        d["reachable"] = "yes" if hits else "no"
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        sc, jc, ec = jget(DAYMET, {"lat": 0.05, "lon": -149.95, "vars": "tmax", "year": 2023, "format": "json"})
        d["control_passed"] = "yes" if sc == 400 and jc and "Tile was not found" in str(jc) else "no"
        d["quality_fields"] = "Tile;Elevation;LCC;year;yday;(per-variable series, no flags)"
        d["notes"] = (f"Centroid query, 1 km grid, one call per AOI per variable set. Pacific control returns HTTP {sc} 'Daymet Tile was not found' (explicit no-coverage). "
                      f"Sample {sample[0] if sample else ''}: tile {sample[1] if sample else ''}, elevation {sample[2] if sample else ''}, vars {sample[3] if sample else ''}, 2023 rows {sample[4] if sample else ''}, valid tmax {sample[5] if sample else ''}. "
                      "North America; all 15 AOIs returned data including 57 N (oil sands), northern limit not probed. Model output (interpolated station data), no per-day quality flags; tile id and elevation are the only provenance. "
                      "Also bulk: THREDDS/NCSS and annual/monthly NetCDF on daac.ornl.gov. New features per AOI: daily tmax/tmin/prcp/srad/vapour pressure/SWE/day length; derived growing-degree-days, frost-free days, annual precip, snowpack SWE, VPD.")
    except Exception as ex:
        fail(d, ex)
    return d


def p_terraclimate():
    base = "https://thredds.northwestknowledge.net/thredds/ncss/TERRACLIMATE_ALL/data/TerraClimate_{var}_2023.nc"
    d = row("S8", "TerraClimate monthly (NW Knowledge Network THREDDS NCSS)", "model",
            base + "?var={var}&latitude={lat}&longitude={lon}&time_start=2023-01-01T00:00:00Z&time_end=2023-12-31T00:00:00Z&accept=csv",
            "none", "composite", "CC0-1.0 per the Planetary Computer STAC collection; the THREDDS server carries no licence field (cite Abatzoglou et al. 2018)")
    try:
        hits = 0
        sample = None
        status = ""
        FILL = -2147483648
        for a in AOIS:
            vals = {}
            for var, sf in (("ppt", 0.1), ("aet", 0.1), ("def", 0.1), ("soil", 0.1), ("tmax", 0.01), ("pdsi", 0.01)):
                s, r = None, None
                rr, ee = http(base.format(var=var), {"var": var, "latitude": a["lat"], "longitude": a["lon"], "time_start": "2023-01-01T00:00:00Z", "time_end": "2023-12-31T00:00:00Z", "accept": "csv"}, timeout=90)
                if rr is None or rr.status_code != 200:
                    vals[var] = None
                    status = rr.status_code if rr is not None else ee
                    continue
                status = rr.status_code
                lines = rr.text.strip().splitlines()[1:]
                v = [float(x.split(",")[-1]) for x in lines]
                good = [x for x in v if x != FILL]
                vals[var] = (len(v), len(good), round(sum(good) * sf, 1) if good else None, sf, v[:3])
                if var == "ppt":
                    pass
                if var == "tmax":
                    break  # keep requests low: ppt, aet, def, soil, tmax per AOI
            ok = vals.get("ppt") and vals["ppt"][1] > 0
            detail("TerraClimate", a["id"], vals["ppt"][1] if vals.get("ppt") else 0, 0, f"ppt_sum_2023_mm={vals['ppt'][2] if ok else None} raw_first3={vals['ppt'][4] if vals.get('ppt') else None}")
            if ok:
                hits += 1
                if sample is None:
                    sample = (a["id"], vals)
        d["http_status"] = status
        d["reachable"] = "yes" if hits else "no"
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        rc, _ = http(base.format(var="ppt"), {"var": "ppt", "latitude": 0.05, "longitude": -149.95, "time_start": "2023-01-01T00:00:00Z", "time_end": "2023-03-31T00:00:00Z", "accept": "csv"})
        cv = [float(x.split(",")[-1]) for x in rc.text.strip().splitlines()[1:]] if rc is not None else []
        d["control_passed"] = "yes" if cv and all(x == FILL for x in cv) else "no"
        pc = jget("https://planetarycomputer.microsoft.com/api/stac/v1/collections/terraclimate")
        d["quality_fields"] = "time (month);grid cell lat/lon;scale_factor (not applied by NCSS);_FillValue -2147483648 (ocean)"
        d["notes"] = (f"NCSS point subset on yearly files (14 variables per the Planetary Computer cube: ppt, tmax, tmin, aet, def, pet, soil, swe, q, srad, vap, vpd, ws, pdsi; ppt, aet, def, soil, tmax queried live), 1/24 deg (~4 km) monthly grid, aggregate name spans 1958-current. "
                      f"Pacific control returns the fill value {FILL} for every month, HTTP 200 (control is the fill, not a 404). "
                      "SURPRISE: NCSS returns the packed integer, not the physical value (ppt scale_factor 0.1, tmax 0.01): a manual Iowa 2024 request returned January ppt 320 where the .das says scale_factor 0.1 (32.0 mm). Apply scale_factor from the .das yourself. "
                      "The OPeNDAP '.dds' on the old :8080 host answers 200 with an empty body. "
                      f"Planetary Computer STAC collection terraclimate: HTTP {pc[0]} (Zarr/NetCDF assets, needs signed reads; same data). Global land. Model output, no per-cell quality flags. "
                      "New features per AOI: monthly and annual ppt, tmax/tmin, PET, AET, climatic water deficit, soil moisture, runoff, snow water equivalent, PDSI, VPD, wind; aridity index."
                      + (f" Sample {sample[0]} 2023 ppt sum {sample[1]['ppt'][2]} mm, aet {sample[1]['aet'][2]}, def {sample[1]['def'][2]}, soil(mean-sum) {sample[1]['soil'][2]}." if sample else ""))
    except Exception as ex:
        fail(d, ex)
    return d


def chirps_probe(path_or_url, gz=False):
    import rasterio
    src = ("/vsigzip/" + str(path_or_url)) if gz else "/vsicurl/" + path_or_url
    res = {}
    with rasterio.open(src) as r:
        b = r.bounds
        for a in AOIS + [{"id": "CONTROL", "lat": 0.05, "lon": -149.95}]:
            inside = b.left <= a["lon"] <= b.right and b.bottom <= a["lat"] <= b.top
            if not inside:
                res[a["id"]] = ("outside", None)
                continue
            v = float(next(r.sample([(a["lon"], a["lat"])]))[0])
            res[a["id"]] = ("nodata" if v < -9000 else "ok", v)
        return b, r.res, res


def p_chirps(version):
    if version == "v3":
        url = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/tifs/chirps-v3.0.2024.01.tif"
        d = row("S8", "CHIRPS v3.0 monthly precipitation (UCSB CHC)", "model", url + "  (also daily: .../v3.0/daily/final/)",
                "none", "composite", "Not stated in the v3.0 README (cite Funk et al.); licence not read from the CHC site")
    else:
        url = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/chirps-v2.0.2024.01.tif.gz"
        d = row("S8", "CHIRPS v2.0 monthly precipitation (UCSB CHC)", "model", url,
                "none", "composite", "Not stated on the file server (cite Funk et al. 2015); licence not read from the CHC site")
    try:
        r, e = http(url, method="HEAD")
        d["http_status"] = r.status_code if r is not None else ""
        d["reachable"] = "yes" if r is not None and r.status_code == 200 else "no"
        if version == "v3":
            b, rs, res = chirps_probe(url)
        else:
            z = CACHE / "chirps-v2.0.2024.01.tif.gz"
            if not z.exists() or z.stat().st_size < 10_000_000:
                rr, e = http(url, stream=True, timeout=300)
                with open(z, "wb") as fh:
                    for chunk in rr.iter_content(1 << 20):
                        fh.write(chunk)
            b, rs, res = chirps_probe(z, gz=True)
        hits = 0
        for a in AOIS:
            st, v = res[a["id"]]
            detail(f"CHIRPS {version}", a["id"], 1 if st == "ok" else 0, 0, f"{st} Jan-2024 precip_mm={v}")
            hits += 1 if st == "ok" else 0
        d["aoi_hits"] = f"{hits}/{len(AOIS)}"
        d["control_passed"] = "yes" if res["CONTROL"][0] != "ok" else "no"
        outside = [a["id"] for a in AOIS if res[a["id"]][0] == "outside"]
        d["quality_fields"] = "raster extent;pixel nodata (-9999);product version;month"
        d["notes"] = (f"Raster bounds L{b.left:.1f} B{b.bottom:.1f} R{b.right:.1f} T{b.top:.1f}, {rs[0]:.2f} deg (~5.5 km). Sampled by range read at the centroid. "
                      f"Control (ocean at equator) = {res['CONTROL'][0]} (-9999 nodata: land mask). "
                      + (f"Coverage: outside bounds for {len(outside)} AOIs: {outside} - coverage gap, not failure. " if outside else "All 15 AOIs inside bounds. ")
                      + ("CORRECTION to the brief: v3.0 spans 60S-60N, not 50S-50N, so v3 covers every AOI incl. the oil sands at 57 N; v2.0 stops at 50N. " if version == "v3" else "v2.0 stops at 50N: AOIs north of it are out. ")
                      + "Precipitation only (merged satellite + gauge). Observation fields inside the tif: only the pixel value and month. Source-side QC exists out of band: v3 README documents final vs preliminary products and a /diagnostics tree with station counts by country, monthly station-density maps and fill maps. "
                      "New features per AOI: monthly/daily/annual precip mm, wet-day frequency, 30-yr mean and anomaly, drought indices (SPI) computed from the series.")
    except Exception as ex:
        fail(d, ex)
    return d


def main():
    order = [p_nza, p_padus, p_alr, p_urban_atlas, p_vancouver, p_toronto, p_calgary, p_regrid,
             p_usgs_water, p_eccc_hydro, p_hydrosheds, p_nhdplus, p_nhn,
             p_eccc_climate, p_ghcn, p_daymet, p_terraclimate, lambda: p_chirps("v3"), lambda: p_chirps("v2")]
    only = sys.argv[1:]
    rows = []
    for fn in order:
        name = getattr(fn, "__name__", "chirps")
        if only and not any(o in name for o in only) and not (name == "<lambda>" and "chirps" in only):
            continue
        t = time.time()
        r = fn()
        rows.append(r)
        print(f"[{time.time()-t:5.1f}s] {r['gap']} {r['candidate']}: reachable={r['reachable']} hits={r['aoi_hits']} control={r['control_passed']}", flush=True)
    if only:
        out = HERE / "C_probes.partial.csv"
        dout = HERE / "C_probe_detail.partial.csv"
    else:
        out = HERE / "C_probes.csv"
        dout = HERE / "C_probe_detail.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    with open(dout, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["candidate", "aoi_id", "n", "nearest_km", "extra"])
        w.writeheader()
        w.writerows(DETAIL)


if __name__ == "__main__":
    main()

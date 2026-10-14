"""Lane A probe: Q1 scene-QC backfill plus the S4/S5 imagery candidates. Re-running reproduces A_probes.csv.

Usage: python probe.py [--skip-backfill]   (static-catalog crawls are cached in cache/; run crawl_sar.py first)
"""
import csv, json, re, sys, math, warnings
warnings.filterwarnings("ignore")
import xml.etree.ElementTree as ET
import numpy as np, pandas as pd, requests, rasterio
import planetary_computer as pc
from pyproj import Transformer
from shapely.geometry import shape, box, Point
from shapely.ops import transform as shp_transform
from common import *

COLS = ["gap", "candidate", "source_type", "endpoint", "auth", "reachable", "http_status", "aoi_hits", "control_passed",
        "observation_unit", "quality_fields", "off_nadir_field", "licence", "notes"]
AOIS = aois()
CONTROL = box(*CONTROL_BBOX)
PC = "https://planetarycomputer.microsoft.com/api/stac/v1"
ES = "https://earth-search.aws.element84.com/v1"
LL = "https://landsatlook.usgs.gov/stac-server"
CMR = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD"
WINDOW = "2024-05-01T00:00:00Z/2024-09-30T23:59:59Z"  # same window the POC adapters use
QC_RE = re.compile(r"^(view:|sun|eo:cloud|cloud|light_haze|quality_category|collection_mode|tile:|sar:|sat:|satl:|landsat:|s2:|s1:|processing|gsd|platform|constellation|umbra:|capella|ard_|accuracy:|planet-nicfi:)")
OFFNADIR_RE = re.compile(r"(off_nadir|incidence|look_angle|grazing|offnadir)", re.I)
ROWS = []


def add(**kw):
    r = {c: "" for c in COLS}
    r.update(kw)
    ROWS.append(r)
    print("ROW", r["gap"], r["candidate"], r["aoi_hits"], r["control_passed"], flush=True)


def qc_keys(props):
    return ";".join(k for k in props if QC_RE.match(k))


def offnadir_keys(props):
    return [(k, props[k]) for k in props if OFFNADIR_RE.search(k)]


def stac_search(url, body, retries=3):
    r = req("POST", url, json=body, retries=retries)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {}


def stac_area_probe(search_url, collection, dt, filt=None, limit=100, extra=None):
    """Per-AOI hit counts, control count, and a differential on one cloud filter."""
    counts, status, sample = {}, {}, None
    for k, g in AOIS.items():
        body = {"collections": [collection], "bbox": list(g.bounds), "limit": limit}
        if dt:
            body["datetime"] = dt
        body.update(extra or {})
        st, o = stac_search(search_url, body)
        status[k] = st
        f = o.get("features", [])
        counts[k] = len(f)
        if f and sample is None:
            sample = (k, f[0])
    body = {"collections": [collection], "bbox": list(CONTROL.bounds), "limit": limit}
    if dt:
        body["datetime"] = dt
    body.update(extra or {})
    st, o = stac_search(search_url, body)
    control = len(o.get("features", []))
    diff = ""
    if filt:
        tests = [k for k in ("farm_sk_quarter", "city_toronto_core", "mine_hvc_bc", "mine_sudbury_on") if counts.get(k)]
        res = []
        for k in tests:
            b = {"collections": [collection], "bbox": list(AOIS[k].bounds), "limit": limit}
            if dt:
                b["datetime"] = dt
            b.update(extra or {})
            b.update(filt)
            _, o2 = stac_search(search_url, b)
            res.append(f"{k}:{counts[k]}->{len(o2.get('features', []))}")
        diff = "cloud filter differential " + ", ".join(res)
    hits = sum(1 for v in counts.values() if v > 0)
    return hits, counts, control, status, sample, diff


# ------------------------------------------------------------------ Q1 backfill rows
def q1_rows(df):
    n = len(df)
    spec = {
        "sentinel2_l2a": ("sentinel-2-l2a", "Sentinel-2 L2A (re-query of POC ids)", "satellite",
                          "granule-metadata asset (MTD_TL.xml) Mean_Viewing_Incidence_Angle_List/Mean_Viewing_Incidence_Angle[@bandId]/ZENITH_ANGLE; sidecar XML, not in item properties"),
        "landsat_c2l2_st": ("landsat-c2-l2", "Landsat C2 L2 (re-query of POC ids)", "satellite", "view:off_nadir (item property)"),
        "sentinel1_rtc": ("sentinel-1-rtc", "Sentinel-1 RTC (re-query of POC ids)", "satellite",
                          "per-pixel; RTC item has only vv/vh assets. Incidence angle is in the GRD sidecar annotation/iw-vv.xml (geolocationGrid/geolocationGridPoint/incidenceAngle, 210 points; also imageAnnotation/.../incidenceAngleMidSwath)"),
    }
    for ad, (coll, name, st, off) in spec.items():
        g = df[df.adapter == ad]
        ok = g[g.status == "ok"]
        stac, o = stac_search(f"{PC}/search", {"collections": [coll], "bbox": list(CONTROL.bounds), "limit": 5, "datetime": WINDOW})
        row0 = ok.iloc[0]
        def have(c):
            s = ok[c].astype(str)
            return int(((s != "") & (s != "nan") & (s != "n/a") & (s != "per-pixel")).sum())
        cnt = {c: have(c) for c in ["off_nadir_deg", "sun_elevation_deg", "sun_azimuth_deg", "cloud_cover_scene_pct", "cloud_cover_aoi_pct", "processing_level", "relative_orbit"]}
        sample = f"sample {row0.aoi_id}: off_nadir {row0.off_nadir_deg}, sun_el {row0.sun_elevation_deg}, scene cloud {row0.cloud_cover_scene_pct}, AOI cloud {row0.cloud_cover_aoi_pct}"
        r = req("GET", f"{PC}/collections/{coll}/items/{row0.item_id}")
        props = r.json()["properties"]
        add(gap="Q1", candidate=name, source_type=st, endpoint=f"{PC}/collections/{coll}/items/{{item_id}}",
            auth="none", reachable="yes", http_status=r.status_code, aoi_hits=f"{len(ok.aoi_id.unique())}/15",
            control_passed="yes" if len(o.get("features", [])) == 0 else "no",
            observation_unit="acquisition", quality_fields=qc_keys(props), off_nadir_field=off, licence="Copernicus/Landsat open (PC: proprietary tag, free)",
            notes=f"{len(ok)}/{len(g)} scene ids of this adapter resolved ({n} across the three); fields filled {cnt}. {sample}. Control bbox returns {len(o.get('features', []))} items in the POC window.")


# ------------------------------------------------------------------ Maxar
def maxar():
    base = "https://maxar-opendata.s3.amazonaws.com/events/"
    st, cat = get_json(base + "catalog.json")
    ev = []
    for l in cat["links"]:
        if l["rel"] != "child":
            continue
        s2, c = get_json(base + l["href"].lstrip("./"))
        if c is None:
            continue
        bbs = c["extent"]["spatial"]["bbox"]
        ev.append((l["href"].split("/")[1], bbs, c["extent"]["temporal"]["interval"][0], c))
    hits = {k: [] for k in AOIS}
    for k, g in AOIS.items():
        for name, bbs, _, _ in ev:
            if any(box(*b).intersects(g) for b in bbs):
                hits[k].append(name)
    ctl = [n for n, bbs, _, _ in ev if any(box(*b).intersects(CONTROL) for b in bbs)]
    maui = next(e for e in ev if e[0].startswith("Maui"))
    pos = [n for n, bbs, _, _ in ev if any(box(*b).intersects(box(*maui[1][0])) for b in bbs)]
    # sample item: the Canadian event with the widest bbox list
    can = next((e for e in ev if e[0].startswith("NWT-Canada")), ev[0])
    ac = [l for l in can[3]["links"] if l["rel"] == "child"][0]["href"]
    base_ev = base + can[0] + "/"
    st2, acq = get_json(urljoin(base_ev, ac))
    ii = [l["href"] for l in acq["links"] if l["rel"] == "item"][0]
    st3, item = get_json(urljoin(urljoin(base_ev, ac), ii))
    p = item["properties"]
    nh = sum(1 for v in hits.values() if v)
    can_ev = [e[0] for e in ev if e[1][0][0] < -50 and e[1][0][1] > 41]
    add(gap="S4", candidate="Maxar Open Data (events)", source_type="satellite",
        endpoint="https://maxar-opendata.s3.amazonaws.com/events/catalog.json -> {event}/collection.json -> ard/acquisition_collections/{catalog_id}_collection.json -> item",
        auth="none", reachable="yes", http_status=st, aoi_hits=f"{nh}/15", control_passed="yes" if not ctl else "no",
        observation_unit="acquisition",
        quality_fields=";".join(k for k in p if QC_RE.match(k)),
        off_nadir_field=f"view:off_nadir (item property, Maxar ARD tile; sample {p.get('view:off_nadir')} deg) and view:incidence_angle ({p.get('view:incidence_angle')} deg, at ground); view:azimuth, view:sun_elevation also item properties",
        licence="CC-BY-NC-4.0",
        notes=f"Static catalog, no search endpoint: {len(ev)} event collections, bbox-intersected client-side. 0 AOI hits is coverage (event-based, mostly hurricanes/floods/fires). Positive control (Maui bbox) matches {pos}. Canadian/near events: {can_ev}. Sample item {item['id']} from {can[0]}: platform {p.get('platform')}, gsd {p.get('gsd')}, tile:clouds_percent {p.get('tile:clouds_percent')}, tile:data_area {p.get('tile:data_area')}. Cloud is a per-tile area percent, not per-AOI.")


# ------------------------------------------------------------------ Satellogic
def satellogic():
    B = "https://satellogic-earthview.s3.us-west-2.amazonaws.com/"
    st0 = req("GET", B + "stac/catalog.json").status_code

    def zone_regions(z):
        f = CACHE / f"satl_zone_{z}.json"
        if f.exists():
            return json.load(open(f))
        pre, _ = s3_list(B, f"data/json/zone={z}/", "/")
        regs = []
        for p in pre:
            m = re.search(r"region=(\d+)_(\d+)/", p)
            if m:
                regs.append((int(m.group(1)), int(m.group(2))))
        json.dump(regs, open(f, "w"))
        return regs

    zones_avail = {m.group(1) for m in (re.search(r"zone=(\w+)/", p) for p in s3_list(B, "data/json/", "/")[0]) if m}

    def find(geom4326):
        c = geom4326.centroid
        zone = int((c.x + 180) // 6) + 1
        z = f"{zone:02d}{'N' if c.y >= 0 else 'S'}"
        if z not in zones_avail:
            return z, []
        tr = Transformer.from_crs("EPSG:4326", f"EPSG:{32600 + zone if c.y >= 0 else 32700 + zone}", always_xy=True).transform
        g = shp_transform(tr, geom4326)
        regs = zone_regions(z)
        return z, [(e, n) for e, n in regs if box(e, n - 384, e + 384, n).intersects(g)]

    hits, zones = {}, {}
    for k, g in AOIS.items():
        zones[k], hits[k] = find(g)
    zc, ctl = find(CONTROL)
    # sample: first hit region, newest date listing
    sample, note_s = None, ""
    for k, h in hits.items():
        if h:
            e, n = h[0]
            pre, keys = s3_list(B, f"data/json/zone={zones[k]}/region={e}_{n}/", "/")
            dates = sorted(p.split("date=")[1].strip("/") for p in pre if "date=" in p)
            if dates:
                _, ks = s3_list(B, f"data/json/zone={zones[k]}/region={e}_{n}/date={dates[0]}/", "/")
                mk = [x for x in ks if x.endswith("_metadata.json")]
                if mk:
                    st, sample = get_json(B + mk[0])
                    note_s = f"sample {sample['id']} for AOI {k}, {len(dates)} dates in region"
                    break
    # positive control: a known item must be found by the same code path
    st, pitem = get_json("https://satellogic-earthview.s3.us-west-2.amazonaws.com/data/json/zone=11N/region=302226_4501997/date=2022-07-01/20220701_191118_SN27_11N_302226_4501997_metadata.json")
    pg = shape(pitem["geometry"])
    _, pz = find(pg)
    props = (sample or pitem)["properties"]
    nh = sum(1 for v in hits.values() if v)
    add(gap="S4", candidate="Satellogic EarthView", source_type="satellite",
        endpoint="s3 listing https://satellogic-earthview.s3.us-west-2.amazonaws.com/?list-type=2&prefix=data/json/zone={UTM}/ (region=E_N is a 384 m UTM tile, upper-left corner) then {item}_metadata.json; static STAC at /stac/catalog.json (date tree, 18k items/day)",
        auth="none", reachable="yes", http_status=st0, aoi_hits=f"{nh}/15", control_passed="yes" if not ctl else "no",
        observation_unit="acquisition", quality_fields=";".join(k for k in props if QC_RE.match(k)),
        off_nadir_field=f"view:off_nadir (item property in {{item}}_metadata.json; sample {props.get('view:off_nadir')} deg); view:azimuth, view:sun_elevation, view:sun_azimuth alongside",
        licence="CC-BY-4.0",
        notes=f"No search API; area lookup done by listing the zone's region prefixes and intersecting 384 m tiles in UTM. Jul-Dec 2022 only. Positive control (known item) found by same code: {bool(pz)}. {note_s}. Zones probed: {sorted(set(zones.values()))}. No cloud field in the item (TOA reflectance product; cloud mask not in metadata). Hits per AOI: { {k: len(v) for k, v in hits.items() if v} }.")


# ------------------------------------------------------------------ static SAR / planet catalogs
def static_catalog(gap, candidate, cache_name, endpoint, licence, root_url, extra_notes="", source_type="satellite", unit="acquisition", extra_geoms=None):
    f = CACHE / f"sar_{cache_name}.json"
    st = req("GET", root_url).status_code
    if not f.exists():
        add(gap=gap, candidate=candidate, source_type=source_type, endpoint=endpoint, auth="none", reachable="partial", http_status=st,
            aoi_hits="n/a", control_passed="n/a", observation_unit=unit, quality_fields="", off_nadir_field="unknown (crawl not finished)",
            licence=licence, notes="crawl cache missing; run crawl_sar.py " + cache_name)
        return
    items = [i for i in json.load(open(f)) if not i["id"].startswith("000-")]  # ICEYE footprint pseudo-items
    for i in items:
        i.setdefault("geometry", None)
    hits = item_hits(items, AOIS)
    ctl = item_hits(items, {"control": CONTROL})["control"]
    # positive control: the first item's own centroid must hit
    it0 = items[0]
    g0 = shape(it0["geometry"]) if it0["geometry"] else box(*it0["bbox"])
    pos = item_hits(items, {"p": g0.centroid.buffer(1e-4)})["p"]
    extra = 0
    if extra_geoms:
        for k, g in AOIS.items():
            if any(g.intersects(e) for e in extra_geoms):
                hits[k] = hits[k] + ["(collection bbox)"]
    nh = sum(1 for v in hits.values() if v)
    mf = CACHE / f"sar_{cache_name}_meta.json"
    if mf.exists():
        extra_notes += " Crawl meta " + json.dumps(json.load(open(mf))) + "."
    byid = {i["id"]: i for i in items}
    first_hit = next((v[0] for v in hits.values() if v and v[0] in byid), None)
    best = byid[first_hit] if first_hit else max(items, key=lambda i: len(i["properties"]))
    def brief(iid):
        q = byid.get(iid)
        if not q:
            return iid
        o = offnadir_keys(q["properties"])
        return f"{iid} {str(q['properties'].get('datetime'))[:10]} " + ",".join(f"{k}={v}" for k, v in o[:2])
    hit_txt = {k: sorted({brief(x) for x in v})[:3] for k, v in hits.items() if v}
    p = best["properties"]
    off = offnadir_keys(p)
    offs = "; ".join(f"{k} ({v})" for k, v in off) or "none found in item properties"
    yrs = pd.Series([(i["properties"].get("datetime") or "none")[:4] for i in items]).value_counts().sort_index().to_dict()
    add(gap=gap, candidate=candidate, source_type=source_type, endpoint=endpoint, auth="none", reachable="yes", http_status=st,
        aoi_hits=f"{nh}/15", control_passed="yes" if not ctl else "no", observation_unit=unit,
        quality_fields=qc_keys(p), off_nadir_field=f"{offs} (item property, sample item {best['id']})", licence=licence,
        notes=f"Static STAC tree crawled once ({len(items)} items, years {yrs}); bbox/geometry intersected client-side, positive control (item's own centroid) matched {len(pos)}. Hits by AOI (id date off-nadir fields): {hit_txt}. {extra_notes}")


def planet_extra_geoms():
    """Fusion (one Nebraska collection) and SpaceNet 7 (one item per L15 tile) are not in the crawl; add their footprints."""
    gs = []
    st, o = get_json("https://www.planet.com/data/stac/fusion/14N/29E-188N/collection.json")
    if o:
        gs.append(box(*o["extent"]["spatial"]["bbox"][0]))
    seen = set()
    for c in ("sn7_train_source", "sn7_test_source"):
        st, o = get_json(f"https://www.planet.com/data/stac/spacenet7/{c}/collection.json")
        for l in (o or {}).get("links", []):
            m = re.search(r"L15-\d+E-\d+N", l["href"]) if l["rel"] == "item" else None
            if m and m.group(0) not in seen:
                seen.add(m.group(0))
                st, it = get_json(l["href"])
                if it:
                    gs.append(shape(it["geometry"]))
    return gs


def licence_of(url):
    st, o = get_json(url)
    return (o or {}).get("license", "")


# ------------------------------------------------------------------ Planet NICFI on PC
def nicfi():
    st = req("GET", f"{PC}/collections/planet-nicfi-analytic").status_code
    hits, counts, control, status, sample, _ = stac_area_probe(f"{PC}/search", "planet-nicfi-analytic", None)
    r = req("GET", f"{PC}/collections/planet-nicfi-analytic/items?limit=1").json()["features"][0]
    bb = r["bbox"]
    _, posj = stac_search(f"{PC}/search", {"collections": ["planet-nicfi-analytic"], "bbox": bb, "limit": 5})
    sas = req("GET", "https://planetarycomputer.microsoft.com/api/sas/v1/token/planet/nicfi").status_code
    add(gap="S4", candidate="Planet NICFI basemaps (Planetary Computer, analytic)", source_type="satellite",
        endpoint=f"{PC}/search (collections=planet-nicfi-analytic, bbox)", auth="key-we-lack", reachable="partial", http_status=st,
        aoi_hits=f"{hits}/15", control_passed="yes" if control == 0 else "no", observation_unit="composite",
        quality_fields=qc_keys(r["properties"]) + ";start_datetime;end_datetime", off_nadir_field="none (monthly/biannual mosaic; no per-scene view angle in item properties)",
        licence="Planet NICFI Participant License (non-commercial; collection tagged proprietary)",
        notes=f"STAC metadata is public, pixels are not: SAS token endpoint .../sas/v1/token/planet/nicfi returned HTTP {sas} (collection note: assets only for GEO-Microsoft PC RFP winners). Tropics only (collection bbox lat -34.2..30.1), so 0/15 AOIs is coverage. Positive control (sample tile bbox {bb}) returns {len(posj.get('features', []))} items. Sample item {r['id']}: gsd {r['properties'].get('gsd')}, cadence {r['properties'].get('planet-nicfi:cadence')}. No cloud or angle metadata.")


# ------------------------------------------------------------------ HLS
def hls_vza(item, geom):
    href = pc.sign(item["assets"]["VZA"]["href"])
    c = geom.centroid
    with rasterio.open(href) as src:
        x, y = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform(c.x, c.y)
        v = next(src.sample([(x, y)]))[0]
        sc = src.scales[0] if src.scales else 1
    return float(v) * (0.01 if sc == 1 else sc)


def hls():
    for coll, tag in (("hls2-l30", "L30"), ("hls2-s30", "S30")):
        st = req("GET", f"{PC}/collections/{coll}").status_code
        hits, counts, control, status, sample, diff = stac_area_probe(f"{PC}/search", coll, WINDOW, filt={"query": {"eo:cloud_cover": {"lt": 5}}})
        k, it = sample
        p = it["properties"]
        vza = hls_vza(it, AOIS[k])
        umm = req("GET", "https://cmr.earthdata.nasa.gov/search/granules.umm_json", params={"provider": "LPCLOUD", "granule_ur": it["id"], "page_size": 1})
        mvz = ""
        try:
            for a in umm.json()["items"][0]["umm"]["AdditionalAttributes"]:
                if a["Name"] in ("MEAN_VIEW_ZENITH_ANGLE", "MEAN_VIEW_AZIMUTH_ANGLE", "MEAN_SUN_ZENITH_ANGLE", "SPATIAL_COVERAGE", "CLOUD_COVERAGE"):
                    mvz += f"{a['Name']}={a['Values'][0]}; "
        except Exception:
            mvz = f"CMR granule lookup HTTP {umm.status_code} gave no UMM"
        add(gap="Q1", candidate=f"HLS {tag} v2.0 (Planetary Computer)", source_type="satellite",
            endpoint=f"{PC}/search (collections={coll}, bbox, datetime)", auth="none", reachable="yes", http_status=st,
            aoi_hits=f"{hits}/15", control_passed="yes" if control == 0 else "no", observation_unit="acquisition",
            quality_fields=qc_keys(p) + ";Fmask(asset)",
            off_nadir_field=f"VZA asset (per-pixel view zenith COG, scale 0.01 deg; value at {k} centroid {vza:.2f} deg); item properties carry only view:azimuth (no zenith/off_nadir). Scene mean in CMR UMM AdditionalAttributes MEAN_VIEW_ZENITH_ANGLE",
            licence="NASA open (proprietary tag on PC; free)",
            notes=f"{diff}. Sample {it['id']} (AOI {k}): eo:cloud_cover {p.get('eo:cloud_cover')}, view:sun_azimuth {p.get('view:sun_azimuth')}, no sun elevation property (SZA asset). CMR UMM for same granule: {mvz}. Per-AOI counts {counts}. Control bbox {control} items.")
    # CMR-STAC
    for coll, tag in (("HLSL30_2.0", "L30"), ("HLSS30_2.0", "S30")):
        st = req("GET", f"{CMR}/collections/{coll}").status_code
        counts, sample = {}, None
        for k, g in AOIS.items():
            s, o = stac_search(f"{CMR}/search", {"collections": [coll], "bbox": list(g.bounds), "datetime": WINDOW.replace("T23:59:59Z", "T23:59:59Z"), "limit": 50})
            f = o.get("features", [])
            counts[k] = (o.get("context", {}) or {}).get("matched", len(f))
            if f and sample is None:
                sample = (k, f[0])
        s, o = stac_search(f"{CMR}/search", {"collections": [coll], "bbox": list(CONTROL.bounds), "datetime": WINDOW, "limit": 5})
        ctl = (o.get("context", {}) or {}).get("matched", len(o.get("features", [])))
        hitsn = sum(1 for v in counts.values() if v)
        p = sample[1]["properties"] if sample else {}
        add(gap="Q1", candidate=f"HLS {tag} via NASA CMR-STAC (LPCLOUD)", source_type="satellite",
            endpoint=f"{CMR}/search (collections={coll})", auth="free-reg", reachable="yes", http_status=st,
            aoi_hits=f"{hitsn}/15", control_passed="yes" if ctl == 0 else "no", observation_unit="acquisition",
            quality_fields=";".join(p.keys()) + ";assets Fmask",
            off_nadir_field="VZA asset (per-pixel COG; href needs Earthdata login) and CMR UMM AdditionalAttributes MEAN_VIEW_ZENITH_ANGLE (public, scene mean); STAC item properties hold only eo:cloud_cover",
            licence="NASA open (free; asset download needs Earthdata Login)",
            notes=f"Search needs no login; asset download redirects to Earthdata. Item properties are minimal (cloud only), so use the UMM record for angles. Counts per AOI {counts}; control matched {ctl}.")


# ------------------------------------------------------------------ Earth Search L1C and Landsat L1
def s2_l1c():
    st = req("GET", f"{ES}/collections/sentinel-2-l1c").status_code
    hits, counts, control, status, sample, diff = stac_area_probe(f"{ES}/search", "sentinel-2-l1c", WINDOW, filt={"query": {"eo:cloud_cover": {"lt": 5}}})
    k, it = sample
    p = it["properties"]
    mtd = req("GET", it["assets"]["granule_metadata"]["href"].replace("s3://sentinel-s2-l1c/", "https://sentinel-s2-l1c.s3.amazonaws.com/"))
    zen = ""
    if mtd.status_code == 200:
        root = ET.fromstring(mtd.content)
        z = [float(e.text) for m in root.iter() if m.tag.endswith("Mean_Viewing_Incidence_Angle") for e in m if e.tag.endswith("ZENITH_ANGLE")]
        zen = f"{np.mean(z):.3f} deg (mean of {len(z)} bands)" if z else "no Mean_Viewing_Incidence_Angle in XML"
    else:
        zen = f"metadata.xml HTTP {mtd.status_code}"
    pcl1c = stac_search(f"{PC}/search", {"collections": ["sentinel-2-l1c"], "bbox": list(AOIS['farm_sk_quarter'].bounds), "limit": 3})
    add(gap="S5", candidate="Sentinel-2 L1C (Earth Search)", source_type="satellite",
        endpoint=f"{ES}/search (collections=sentinel-2-l1c, bbox, datetime)", auth="none", reachable="yes", http_status=st,
        aoi_hits=f"{hits}/15", control_passed="yes" if control == 0 else "no", observation_unit="acquisition",
        quality_fields=qc_keys(p),
        off_nadir_field=f"not in item properties. granule_metadata asset (s3://sentinel-s2-l1c/tiles/.../metadata.xml, readable over https) Mean_Viewing_Incidence_Angle_List/ZENITH_ANGLE; sample {zen}",
        licence="Copernicus open (Sentinel Data Legal Notice)",
        notes=f"{diff}. Per-AOI counts {counts}. Sample {it['id']} (AOI {k}): eo:cloud_cover {p.get('eo:cloud_cover')}, view:sun_elevation {p.get('view:sun_elevation')}, s2:product_type {p.get('s2:product_type')} (L1C = TOA, uncorrected), s2:processing_baseline {p.get('s2:processing_baseline')}. Planetary Computer search on collection sentinel-2-l1c for farm_sk_quarter returns {len(pcl1c[1].get('features', []))} items (HTTP {pcl1c[0]}); counts are capped at the 100-item page limit. No cloud-shadow breakdown in L1C items.")


def landsat_l1():
    st = req("GET", f"{LL}/collections/landsat-c2l1").status_code
    hits, counts, control, status, sample, diff = stac_area_probe(f"{LL}/search", "landsat-c2l1", WINDOW, filt={"query": {"eo:cloud_cover": {"lt": 5}}})
    k, it = sample
    p = it["properties"]
    dl = requests.head(it["assets"]["red"]["href"], allow_redirects=False, timeout=30)
    add(gap="S5", candidate="Landsat C2 L1 (USGS LandsatLook STAC)", source_type="satellite",
        endpoint=f"{LL}/search (collections=landsat-c2l1, bbox, datetime)", auth="free-reg", reachable="yes", http_status=st,
        aoi_hits=f"{hits}/15", control_passed="yes" if control == 0 else "no", observation_unit="acquisition",
        quality_fields=qc_keys(p),
        off_nadir_field=f"view:off_nadir (item property; sample {p.get('view:off_nadir')}); per-pixel VZA/VAA/SZA/SAA assets and ANG.txt for angles",
        licence="USGS public domain",
        notes=f"{diff}. Per-AOI counts {counts}. Search is anonymous; asset GET returns HTTP {dl.status_code} redirect to ers.cr.usgs.gov (EROS login). Sample {it['id']} (AOI {k}): correction {p.get('landsat:correction')} (L1TP = terrain-corrected TOA), eo:cloud_cover {p.get('eo:cloud_cover')}, view:sun_elevation {p.get('view:sun_elevation')}, accuracy:geometric_rmse {p.get('accuracy:geometric_rmse')}. Earth Search has only landsat-c2-l2 (no L1) and Planetary Computer likewise.")


# ------------------------------------------------------------------ brokers
def skyfi():
    S = "https://app.skyfi.com/platform-api"
    st = req("GET", f"{S}/openapi.json")
    o = st.json()
    sc = o["components"]["schemas"]
    ar = list(sc["ArchiveResponse"]["properties"])
    rq = list(sc["GetArchivesRequest"]["properties"])
    aoi = "POLYGON((-106.305868 51.996387,-106.294132 51.996387,-106.294132 52.003613,-106.305868 52.003613,-106.305868 51.996387))"
    codes = {}
    for m, p, body in (("POST", "/archives", {"aoi": aoi, "maxOffNadirAngle": 20}), ("POST", "/pricing", {"aoi": aoi}),
                       ("GET", "/providers", None), ("POST", "/tasking/products", {"aoi": aoi}), ("GET", "/ping", None)):
        r = req(m, S + p, json=body)
        codes[p] = r.status_code
    add(gap="S4", candidate="SkyFi Platform API (archive search + quote)", source_type="satellite", endpoint=f"{S}/archives (POST), {S}/pricing (POST), {S}/openapi.json",
        auth="key-we-lack", reachable="partial", http_status=codes["/archives"], aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields=";".join(ar), off_nadir_field="offNadirAngle (ArchiveResponse field, degrees, range -90..90, example 30.0); request filter maxOffNadirAngle (0..50)",
        licence="per provider; archive has openData boolean flag",
        notes=f"OpenAPI spec and docs are public (v{o['info']['version']}); every data endpoint returns 401 'Use X-Skyfi-Api-Key header' (statuses {codes}), only /ping is open. No public price or archive preview without a key. Quote per docs: POST /archives {{aoi WKT, fromDate, toDate, maxCloudCoveragePercent, maxOffNadirAngle, resolutions, productTypes, providers, openData}} returns archives[] with archiveId, provider, constellation, productType, resolution, captureTimestamp, cloudCoveragePercent, offNadirAngle, footprint, priceForOneSquareKm (USD), priceFullScene (USD), minSqKm, maxSqKm, openData, deliveryTimeHours, gsd; POST /pricing {{aoi}} returns tasking price per sq km by productType/resolution/provider; POST /order-archive/validate checks an order without buying. Request fields: {rq}.")


def up42():
    c = req("GET", "https://api.up42.com/collections")
    d = c.json()["data"]
    types = pd.Series([x["type"] for x in d]).value_counts().to_dict()
    names = sorted({x["hostName"] for x in d})
    c2 = req("GET", "https://api.up42.com/v2/collections", params={"size": 200}).json()["content"]
    integ = pd.Series([i for x in c2 for i in x.get("integrations", [])]).value_counts().to_dict()
    se = req("POST", "https://api.up42.com/catalog/hosts/oneatlas/stac/search", json={"collections": ["PHR"], "bbox": [-106.3, 51.99, -106.29, 52.0], "limit": 1})
    es = req("POST", "https://api.up42.com/v2/orders/estimate", json={})
    add(gap="S4", candidate="UP42 (catalog search + order estimate)", source_type="satellite",
        endpoint="https://api.up42.com/collections (GET, public); https://api.up42.com/catalog/hosts/{host}/stac/search (POST); https://api.up42.com/v2/orders/estimate (POST)",
        auth="paid", reachable="partial", http_status=c.status_code, aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields="cloudCoverage (search query/response property); acquisitionDate; start_datetime; end_datetime; id",
        off_nadir_field="per-host STAC property, not uniform; docs list incidence angle and off-nadir angle as collection specs (Pleiades: incidence 5-50 deg, off-nadir 30 deg); tasking order param maxIncidenceAngle. Search-result property name not verifiable without a token",
        licence="per host/collection EULA; credits-based",
        notes=f"Public: collection list ({len(d)} collections, types {types}, {len(names)} hosts incl. vantor, oneatlas, capellaspace, iceye, umbra, planet, satellogic) with integrations flags {integ}. Search returns HTTP {se.status_code} and estimate HTTP {es.status_code} without a bearer token. Docs state per-collection price floors in credits per km2 (Pleiades catalog from 1,000, tasking from 1,700 credits/km2). A quote per docs: search body {{collections, bbox, datetime, limit, query:{{cloudCoverage:{{LTE:90}}}}}} returns features with properties.id, acquisitionDate, cloudCoverage; POST /v2/orders/estimate returns credits for aoi + data product.")


def sentinel_hub():
    out = {}
    for tag, base in (("sh", "https://services.sentinel-hub.com/api/v1/catalog/1.0.0"), ("cdse", "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0")):
        c = req("GET", base + "/collections")
        ids = [x["id"] for x in c.json().get("collections", [])]
        s = req("POST", base + "/search", json={"collections": ["sentinel-2-l2a"], "bbox": [-106.3, 51.99, -106.29, 52.0], "datetime": "2024-08-01T00:00:00Z/2024-09-01T00:00:00Z", "limit": 2})
        q = req("GET", base + "/collections/sentinel-2-l2a/queryables")
        out[tag] = (c.status_code, ids, s.status_code, q.status_code)
    add(gap="S4", candidate="Sentinel Hub Catalog API (Sinergise) and CDSE instance", source_type="satellite",
        endpoint="https://services.sentinel-hub.com/api/v1/catalog/1.0.0/search (POST); https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search",
        auth="free-reg", reachable="partial", http_status=out["sh"][2], aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields="eo:cloud_cover; datetime; platform; instrument; gsd (collection summaries)",
        off_nadir_field="none in catalog items (open collections only; S2 view angles are in the granule metadata, not the catalog)",
        licence="Copernicus open for S2/S1; commercial (Planet, Airbus, Maxar) via paid Third Party Data Import",
        notes=f"Collection list is anonymous: services.sentinel-hub.com {out['sh'][1]}; CDSE {out['cdse'][1]}. Search, items and queryables return 401 without an OAuth bearer (statuses SH search {out['sh'][2]}, queryables {out['sh'][3]}; CDSE search {out['cdse'][2]}). Registration is free for CDSE; commercial archive search is part of the paid TPDI service, priced in Processing Units per the docs. A quote is not a catalog call: it returns scene id, datetime, eo:cloud_cover only. No price field in the catalog.")


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    import backfill
    if "--skip-backfill" in sys.argv and (LANE / "scene_qc_backfill.csv").exists():
        df = pd.read_csv(LANE / "scene_qc_backfill.csv", keep_default_na=False)
    else:
        df = backfill.run().fillna("")
    q1_rows(df)
    maxar()
    satellogic()
    static_catalog("S4", "Umbra open SAR data", "umbra", "https://umbra-open-data-catalog.s3.amazonaws.com/stac/catalog.json (static year/month/day tree)", licence_of("https://umbra-open-data-catalog.s3.amazonaws.com/stac/catalog.json") or "CC-BY-4.0", "https://umbra-open-data-catalog.s3.amazonaws.com/stac/catalog.json")
    static_catalog("S4", "Capella open SAR data", "capella", "https://capella-open-data.s3.us-west-2.amazonaws.com/stac/catalog.json (static catalog, by-datetime branch crawled)", "CC-BY-4.0", "https://capella-open-data.s3.us-west-2.amazonaws.com/stac/catalog.json")
    static_catalog("S4", "ICEYE open SAR data", "iceye", "https://iceye-open-data-catalog.s3.amazonaws.com/collections/iceye-sar.json (static)", licence_of("https://iceye-open-data-catalog.s3.amazonaws.com/collections/iceye-sar.json") or "CC-BY-NC-4.0", "https://iceye-open-data-catalog.s3.amazonaws.com/catalog.json")
    static_catalog("S4", "Planet open STAC (Open SkySat, Open Canada, disasters, education, Tanager)", "planet", "https://www.planet.com/data/stac/catalog.json (static; spacenet7 and fusion not crawled)", "CC-BY-SA-4.0 / CC-BY-NC (per collection)", "https://www.planet.com/data/stac/catalog.json", extra_notes="All three hits are Tanager-1 hyperspectral core-imagery scenes (424 bands, gsd ~36 m; relevant to gap S3), not SkySat or PlanetScope. Open SkySat has 5 sites (San Francisco is the only one in North America). Open Canada is Fort McKay AB only; its psscene collection (11 items) and the lst/swc/arps products do not intersect any AOI. Also checked Fusion (Nebraska) and one item per SpaceNet 7 L15 tile.", extra_geoms=planet_extra_geoms())
    nicfi()
    hls()
    s2_l1c()
    landsat_l1()
    skyfi()
    up42()
    sentinel_hub()
    with open(LANE / "A_probes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(ROWS)
    print("wrote", len(ROWS), "rows")

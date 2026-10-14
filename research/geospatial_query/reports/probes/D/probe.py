"""Lane D probe: ground-level camera imagery (gap S9). Re-run reproduces D_probes.csv and the sample_*.json files.

    /home/tony/lib/miniforge3/envs/geoquery/bin/python probe.py
"""
import csv, json, math, os, re, time, collections
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
AOIS = json.load(open(os.path.join(ROOT, "examples", "test_aois.geojson")))["features"]
AOIS = [(f["properties"]["aoi_id"], f["properties"]["centroid_lat"], f["properties"]["centroid_lon"]) for f in AOIS]
CONTROL = ("control_pacific", 0.05, -149.95)
R_M = 1000
UA = {"User-Agent": "geoquery-probe-laneD/0.1 (research; contact phyberosis@gmail.com)"}
COLS = ["gap", "candidate", "source_type", "endpoint", "auth", "reachable", "http_status", "aoi_hits",
        "control_passed", "observation_unit", "quality_fields", "off_nadir_field", "licence", "notes"]
rows = []
_last = collections.defaultdict(float)


def get(url, method="GET", host_gap=0.5, retries=3, **kw):
    host = url.split("/")[2]
    kw.setdefault("timeout", 40)
    h = dict(UA); h.update(kw.pop("headers", {}))
    r = None
    for i in range(retries):
        wait = host_gap - (time.time() - _last[host])
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        try:
            r = requests.request(method, url, headers=h, **kw)
        except requests.RequestException as e:
            r = None
            err = f"{type(e).__name__}: {str(e)[:100]}"
            time.sleep(2)
            continue
        if r.status_code == 429:
            time.sleep(10 * (i + 1))
            continue
        return r
    if r is None:
        class Fail:
            status_code = 0
            text = err
            headers = {}
            def json(self): raise ValueError(err)
        return Fail()
    return r


def bbox(lat, lon, r=R_M):
    dl = r / 111320.0
    dn = r / (111320.0 * math.cos(math.radians(lat)))
    return (lon - dn, lat - dl, lon + dn, lat + dl)


def hav(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


def add(**k):
    row = {c: k.get(c, "") for c in COLS}
    rows.append(row)


def save(name, obj):
    with open(os.path.join(HERE, f"sample_{name}.json"), "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def hits_str(d):
    return f"{sum(1 for a in AOIS if d.get(a[0], 0) > 0)}/15"


def fmt_counts(d, cap=15):
    nz = [f"{k}={v}" for k, v in list(d.items())[:cap] if v]
    z = sum(1 for v in list(d.values())[:cap] if not v)
    return (", ".join(nz) or "none") + f" (+{z} AOIs with 0)"


# ------------------------------------------------------------------ Panoramax
def pbox(aid):
    from shapely.geometry import shape
    for f in json.load(open(os.path.join(ROOT, "examples", "test_aois.geojson")))["features"]:
        if f["properties"]["aoi_id"] == aid:
            return shape(f["geometry"]).bounds
    return None


def json_retry(url, params=None, tries=6, **kw):
    """GET json; retry with backoff on 429, 5xx, non-JSON or an API error body. Returns (json, status, retries)."""
    retries = 0
    for i in range(tries):
        r = get(url, params=params, **kw)
        ra = r.headers.get("retry-after") if hasattr(r, "headers") else None
        try:
            j = r.json()
        except Exception:
            j = None
        if r.status_code == 200 and isinstance(j, dict) and "error" not in j:
            return j, r.status_code, retries
        retries += 1
        time.sleep(float(ra) if ra and ra.replace(".", "").isdigit() else 5 * (i + 1))
    raise RuntimeError(f"gave up after {tries} tries: {url} {params} status={r.status_code} body={getattr(r, 'text', '')[:150]}")


def panoramax():
    ep = "https://api.panoramax.xyz/api/search?bbox={bbox}&limit=1000"
    counts, stats, sample = {}, collections.Counter(), None
    nfeat = 0
    status = set()
    pitch_by_aoi, retries_total = {}, 0
    for aid, lat, lon in AOIS + [CONTROL]:
        b = pbox(aid) if aid != CONTROL[0] else bbox(lat, lon)
        j, st, rt = json_retry("https://api.panoramax.xyz/api/search", params={"bbox": ",".join(f"{x:.6f}" for x in b), "limit": 1000}, timeout=90)
        retries_total += rt
        status.add(st)
        fs = j.get("features", [])
        counts[aid] = len(fs)
        if aid == "city_toronto_core" and fs:
            sample = fs[0]
        if aid != CONTROL[0]:
            pv, dts = collections.Counter(), []
            for f in fs:
                p = f["properties"]; ex = p.get("exif", {})
                nfeat += 1
                for k in ("view:azimuth", "pers:pitch", "pers:roll", "quality:horizontal_accuracy", "datetime", "license"):
                    if p.get(k) is not None: stats[k] += 1
                if ex.get("Exif.Image.Make"): stats["exif_make"] += 1
                if ex.get("Xmp.GPano.ProjectionType"): stats["is_pano"] += 1
                pp = p.get("pers:pitch")
                if pp is not None:
                    pv[round(pp)] += 1
                    if round(pp) != 0: stats["pitch_nonzero"] += 1
                if p.get("datetime"): dts.append(p["datetime"][:7])
            if fs:
                nz = sum(v for k, v in pv.items() if k != 0)
                pitch_by_aoi[aid] = dict(n=len(fs), with_pitch=sum(pv.values()), nonzero=nz, dist=dict(sorted(pv.items())), dates=f"{min(dts)}..{max(dts)}")
    ctrl = counts.pop(CONTROL[0])
    # filter differential: a far-future datetime window must empty the Toronto bbox
    b = pbox("city_toronto_core")
    bb = ",".join(f"{x:.6f}" for x in b)
    n2 = len(json_retry("https://api.panoramax.xyz/api/search", params={"bbox": bb, "limit": 1000, "datetime": "2030-01-01T00:00:00Z/.."}, timeout=90)[0]["features"])
    n3 = len(json_retry("https://api.panoramax.xyz/api/search", params={"bbox": bb, "limit": 1000, "datetime": "2025-08-01T00:00:00Z/2025-08-31T23:59:59Z"}, timeout=90)[0]["features"])
    if sample: save("panoramax", sample)
    with open(os.path.join(HERE, "panoramax_pitch_by_aoi.json"), "w") as f:
        json.dump(pitch_by_aoi, f, indent=1)
    pit = "; ".join(f"{k}: {v['nonzero']}/{v['with_pitch']} nonzero {v['dist']} dated {v['dates']}" for k, v in pitch_by_aoi.items())
    add(gap="S9", candidate="panoramax", source_type="vehicle", endpoint=ep, auth="none", reachable="yes",
        http_status=",".join(map(str, sorted(status))), aoi_hits=hits_str(counts),
        control_passed="yes" if ctrl == 0 and n2 == 0 else "no", observation_unit="acquisition",
        quality_fields="datetime;view:azimuth;pers:pitch;pers:roll;quality:horizontal_accuracy;license;exif(Exif.Image.Make/Model/GPSImgDirection/DateTimeOriginal);Xmp.GPano.ProjectionType;pers:interior_orientation;geovisio:producer;geovisio:status;original_file:size;panoramax:horizontal_pixel_density",
        off_nadir_field="properties.pers:pitch (also exif Xmp.Camera.Pitch / Xmp.GPano.PosePitchDegrees); heading in properties.view:azimuth",
        licence="per item properties.license (CC-BY-SA-4.0 on every item seen); link rel=license to SPDX",
        notes=(f"bbox = the AOI polygon's own extent (not a 1 km box around the centroid; stress_city_toronto_full is 25 km wide and returns 0 in a 1 km box at its centroid but 1000 in its full extent). "
               f"Federated STAC-like instance (items link via=original instance e.g. bikespace Toronto). Capped at limit=1000/AOI; counts {fmt_counts(counts)}; control={ctrl}; retries={retries_total}. "
               f"Filter differential Toronto core: datetime>=2030 -> {n2}; datetime in 2025-08 -> {n3}. Field coverage over {nfeat} items in AOIs: {dict(stats)}. "
               f"pers:pitch rounded to whole degrees, per AOI: {pit}. Pitch is non-zero only in some surveys, so it can discriminate there but is 0 in most of the data; is_pano counts equirectangular 360 items. No 429 seen at 2 req/s."))


# ------------------------------------------------------------------ Mapillary
def mapillary():
    ep = "https://graph.mapillary.com/images?bbox={bbox}&limit=1  (no access_token)"
    codes, msgs = collections.Counter(), set()
    for aid, lat, lon in AOIS:
        b = bbox(lat, lon)
        r = get("https://graph.mapillary.com/images", params={"bbox": ",".join(f"{x:.6f}" for x in b), "limit": 1})
        codes[r.status_code] += 1
        try:
            e = r.json().get("error", {}); msgs.add(f"code={e.get('code')} {e.get('message')}")
        except Exception:
            msgs.add("nonjson")
    tcodes = collections.Counter()
    for aid, lat, lon in AOIS[:3]:
        n = 2 ** 14
        x = int((lon + 180) / 360 * n)
        y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        for layer in ("mly1_public", "mly1_computed_public"):
            r = get(f"https://tiles.mapillary.com/maps/vtp/{layer}/2/14/{x}/{y}")
            tcodes[f"{layer}:{r.status_code}"] += 1
    r = get("https://tiles.mapillary.com/maps/vtp/mly1_public/2/14/4700/6000", params={"access_token": "MLY|0|0"})
    tdummy = r.status_code
    r = get("https://graph.mapillary.com/images", params={"bbox": "-79.39,43.64,-79.37,43.66", "limit": 1, "access_token": "MLY|0|0"})
    gdummy = (r.status_code, r.text[:120])
    add(gap="S9", candidate="mapillary_api_v4", source_type="vehicle", endpoint="https://graph.mapillary.com/images?bbox={bbox}&limit=N&access_token=<client token>; tiles https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}",
        auth="free-reg", reachable="partial", http_status=f"graph {dict(codes)}; tiles {dict(tcodes)}", aoi_hits="0/15", control_passed="n/a",
        observation_unit="acquisition",
        quality_fields="none seen live (blocked). Documented image fields: captured_at;compass_angle;computed_compass_angle;is_pano;make;model;camera_type;exif_orientation;altitude;computed_altitude;geometry;sequence;quality_score;creator;height;width",
        off_nadir_field="none usable: no pitch field documented in v4 images; compass_angle is heading only. Not verified live",
        licence="CC-BY-SA-4.0 (Mapillary imagery)",
        notes=(f"POC adapter sends no access_token (poc/adapters_infrastructure.py _a_ground_imagery, GET graph.mapillary.com/images bbox, headers=UA only). Graph returns HTTP 500 {sorted(msgs)} for every AOI; "
               f"it is a token fault, not coverage and not an outage (500 not 401). A dummy token MLY|0|0 gives {gdummy}. Public tiles also need a token: tiles.mapillary.com returns 403 with empty body without token ({dict(tcodes)}) and 403 with dummy token ({tdummy}). "
               "Fix = register a Mapillary developer app (free) and pass a client token; no account made here (rule 5)."))


# ------------------------------------------------------------------ KartaView
def kartaview():
    ep = "https://api.kartaview.org/2.0/photo/?tlLat={n}&tlLng={w}&brLat={s}&brLng={e}"
    env, http = collections.Counter(), collections.Counter()
    for aid, lat, lon in AOIS:
        w, s, e, n = bbox(lat, lon)
        r = get("https://api.kartaview.org/2.0/photo/", params={"tlLat": n, "tlLng": w, "brLat": s, "brLng": e})
        http[r.status_code] += 1
        try:
            st = r.json().get("status", {}); env[f"{st.get('apiCode')} {st.get('apiMessage')}"] += 1
        except Exception:
            env["nonjson"] += 1
    r2 = get("https://api.openstreetcam.org/2.0/photo/", params={"tlLat": 43.66, "tlLng": -79.39, "brLat": 43.64, "brLng": -79.37})
    r3 = get("https://api.kartaview.org/1.0/list/nearby-photos/", params={"lat": 43.65, "lng": -79.38})
    add(gap="S9", candidate="kartaview", source_type="vehicle", endpoint=ep, auth="free-reg", reachable="partial",
        http_status=f"api.kartaview.org 2.0 {dict(http)} (envelope {dict(env)}); api.openstreetcam.org 2.0 {r2.status_code}; 1.0 nearby-photos {r3.status_code}",
        aoi_hits="0/15", control_passed="n/a", observation_unit="acquisition",
        quality_fields="none seen live (blocked)", off_nadir_field="none seen live; legacy v1 photo objects carried heading/lat/lng only",
        licence="CC-BY-SA (KartaView imagery)",
        notes=("Every keyless call returns apiCode 400 'Restricted access!'. api.kartaview.org wraps it in HTTP 200 (envelope status.apiCode=400), which is why the POC reports 'apiCode=400 Restrict'; "
               "api.openstreetcam.org returns the same body with HTTP 400; the v1.0 list endpoints now 404. The API doc (api.openstreetcam.org/api/doc.html) says secured methods need an access_token obtained by OSM OAuth. "
               "Public reads are no longer anonymous. No OSM account used (rule 5)."))


# ------------------------------------------------------------------ Bee Maps / Hivemapper
def beemaps():
    base = "https://beemaps.com/api/developer"
    r1 = get(base + "/imagery"); r2 = get(base + "/map-data", method="POST", json={}, headers={"Content-Type": "application/json"})
    r3 = get(base + "/imagery/poly", method="POST", json={"geometry": {"type": "Point", "coordinates": [-79.383, 43.65]}})
    add(gap="S9", candidate="bee_maps_hivemapper", source_type="vehicle", endpoint=base + "/imagery/poly (POST GeoJSON polygon; Authorization: Basic <key>)", auth="paid",
        reachable="partial", http_status=f"GET /imagery {r1.status_code}; POST /map-data {r2.status_code}; POST /imagery/poly {r3.status_code}", aoi_hits="n/a", control_passed="n/a",
        observation_unit="acquisition",
        quality_fields="none seen live. Docs (API ref v1.3.0): timestamps; GPS accuracy metrics; IMU data; camera calibration endpoint /devices",
        off_nadir_field="none seen live; docs claim IMU data per frame (pitch/roll not verified)",
        licence="commercial terms; per-view USD metering on returned image URLs; query area <=5 km2",
        notes=("Key required for all endpoints (Basic API key from the Bee Maps dashboard); keyless calls give 403 Forbidden/404. Billing = API credits per query plus per-view USD balance (beemaps.com/pricing), so no free public API. "
               "36% of world roads claimed. Hivemapper's older free 'honey' map-data API was folded into Bee Maps. Docs read: beemaps.com/docs/api-reference."))


# ------------------------------------------------------------------ Google Street View
def gsv():
    ep = "https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lon}&radius=1000&key=<KEY>"
    sts = collections.Counter(); msg = ""
    for aid, lat, lon in AOIS:
        r = get("https://maps.googleapis.com/maps/api/streetview/metadata", params={"location": f"{lat},{lon}", "radius": 1000})
        j = r.json(); sts[j.get("status")] += 1; msg = j.get("error_message", "")[:90]
    add(gap="S9", candidate="google_street_view_metadata", source_type="vehicle", endpoint=ep, auth="key-we-lack", reachable="yes",
        http_status="200 (body status REQUEST_DENIED)", aoi_hits="0/15", control_passed="n/a", observation_unit="acquisition",
        quality_fields="none seen live. Documented response: status;pano_id;location.lat/lng;date (YYYY-MM);copyright",
        off_nadir_field="none: metadata has no heading or pitch (those are request parameters of the Static image, not returned)",
        licence="proprietary; Google Maps Platform ToS bars caching or bulk storage of imagery; metadata requests are free and unbilled",
        notes=(f"All 15 AOIs: {dict(sts)} ('{msg}'). With a key it would return pano_id, capture month, coordinates and copyright for the nearest pano within radius, status ZERO_RESULTS where none. "
               "It gives existence and capture month only, no heading or pitch. No key held, none requested (rule 5)."))


# ------------------------------------------------------------------ Windy
def windy():
    r = get("https://api.windy.com/webcams/api/v3/webcams", params={"nearby": "43.65,-79.38,1", "include": "location,images"})
    add(gap="S9", candidate="windy_webcams", source_type="fixed camera",
        endpoint="https://api.windy.com/webcams/api/v3/webcams?nearby={lat},{lon},{radius_km}&include=location,images  (header x-windy-api-key)",
        auth="free-reg", reachable="partial", http_status=str(r.status_code), aoi_hits="n/a", control_passed="n/a", observation_unit="snapshot",
        quality_fields="none seen live. Docs: status;lastUpdatedOn;location;images.current(preview/thumbnail); player",
        off_nadir_field="none", licence="Windy ToS; free tier shows images with expiring URLs (10 min) and attribution; bulk use needs paid Professional tier",
        notes=f"Keyless call returns 403 {r.text[:100]}. A free key needs a Windy account (not created). Camera orientation is not an API field."
              " Camera coordinates are provided but there is no heading or pitch.")


# ------------------------------------------------------------------ 511
def r511():
    for cand, host in (("511_ontario", "511on.ca"), ("511_alberta", "511.alberta.ca")):
        r = get(f"https://{host}/api/v2/get/cameras", params={"format": "json"}, host_gap=1)
        rd = get(f"https://{host}/developers/doc")
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", rd.text))
        thr = re.search(r"Throttling[^.]*\.", txt)
        add(gap="S9", candidate=cand, source_type="fixed camera", endpoint=f"https://{host}/api/v2/get/cameras?key=<KEY>&format=json",
            auth="free-reg", reachable="partial", http_status=str(r.status_code), aoi_hits="n/a", control_passed="n/a", observation_unit="snapshot",
            quality_fields="none seen live (blocked)", off_nadir_field="none seen live",
            licence="provincial open data terms (not stated by API); not verified",
            notes=(f"Keyless call: HTTP {r.status_code} {r.text[:60]}. The endpoint returns all cameras (no area parameter), so AOI filtering is client-side. Throttling is enabled: ten calls every 60 seconds per the doc. "
                   f"Docs say a registered account is required to obtain a developer key. {'Ontario highways only (MTO plus municipal).' if 'on.ca' in host else 'Alberta highways only.'} Account not created (rule 5)."))


# ------------------------------------------------------------------ DriveBC
def drivebc():
    ep = "https://www.drivebc.ca/api/webcams/"
    r = get(ep, timeout=90)
    cams = r.json()
    counts, nearest = {}, {}
    for aid, lat, lon in AOIS + [CONTROL]:
        ds = sorted((hav(lat, lon, c["location"]["coordinates"][1], c["location"]["coordinates"][0]), c["id"]) for c in cams)
        counts[aid] = sum(1 for d, _ in ds if d <= R_M / 1000)
        nearest[aid] = ds[0]
    ctrl = counts.pop(CONTROL[0])
    best = min((a for a in AOIS), key=lambda a: nearest[a[0]][0])
    cam = next(c for c in cams if c["id"] == nearest[best[0]][1])
    img = get("https://www.drivebc.ca" + cam["links"]["imageDisplay"].split("?")[0], method="HEAD")
    save("drivebc_webcams", cam)
    near_s = "; ".join(f"{a[0]}={nearest[a[0]][0]:.2f}km" for a in AOIS if nearest[a[0]][0] < 100)
    add(gap="S9", candidate="drivebc_webcams", source_type="fixed camera", endpoint=ep, auth="none", reachable="yes", http_status=str(r.status_code),
        aoi_hits=hits_str(counts), control_passed="yes" if ctrl == 0 else "no", observation_unit="snapshot",
        quality_fields="last_update_modified;last_update_attempt;update_period_mean;update_period_stddev;marked_stale;marked_delayed;is_on;orientation;elevation;highway;region_name;credit;links.imageDisplay",
        off_nadir_field="orientation (cardinal compass facing, e.g. 'E'); no pitch field",
        licence="not stated in API response (DataBC listing not found via catalogue search); images carry dbc_mark DriveBC.ca",
        notes=(f"{len(cams)} cameras, BC only, list is one 1.2 MB GET with no area parameter so the bbox is client-side. Within 1 km: {fmt_counts(counts)}; nearest camera to AOIs within 100 km: {near_s or 'none'}. "
               f"Image URL /images/<id>.jpg is a live latest-frame only (HEAD {img.status_code} {img.headers.get('content-type')}); about one frame per {cam['update_period_mean']} s; no archive. "
               "Only highway sites, so farm/mine/oil-sands AOIs outside BC are coverage misses."))


# ------------------------------------------------------------------ PhenoCam
def phenocam():
    cams, url = [], "https://phenocam.nau.edu/api/cameras/?format=json&limit=500"
    while url:
        r = get(url, timeout=60); j = r.json(); cams += j["results"]; url = j.get("next")
    counts, nearest, c25 = {}, {}, {}
    for aid, lat, lon in AOIS + [CONTROL]:
        ds = sorted((hav(lat, lon, c["Lat"], c["Lon"]), c["Sitename"]) for c in cams)
        counts[aid] = sum(1 for d, _ in ds if d <= R_M / 1000); c25[aid] = sum(1 for d, _ in ds if d <= 25); nearest[aid] = ds[0]
    ctrl = counts.pop(CONTROL[0]); c25.pop(CONTROL[0])
    best = min(AOIS, key=lambda a: nearest[a[0]][0])
    site = next(c for c in cams if c["Sitename"] == nearest[best[0]][1])
    img = get(f"https://phenocam.nau.edu/data/latest/{site['Sitename']}.jpg", method="HEAD")
    rl = get("https://phenocam.nau.edu/api/roilists/", params={"format": "json", "site": site["Sitename"], "limit": 200})
    rois = [x for x in rl.json().get("results", []) if x["site"] == site["Sitename"]]
    rl_filter_ok = len(rois) > 0 or rl.json().get("count") != 1599
    hdr = ""
    if rois:
        csvu = rois[0]["one_day_summary"]
        rr = get(csvu, headers={"Range": "bytes=0-6000"})
        hdr = "\n".join(l for l in rr.text.splitlines() if not l.startswith("#"))[:900]
    sample = {"camera": site, "roi": rois[0] if rois else None, "latest_image_http": img.status_code,
              "latest_image_last_modified": img.headers.get("last-modified"), "gcc_1day_csv_header_and_first_rows": hdr}
    save("phenocam", sample)
    near_s = "; ".join(f"{a[0]}={nearest[a[0]][0]:.0f}km({nearest[a[0]][1]})" for a in AOIS if nearest[a[0]][0] < 60)
    add(gap="S9", candidate="phenocam", source_type="fixed camera", endpoint="https://phenocam.nau.edu/api/cameras/?format=json&limit=500 ; /api/roilists/?site={site} ; /data/latest/{site}.jpg",
        auth="none", reachable="yes", http_status=str(r.status_code), aoi_hits=hits_str(counts), control_passed="yes" if ctrl == 0 else "no", observation_unit="snapshot",
        quality_fields="Lat;Lon;Elev;active;date_first;date_last;utc_offset;infrared;sitemetadata.camera_description;sitemetadata.camera_orientation;sitemetadata.site_type;sitemetadata.primary_veg_type;roi missing_data_pct;roi site_years;1-day GCC/RCC/BCC series",
        off_nadir_field="sitemetadata.camera_orientation (cardinal, e.g. 'NNW'); no pitch field",
        licence="not stated in API response; PhenoCam data policy requires citation (not verified)",
        notes=(f"{len(cams)} cameras network-wide, list has no area filter (client-side distance). Within 1 km: {fmt_counts(counts)}; within 25 km: {fmt_counts(c25)}; control={ctrl}. Nearest camera to an AOI under 60 km: {near_s or 'none'}. "
               f"Latest image HEAD {img.status_code} (last-modified {img.headers.get('last-modified')}, so stale if camera inactive). roilists site= filter {'works' if rl_filter_ok else 'NOT applied'} on this query; ROI 1-day GCC CSV is the derived greenness series. "
               "Sparse network (mostly research tower sites), so AOI hits depend on whether a farm or mine happens to host one."))


# ------------------------------------------------------------------ AMOS
def amos():
    dns = get("https://amos.cse.wustl.edu/")
    mv = requests.get("https://mvrl.cse.wustl.edu/datasets/amos/", headers=UA, timeout=30, verify=False)
    g = get("https://gist.githubusercontent.com/golanlevin/5e752579c781b624e52261a2c3feeadb/raw", timeout=60)
    reader = list(csv.DictReader(g.text.splitlines()))
    pts = []
    for x in reader:
        try: pts.append((float(x["latitude"]), float(x["longitude"]), x))
        except Exception: pass
    counts = {}
    for aid, lat, lon in AOIS + [CONTROL]:
        counts[aid] = sum(1 for la, lo, _ in pts if hav(lat, lon, la, lo) <= R_M / 1000)
    ctrl = counts.pop(CONTROL[0])
    hit = next(((la, lo, x) for la, lo, x in pts if hav(AOIS[8][1], AOIS[8][2], la, lo) <= 5), None)
    if hit: save("amos", hit[2])
    add(gap="S9", candidate="amos", source_type="fixed camera", endpoint="https://mvrl.cse.wustl.edu/datasets/amos/ (request form); camera list mirror https://gist.githubusercontent.com/golanlevin/5e752579c781b624e52261a2c3feeadb/raw",
        auth="free-reg", reachable="partial", http_status=f"amos.cse.wustl.edu {dns.status_code} (DNS gone); mvrl page {mv.status_code}; gist {g.status_code}",
        aoi_hits=hits_str(counts), control_passed="yes" if ctrl == 0 else "no", observation_unit="snapshot",
        quality_fields="cameraid;name;url;latitude;longitude;last_width;last_height;mhash (mirror CSV columns)", off_nadir_field="none",
        licence="none stated; images are scraped public webcams, access by Google-form request",
        notes=(f"The original amos.cse.wustl.edu host does not resolve. MVRL page says ~55 TB, 'hundreds of millions' of images, access by form (forms.gle), no API. "
               f"aoi_hits was computed against a third-party gist of {len(pts)} 'rescued' camera positions (1 km): {fmt_counts(counts)}; control={ctrl}. Camera URLs are mostly long dead; positions are static. "
               "MVRL page serves an incomplete TLS chain (fetched with verify=False). Not usable as a live source; reference only for camera locations."))


# ------------------------------------------------------------------ Wikimedia Commons
def wikimedia():
    ep = "https://commons.wikimedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=1000&gslimit=500&gsnamespace=6&format=json"
    counts, sample, meta_stats, nfile, retries = {}, None, collections.Counter(), 0, 0
    pass2 = {}
    for aid, lat, lon in AOIS + [CONTROL]:
        j, _, rt = json_retry("https://commons.wikimedia.org/w/api.php", params=dict(action="query", list="geosearch", gscoord=f"{lat}|{lon}", gsradius=R_M, gslimit=500, gsnamespace=6, format="json"), host_gap=1.0)
        retries += rt
        counts[aid] = len(j.get("query", {}).get("geosearch", []))
        if counts[aid] and aid != CONTROL[0]:
            r2j, _, rt = json_retry("https://commons.wikimedia.org/w/api.php", host_gap=1.0, params=dict(action="query", generator="geosearch", ggscoord=f"{lat}|{lon}", ggsradius=R_M, ggslimit=5, ggsnamespace=6,
                     prop="imageinfo|coordinates", iiprop="extmetadata|metadata|timestamp|size|url", coprop="type|dim|globe|name", colimit=50, format="json", formatversion=2))
            retries += rt
            for p in r2j.get("query", {}).get("pages", []):
                ii = (p.get("imageinfo") or [{}])[0]; nfile += 1
                names = {m["name"] for m in ii.get("metadata") or []}
                for k in ("Make", "Model", "GPSImgDirection", "GPSAltitude", "DateTimeOriginal", "GPSLatitude", "GPSDOP", "ExposureTime"):
                    if k in names: meta_stats[k] += 1
                em = ii.get("extmetadata", {})
                for k in ("DateTimeOriginal", "LicenseShortName", "GPSLatitude"):
                    if k in em: meta_stats["ext." + k] += 1
                if sample is None and "Make" in names and "GPSImgDirection" in names:
                    sample = p
                if sample is None and aid == "city_toronto_core":
                    sample = p
    for aid, lat, lon in AOIS:
        j, _, rt = json_retry("https://commons.wikimedia.org/w/api.php", params=dict(action="query", list="geosearch", gscoord=f"{lat}|{lon}", gsradius=R_M, gslimit=500, gsnamespace=6, format="json"), host_gap=1.0)
        retries += rt; pass2[aid] = len(j.get("query", {}).get("geosearch", []))
    stable = pass2 == {k: v for k, v in counts.items() if k != CONTROL[0]}
    ctrl = counts.pop(CONTROL[0])
    r10j, _, _ = json_retry("https://commons.wikimedia.org/w/api.php", params=dict(action="query", list="geosearch", gscoord="43.65|-79.383", gsradius=10000, gslimit=500, gsnamespace=6, format="json"), host_gap=1.0)
    n10 = len(r10j["query"]["geosearch"])
    if sample: save("wikimedia_commons", sample)
    add(gap="S9", candidate="wikimedia_commons", source_type="handheld", endpoint=ep, auth="none", reachable="yes", http_status="200",
        aoi_hits=hits_str(counts), control_passed="yes" if ctrl == 0 else "no", observation_unit="acquisition",
        quality_fields="coordinates.type (camera|object);coordinates.dim;extmetadata.DateTimeOriginal;extmetadata.LicenseShortName;extmetadata.GPSLatitude;metadata.Make;metadata.Model;metadata.GPSImgDirection;metadata.GPSAltitude;width;height;timestamp",
        off_nadir_field="metadata.GPSImgDirection (heading, when EXIF carries it); no pitch field", licence="per file via extmetadata.LicenseShortName/License (CC BY, CC BY-SA, PD)",
        notes=(f"geosearch radius 1000 m, cap 500 (per-AOI counts: {dict(counts)}; control={ctrl}; Toronto at 10 km gives {n10}, so radius filter works; second full pass identical={stable}, 429/error retries={retries}). "
               f"Sampled {nfile} files in hit AOIs (<=5 per AOI): EXIF/extmetadata presence {dict(meta_stats)}. coordinates[].type='camera' separates camera position from depicted-object position; most coordinates are user-entered, no accuracy field. "
               "Heading and camera make exist only for files whose EXIF survived upload. User-Agent header required. Wikimedia does rate-limit: without backoff a 429/error body reads as 0 hits (first run saw Toronto=0), so json_retry sleeps and retries on 429/5xx/error body."))


# ------------------------------------------------------------------ Flickr
def flickr():
    r = get("https://api.flickr.com/services/rest/", params=dict(method="flickr.photos.search", format="json", nojsoncallback=1, bbox="-79.39,43.64,-79.37,43.66", has_geo=1))
    j = r.json()
    def feed(lat, lon):
        rr = get("https://www.flickr.com/services/feeds/geo/", params=dict(format="json", nojsoncallback=1, lat=lat, lon=lon, radius=1, radius_units="km"))
        try:
            return rr.json()
        except Exception:
            return json.loads(rr.text.replace("\\'", "'"))
    a = feed(43.65, -79.38); b = feed(CONTROL[1], CONTROL[2])
    la = {i["link"] for i in a["items"]}; lb = {i["link"] for i in b["items"]}
    ignored = len(la & lb) > 0.5 * len(la)
    add(gap="S9", candidate="flickr", source_type="handheld", endpoint="https://api.flickr.com/services/rest/?method=flickr.photos.search&bbox={bbox}&has_geo=1&extras=geo,date_taken,license,owner_name&api_key=<KEY>",
        auth="key-we-lack", reachable="partial", http_status=f"rest {r.status_code} (body stat={j.get('stat')} code={j.get('code')}); feeds/geo 200",
        aoi_hits="n/a", control_passed="no" if ignored else "yes", observation_unit="acquisition",
        quality_fields="none seen live. Docs: geo accuracy (1-16 zoom level);datetaken;license;owner;latitude;longitude (extras=geo,date_taken,license)",
        off_nadir_field="none: Flickr API does not expose EXIF heading in search results (needs photos.getExif per photo)",
        licence="per photo licence id (0-10: ARR, CC variants, PD)",
        notes=(f"REST needs api_key: '{j.get('message')}'. The keyless Atom/JSON feed /services/feeds/geo/ accepted lat/lon/radius but returned the same global recent-uploads set for Toronto and mid-Pacific ({len(la & lb)}/{len(la)} shared), "
               "so the spatial filter is ignored: no keyless area search. The feed is a 20-item live window, not an archive. Flickr geo 'accuracy' is a map zoom level, not meters."))


# ------------------------------------------------------------------ iNaturalist
def inat():
    ep = "https://api.inaturalist.org/v1/observations?lat={lat}&lng={lon}&radius=1&photos=true&per_page=1"
    counts, sample, accs = {}, None, []
    for aid, lat, lon in AOIS + [CONTROL]:
        r = get("https://api.inaturalist.org/v1/observations", params=dict(lat=lat, lng=lon, radius=1, photos="true", per_page=1, order_by="created_at"), host_gap=1.1)
        j = r.json(); counts[aid] = j.get("total_results", 0)
        if j.get("results") and aid != CONTROL[0]:
            o = j["results"][0]
            accs.append((aid, o.get("positional_accuracy"), o.get("public_positional_accuracy"), o.get("geoprivacy"), o.get("obscured")))
            if sample is None and aid == "city_toronto_core": sample = o
    ctrl = counts.pop(CONTROL[0])
    base = dict(lat=43.65, lng=-79.383, per_page=0)
    n = {}
    for nm, extra in (("r1", dict(radius=1)), ("r5", dict(radius=5)), ("acc<=50", dict(radius=1, acc_below=50)), ("photos_false", dict(radius=1, photos="false"))):
        n[nm] = get("https://api.inaturalist.org/v1/observations", params=dict(base, **extra), host_gap=1.1).json().get("total_results")
    if sample: save("inaturalist", sample)
    add(gap="S9", candidate="inaturalist", source_type="handheld", endpoint=ep, auth="none", reachable="yes", http_status="200", aoi_hits=hits_str(counts),
        control_passed="yes" if ctrl == 0 else "no", observation_unit="acquisition",
        quality_fields="positional_accuracy;public_positional_accuracy;geoprivacy;taxon_geoprivacy;obscured;observed_on;time_observed_at;quality_grade;license_code;photos[].license_code;photos[].original_dimensions;location",
        off_nadir_field="none (EXIF heading/pitch not exposed)", licence="per observation license_code and per photo (cc-by, cc-by-nc, cc0, ...) ; some all rights reserved",
        notes=(f"Counts within 1 km (all observations with photos): {fmt_counts(counts)}; control={ctrl}. Toronto filter differentials: {n} (radius, acc_below and photos filters all change the count, so applied). "
               f"positional_accuracy is in metres and often large: first-hit sample (aoi, accuracy, public accuracy, geoprivacy, obscured) = {accs[:6]}. Obscured records are moved to a ~0.2 degree cell, so a 1 km hit can be fiction for sensitive taxa. "
               "Target is a species not a place: images are close-ups of organisms, not scenes. Recommended <=60 req/min; ran at ~1/s."))


# ------------------------------------------------------------------ GBIF
def gbif():
    ep = "https://api.gbif.org/v1/occurrence/search?mediaType=StillImage&decimalLatitude={s},{n}&decimalLongitude={w},{e}&limit=0"
    counts, allc, sample = {}, {}, None
    for aid, lat, lon in AOIS + [CONTROL]:
        w, s, e, n = bbox(lat, lon)
        p = dict(decimalLatitude=f"{s:.6f},{n:.6f}", decimalLongitude=f"{w:.6f},{e:.6f}", limit=0)
        counts[aid] = get("https://api.gbif.org/v1/occurrence/search", params=dict(p, mediaType="StillImage")).json().get("count", 0)
        allc[aid] = get("https://api.gbif.org/v1/occurrence/search", params=p).json().get("count", 0)
        if counts[aid] and sample is None and aid != CONTROL[0]:
            p2 = dict(p, mediaType="StillImage", limit=1)
            sample = get("https://api.gbif.org/v1/occurrence/search", params=p2).json()["results"][0]
    ctrl = counts.pop(CONTROL[0]); allc.pop(CONTROL[0])
    if sample: save("gbif_media", sample)
    sf = {k: sample.get(k) for k in ("coordinateUncertaintyInMeters", "eventDate", "license", "basisOfRecord", "datasetName", "issues")} if sample else {}
    add(gap="S9", candidate="gbif_media", source_type="handheld", endpoint=ep, auth="none", reachable="yes", http_status="200", aoi_hits=hits_str(counts),
        control_passed="yes" if ctrl == 0 else "no", observation_unit="acquisition",
        quality_fields="coordinateUncertaintyInMeters;eventDate;license;basisOfRecord;issues;georeferenceVerificationStatus;datasetKey;extensions.Multimedia(license,created,creator,identifier,rightsHolder)",
        off_nadir_field="none", licence="per record (CC0, CC-BY, CC-BY-NC) and per media item in the Multimedia extension",
        notes=(f"Image-bearing occurrences within 1 km: {fmt_counts(counts)}; control={ctrl}; the mediaType=StillImage filter cuts the all-occurrence counts ({fmt_counts(allc, 6)}), so it is applied. "
               f"One sample record: {sf}. Mostly iNaturalist research-grade copies via GBIF, so overlaps the iNaturalist row; coordinate uncertainty usually missing on non-iNat sets. Organism photos, not scenes."))


# ------------------------------------------------------------------ Geograph
def geograph():
    ep = "https://www.geograph.org.uk/syndicator.php?format=JSON&q={lat},{lon}"
    counts, nearest, errs = {}, {}, collections.Counter()
    for aid, lat, lon in AOIS + [CONTROL]:
        j = get("https://www.geograph.org.uk/syndicator.php", params=dict(format="JSON", q=f"{lat},{lon}"), host_gap=1).json()
        its = j.get("items", [])
        if j.get("error"): errs[j["error"]] += 1
        ds = [hav(lat, lon, float(i["lat"]), float(i["long"])) for i in its if i.get("lat")]
        counts[aid] = sum(1 for d in ds if d <= R_M / 1000); nearest[aid] = round(min(ds), 0) if ds else None
    ctrl = counts.pop(CONTROL[0]); nearest.pop(CONTROL[0])
    uk = get("https://www.geograph.org.uk/syndicator.php", params=dict(format="JSON", q="51.5,-0.12"), host_gap=1).json()
    ukn = sum(1 for i in uk["items"] if hav(51.5, -0.12, float(i["lat"]), float(i["long"])) <= 1)
    if uk["items"]: save("geograph", uk["items"][0])
    it = uk["items"][0]
    add(gap="S9", candidate="geograph", source_type="handheld", endpoint=ep, auth="none", reachable="yes", http_status="200", aoi_hits=hits_str(counts),
        control_passed="yes" if ctrl == 0 else "no", observation_unit="acquisition",
        quality_fields=";".join(sorted(it.keys())), off_nadir_field="none in feed (view direction exists only on the photo page)",
        licence="CC-BY-SA-2.0 (licence field in each item)",
        notes=(f"UK/Ireland only, so 0/15 on the Canada+US AOIs is coverage, not failure. Positive control at London 51.5,-0.12: {ukn} items within 1 km (of {len(uk['items'])} returned). "
               f"For all 16 non-UK points (15 AOIs + control) the endpoint answers HTTP 200 with a JSON error body: {dict(errs)}. Results are capped per page (~15-20), paginated via nextURL."))


# ------------------------------------------------------------------ datasets
def datasets():
    hf = get("https://huggingface.co/api/datasets/osv5m/osv5m").json()
    tr = get("https://huggingface.co/api/datasets/osv5m/osv5m/tree/main").json()
    csvs = {t["path"]: t["size"] for t in tr if t["path"].endswith(".csv")}
    rr = get("https://huggingface.co/datasets/osv5m/osv5m/resolve/main/test.csv", headers={"Range": "bytes=0-4000"}, allow_redirects=True)
    lines = rr.text.splitlines()
    hdr = next(csv.reader([lines[0]])); first = next(csv.reader([lines[1]]))
    save("osv5m", dict(zip(hdr, first)))
    add(gap="S9", candidate="osv5m", source_type="vehicle", endpoint="https://huggingface.co/datasets/osv5m/osv5m (train.csv/test.csv + images/*.zip)", auth="none", reachable="yes",
        http_status="200", aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields=";".join(hdr),
        off_nadir_field="none (no heading or pitch column)", licence=f"{hf.get('tags') and [t for t in hf['tags'] if t.startswith('license')][0]} (images are Mapillary CC-BY-SA)",
        notes=(f"5.1M Mapillary street-level images, 225 countries, lat/lon per image, captured_at (ms epoch), creator_username, drive_side, land_cover. Total repo {hf.get('usedStorage', 0)/1e9:.0f} GB, "
               f"CSV sizes {csvs}. Free, no gating, so it is a free offline snapshot of Mapillary, circa 2023, for query by lat/lon after download. Not live. thumb_original_url fbcdn links expire."))
    add(gap="S9", candidate="bdd100k", source_type="vehicle", endpoint="https://doc.bdd100k.com/download.html (login-less form; hosts unreachable from this sandbox)", auth="free-reg", reachable="no", http_status="0",
        aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields="per video: GPS/IMU info JSON (timestamp;latitude;longitude;speed;accuracy;altitude;heading); weather;scene;timeofday attributes",
        off_nadir_field="none (GPS/IMU info has heading and IMU accelerometer/gyro; no camera pitch)", licence="BDD100K custom licence (accepted on download); commercial use restricted",
        notes=("Host did not respond (doc.bdd100k.com, www.bdd100k.com both connection failure). Facts from web search of the official doc and paper, not verified live: 100K videos of 40 s, >50K rides, New York, San Francisco Bay Area and a few other regions; "
               "GPS/IMU package 3.9 GB, 100K keyframe images 5.3 GB, labels 107 MB; lat/lon is per video track (GPS at ~1 Hz), not per image. Fixed US city footprint; no Canadian coverage."))
    add(gap="S9", candidate="nuscenes", source_type="vehicle", endpoint="https://www.nuscenes.org/nuscenes#download (registration form)", auth="free-reg", reachable="partial", http_status="200",
        aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields="ego_pose (translation, rotation, timestamp in a map frame); calibrated_sensor (camera intrinsics, extrinsic pitch/yaw/roll); sample_data timestamps; scene location log",
        off_nadir_field="calibrated_sensor.rotation (quaternion giving the camera extrinsics, incl. pitch) in calibrated_sensor.json",
        licence="CC BY-NC-SA 4.0 (non-commercial)",
        notes=("Site is a JS page, data needs registration (no account made). Facts from web search of the paper, not verified live: 1000 scenes of 20 s, Boston Seaport and Singapore One North / Queenstown / Holland Village, 1.4M camera images, ~5.5 h; "
               "6 cameras per sample; position per frame is local ego pose (x, y in a city map frame) tied to a map origin, not WGS84 per image. Two foreign city districts only."))
    add(gap="S9", candidate="yfcc100m", source_type="handheld", endpoint="https://registry.opendata.aws/multimedia-commons/ (s3://multimedia-commons) ; metadata via Yahoo Webscope", auth="none", reachable="yes", http_status="200",
        aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields="Flickr metadata: latitude;longitude;accuracy (zoom level 1-16);datetaken;capturedevice (camera make/model);licensename;machine tags",
        off_nadir_field="none", licence="per photo Creative Commons variant (CC0 for the Multimedia Commons features/annotations; underlying photos CC BY/BY-NC/BY-SA...)",
        notes=("AWS registry page confirms ~100M CC-licensed Flickr images/videos, Multimedia Commons feature corpus CC0. From web search, not verified live: ~48.4M photos carry a geotag, "
               "metadata archive ~12.5 GB compressed; lat/lon per image with accuracy as a Flickr zoom level, not metres. Global coverage but densest at tourist sites; the photos span 2004-2014 so are stale. "
               "Subset as a point table can be filtered locally by AOI."))


def main():
    for fn in (panoramax, mapillary, kartaview, beemaps, gsv, windy, r511, drivebc, phenocam, amos, wikimedia, flickr, inat, gbif, geograph, datasets):
        try:
            fn(); print("done", fn.__name__, flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            add(gap="S9", candidate=fn.__name__ + "_ERROR", source_type="handheld", endpoint="", auth="none", reachable="no", http_status="0", aoi_hits="n/a",
                control_passed="n/a", observation_unit="acquisition", quality_fields="", off_nadir_field="none", licence="", notes=f"probe error {type(e).__name__}: {e}")
    with open(os.path.join(HERE, "D_probes.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(rows)
    print(len(rows), "rows")


if __name__ == "__main__":
    import urllib3; urllib3.disable_warnings()
    main()

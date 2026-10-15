"""LANE CAM proof-of-concept reads: ground-level camera and photo sources over the 15 test AOIs.

Run with the geoquery env python. Writes poc_values.csv and poc_status.csv next to this file.
Usage: poc.py [source ...]   (default: all)
"""
import csv, datetime as dt, json, math, os, statistics, sys, time
import requests
from shapely.geometry import shape, Point, box
from shapely.ops import transform
import pyproj

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
AOIS = json.load(open(os.path.join(ROOT, "examples", "test_aois.geojson")))["features"]
UA = {"User-Agent": "geospatial-query-poc/0.1 (research; phyberosis@gmail.com)"}
TODAY = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
COLS = "aoi_id,source,feature,value,unit,time,time_accuracy,description,source_url,licence,endpoint".split(",")
VALUES, STATUS, NOTES = [], [], {}


def get(url, params=None, tries=8, gap=0.5, timeout=90, **kw):
    """GET with backoff on 429 and 5xx; returns the response or None when every try failed."""
    wait = 2.0
    for _ in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout, **kw)
        except requests.RequestException:
            time.sleep(wait); wait = min(wait * 2, 60); continue
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("Retry-After")
            time.sleep(float(ra) if ra and ra.isdigit() else wait); wait = min(wait * 2, 60); continue
        time.sleep(gap)
        return r
    return None


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_t(s):
    s = s.replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def duration(seconds):
    seconds = int(round(seconds))
    d, rem = divmod(seconds, 86400); h, rem = divmod(rem, 3600); m, s = divmod(rem, 60)
    out = "P" + (f"{d}D" if d else "")
    if h or m or s or not d:
        out += "T" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{s}S" if s or not (h or m) else "")
    return out


def span(times):
    """Midpoint and half-span duration of a list of datetimes."""
    lo, hi = min(times), max(times)
    return iso(lo + (hi - lo) / 2), duration((hi - lo).total_seconds() / 2 or 1)


def circ_mean(deg):
    x = sum(math.cos(math.radians(d)) for d in deg); y = sum(math.sin(math.radians(d)) for d in deg)
    return (math.degrees(math.atan2(y, x)) % 360), math.hypot(x, y) / len(deg)


def row(aoi, source, feature, value, unit, t, acc, desc, url, lic, endpoint):
    VALUES.append(dict(aoi_id=aoi, source=source, feature=feature, value=value, unit=unit, time=t, time_accuracy=acc,
                       description=desc, source_url=url, licence=lic, endpoint=endpoint))


def status(source, feature, reason, aois_with_value=None):
    n = len({v["aoi_id"] for v in VALUES if v["source"] == source and v["feature"] == feature})
    STATUS.append(dict(source=source, feature=feature, status="validated" if n else "dropped",
                       n_aois_with_value=n, reason=reason))


def aoi_geoms():
    for f in AOIS:
        g = shape(f["geometry"])
        yield f["properties"]["aoi_id"], g, g.bounds


def dist_km(g, lon, lat):
    """Distance from an AOI polygon to a point, metres/1000, in a local azimuthal equidistant frame."""
    c = g.centroid
    prj = pyproj.Transformer.from_crs("EPSG:4326", f"+proj=aeqd +lat_0={c.y} +lon_0={c.x} +ellps=WGS84", always_xy=True).transform
    return transform(prj, g).distance(transform(prj, Point(lon, lat))) / 1000


# ---------------------------------------------------------------- panoramax
PX = "https://api.panoramax.xyz/api/search"


def px_items(b, depth=0, seen=None):
    """All STAC items in a bbox; splits into quadrants whenever a page comes back full."""
    r = get(PX, {"bbox": ",".join(f"{x:.6f}" for x in b), "limit": 1000}, timeout=120)
    if r is None or r.status_code != 200:
        raise RuntimeError(f"panoramax {None if r is None else r.status_code} for {b}")
    feats = r.json()["features"]
    if len(feats) < 1000 or depth >= 7:
        return feats
    w, s, e, n = b; mx, my = (w + e) / 2, (s + n) / 2
    out = []
    for q in ((w, s, mx, my), (mx, s, e, my), (w, my, mx, n), (mx, my, e, n)):
        out += px_items(q, depth + 1)
    return out


def panoramax():
    src = "panoramax"; url = "https://api.panoramax.xyz/api/search"; lic = "CC-BY-SA-4.0"
    ep = PX + "?bbox={w},{s},{e},{n}&limit=1000 (quadrant split on a full page)"
    ok = set()
    for aid, g, b in aoi_geoms():
        try:
            items = px_items(b)
        except RuntimeError as ex:
            NOTES.setdefault("panoramax_err", []).append(str(ex)); continue
        uniq = {f["id"]: f for f in items}
        feats = [f for f in uniq.values() if box(*b).intersects(Point(f["geometry"]["coordinates"]))]
        n = len(feats)
        row(aid, src, "panoramax_image_n", n, "count", TODAY, "", "Panoramax images with capture position inside the AOI extent (snapshot)", url, lic, ep)
        ts = [parse_t(f["properties"]["datetime"]) for f in feats if f["properties"].get("datetime")]
        if not ts:
            continue
        tm, acc = span(ts)
        def vals(k):
            return [f["properties"][k] for f in feats if f["properties"].get(k) is not None]
        p = vals("pers:pitch")
        if p:
            row(aid, src, "panoramax_camera_pitch_deg", round(statistics.median(p), 2), "deg", tm, acc,
                f"Median pers:pitch over {len(p)} of {n} images (0 = level; capture times span the midpoint +/- accuracy)", url, lic, ep)
        h = vals("view:azimuth")
        if h:
            m, R = circ_mean(h)
            row(aid, src, "panoramax_camera_heading_deg", round(m, 1), "deg", tm, acc,
                f"Circular mean of view:azimuth over {len(h)} of {n} images, resultant length {R:.2f} (low = headings spread in all directions)", url, lic, ep)
        a = vals("quality:horizontal_accuracy")
        if a:
            row(aid, src, "panoramax_gps_accuracy_m", round(statistics.median(a), 2), "m", tm, acc,
                f"Median quality:horizontal_accuracy over {len(a)} of {n} images", url, lic, ep)
        ok.add(aid)
    errs = NOTES.get("panoramax_err")
    tail = f"; failed AOIs: {len(errs)}" if errs else ""
    for f, why in [("panoramax_image_n", "count of items in the extent"), ("panoramax_camera_pitch_deg", "median pers:pitch item property"),
                   ("panoramax_camera_heading_deg", "circular mean view:azimuth item property"),
                   ("panoramax_gps_accuracy_m", "median quality:horizontal_accuracy item property")]:
        status(src, f, f"STAC /search over the AOI extent; {why}{tail}")


# ---------------------------------------------------------------- drivebc
ORIENT = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}


def drivebc():
    src = "drivebc_webcams"; ep = "https://www.drivebc.ca/api/webcams/"; lic = "not stated in API response (images carry a DriveBC.ca mark)"
    r = get(ep)
    cams = r.json() if r is not None and r.status_code == 200 else []
    if not cams:
        for f in ("drivebc_webcam_n", "drivebc_nearest_camera_km", "drivebc_camera_heading", "drivebc_snapshot_date"):
            status(src, f, "camera list did not load")
        return
    for aid, g, b in aoi_geoms():
        if not (48.2 <= g.centroid.y <= 60 and -139.1 <= g.centroid.x <= -114):
            continue  # DriveBC covers British Columbia only
        ds = sorted(((dist_km(g, c["location"]["coordinates"][0], c["location"]["coordinates"][1]), c) for c in cams if c.get("location")), key=lambda x: x[0])
        inside = [c for d, c in ds if d == 0]
        row(aid, src, "drivebc_webcam_n", len(inside), "count", TODAY, "", "DriveBC cameras with position inside the AOI polygon (snapshot)", ep, lic, ep)
        d0, c0 = ds[0]
        last = c0.get("last_update_modified")
        t = iso(parse_t(last)) if last else TODAY
        row(aid, src, "drivebc_nearest_camera_km", round(d0, 2), "km", t, "PT1S", f"Distance from the AOI polygon to the nearest DriveBC camera: {c0['name']} (id {c0['id']})", ep, lic, ep)
        if d0 <= 5 and c0.get("orientation") in ORIENT:
            row(aid, src, "drivebc_camera_heading", ORIENT[c0["orientation"]], "deg", t, "PT1S",
                f"Compass direction camera {c0['id']} '{c0['name']}' faces (orientation field '{c0['orientation']}'), {d0:.2f} km from the AOI", ep, lic, ep)
        if d0 <= 5 and last:
            row(aid, src, "drivebc_snapshot_date", iso(parse_t(last)), "datetime", t, "PT1S",
                f"last_update_modified of camera {c0['id']}: time of its latest frame, {d0:.2f} km from the AOI", ep, lic, ep)
    status(src, "drivebc_webcam_n", "camera list filtered by AOI polygon; BC AOIs only (DriveBC is BC-only, other AOIs are out of coverage)")
    status(src, "drivebc_nearest_camera_km", "nearest camera to the AOI polygon, BC AOIs only")
    status(src, "drivebc_camera_heading", "orientation field of the nearest camera if within 5 km")
    status(src, "drivebc_snapshot_date", "last_update_modified of the nearest camera if within 5 km")


# ---------------------------------------------------------------- phenocam
def phenocam():
    src = "phenocam"; ep = "https://phenocam.nau.edu/api/cameras/"; lic = "not stated in API response (PhenoCam data policy requires citation)"
    cams, url = [], "https://phenocam.nau.edu/api/cameras/?format=json&limit=500"
    while url:
        r = get(url)
        if r is None or r.status_code != 200:
            break
        j = r.json(); cams += j["results"]; url = j.get("next")
    rois, url = [], "https://phenocam.nau.edu/api/roilists/?format=json&limit=500"
    while url:
        r = get(url)
        if r is None or r.status_code != 200:
            break
        j = r.json(); rois += j["results"]; url = j.get("next")
    if not cams:
        for f in ("phenocam_gcc", "phenocam_camera_heading", "phenocam_missing_data_pct", "phenocam_station_distance_km"):
            status(src, f, "site list did not load")
        return
    for aid, g, b in aoi_geoms():
        ds = sorted(((dist_km(g, c["Lon"], c["Lat"]), c["Sitename"], c) for c in cams if c.get("Lat") is not None), key=lambda x: x[0])
        d0, name, c0 = ds[0]
        row(aid, src, "phenocam_station_distance_km", round(d0, 1), "km", c0.get("date_last") and f"{c0['date_last']}T00:00:00Z" or TODAY, "P12H" if c0.get("date_last") else "",
            f"Distance from the AOI polygon to the nearest PhenoCam site: {name} ({'active' if c0['active'] else 'inactive'}, {c0.get('date_first')} to {c0.get('date_last')})", ep, lic, ep)
        # GCC and QC fields: nearest site within 30 km only
        near = [(d, n, c) for d, n, c in ds if d <= 30]
        if not near:
            continue
        d, name, c = near[0]
        sr = sorted([r_ for r_ in rois if r_["site"] == name], key=lambda r_: (r_["roitype"] != "AG", r_["sequence_number"]))
        ori = (c.get("sitemetadata") or {}).get("camera_orientation")
        if ori in ORIENT:
            row(aid, src, "phenocam_camera_heading", ORIENT[ori], "deg", f"{c['date_last']}T00:00:00Z", "P12H",
                f"Compass direction camera {name} faces (camera_orientation '{ori}'), {d:.1f} km from the AOI", ep, lic, ep)
        if not sr:
            continue
        r0 = sr[0]
        row(aid, src, "phenocam_missing_data_pct", float(r0["missing_data_pct"]), "percent", f"{r0['last_date']}T00:00:00Z", "P12H",
            f"Missing-days share of ROI {r0['roi_name']} ({r0['first_date']} to {r0['last_date']}), site {d:.1f} km from the AOI", r0["roi_page"], lic, "https://phenocam.nau.edu/api/roilists/")
        rr = get(r0["one_day_summary"])
        if rr is None or rr.status_code != 200:
            continue
        lines = [l for l in rr.text.splitlines() if not l.startswith("#")]
        rd = list(csv.DictReader(lines))
        tail = [x for x in rd[-30:] if x["gcc_90"] not in ("NA", "") and x["outlierflag_gcc_90"] in ("NA", "")]
        if tail:
            vals_ = [float(x["gcc_90"]) for x in tail]
            ts = [dt.datetime.fromisoformat(x["date"]).replace(tzinfo=dt.timezone.utc) + dt.timedelta(hours=12) for x in tail]
            tm, acc = span(ts)
            row(aid, src, "phenocam_gcc", round(statistics.mean(vals_), 4), "ratio", tm, acc,
                f"Mean daily gcc_90 of ROI {r0['roi_name']} over the last {len(tail)} valid days of the series ({tail[0]['date']} to {tail[-1]['date']}), site {d:.1f} km from the AOI",
                r0["one_day_summary"], lic, r0["one_day_summary"])
    status(src, "phenocam_station_distance_km", "distance from the AOI polygon to the nearest site in the global camera list")
    status(src, "phenocam_camera_heading", "camera_orientation of the nearest site, read only within 30 km")
    status(src, "phenocam_missing_data_pct", "roilists missing_data_pct of the nearest site's ROI, read only within 30 km")
    status(src, "phenocam_gcc", "mean of the last 30 valid days of gcc_90 in the 1-day summary CSV of the nearest site's ROI, read only within 30 km")


# ---------------------------------------------------------------- wikimedia
WM = "https://commons.wikimedia.org/w/api.php"


def wm_tile(b, depth=0):
    w, s, e, n = b
    r = get(WM, dict(action="query", list="geosearch", gsbbox=f"{n}|{w}|{s}|{e}", gsnamespace=6, gslimit=500, format="json"), gap=1.0)
    if r is None or r.status_code != 200 or "error" in r.json():
        raise RuntimeError(f"wikimedia {None if r is None else (r.status_code, r.text[:100])}")
    hits = r.json()["query"]["geosearch"]
    if len(hits) < 500 or depth >= 6:
        return hits
    mx, my = (w + e) / 2, (s + n) / 2
    out = []
    for q in ((w, s, mx, my), (mx, s, e, my), (w, my, mx, n), (mx, my, e, n)):
        out += wm_tile(q, depth + 1)
    return out


def wm_hits(b):
    w, s, e, n = b
    # the API refuses boxes over 10 km a side; tile at <= 8 km
    nx = max(1, math.ceil((e - w) * 111.32 * math.cos(math.radians((s + n) / 2)) / 8)); ny = max(1, math.ceil((n - s) * 111.32 / 8))
    out = {}
    for i in range(nx):
        for j in range(ny):
            t = (w + (e - w) * i / nx, s + (n - s) * j / ny, w + (e - w) * (i + 1) / nx, s + (n - s) * (j + 1) / ny)
            for h in wm_tile(t):
                out[h["pageid"]] = h
    return list(out.values())


def wikimedia():
    src = "wikimedia_commons"; lic = "per file (CC BY, CC BY-SA, PD)"; ep = WM + "?action=query&list=geosearch&gsbbox={n}|{w}|{s}|{e}&gsnamespace=6 (tiled <= 8 km)"
    url = "https://commons.wikimedia.org/wiki/Special:Search"
    fails = 0
    for aid, g, b in aoi_geoms():
        try:
            hits = wm_hits(b)
        except RuntimeError:
            fails += 1; continue
        row(aid, src, "wikimedia_photo_n", len(hits), "count", TODAY, "", "Commons files (namespace 6) with a coordinate inside the AOI extent (snapshot)", url, lic, ep)
        if not hits:
            continue
        step = max(1, len(hits) // 120)
        sample = hits[::step][:120]
        heads, times, nmeta = [], [], 0
        for i in range(0, len(sample), 50):
            ids = "|".join(str(h["pageid"]) for h in sample[i:i + 50])
            r = get(WM, dict(action="query", pageids=ids, prop="imageinfo", iiprop="metadata|timestamp|extmetadata", format="json", formatversion=2), gap=1.0)
            if r is None or r.status_code != 200:
                continue
            for p in r.json().get("query", {}).get("pages", []):
                ii = (p.get("imageinfo") or [{}])[0]
                nmeta += 1
                md = {m["name"]: m["value"] for m in (ii.get("metadata") or []) if isinstance(m, dict) and "name" in m}
                hd = md.get("GPSImgDirection")
                try:
                    if isinstance(hd, str) and "/" in hd:
                        a_, b_ = hd.split("/"); hd = float(a_) / float(b_)
                    if hd is not None:
                        heads.append(float(hd) % 360)
                except (ValueError, ZeroDivisionError):
                    pass
                dto = (ii.get("extmetadata") or {}).get("DateTimeOriginal", {}).get("value") or md.get("DateTimeOriginal")
                if dto:
                    try:
                        times.append(parse_t(str(dto)[:19].replace(" ", "T").replace(":", "-", 2)) if str(dto)[4] in ":-" else None)
                    except Exception:
                        pass
        times = [t for t in times if t and 1990 < t.year <= 2027]
        if heads and times:
            m, R = circ_mean(heads); tm, acc = span(times)
            row(aid, src, "wikimedia_camera_heading_deg", round(m, 1), "deg", tm, acc,
                f"Circular mean of EXIF GPSImgDirection over {len(heads)} of {nmeta} sampled files (of {len(hits)} in the AOI), resultant length {R:.2f}; time = span of DateTimeOriginal in the sample", url, lic, WM + "?action=query&prop=imageinfo&iiprop=metadata|extmetadata")
    tail = f"; {fails} AOIs failed after backoff" if fails else ""
    status(src, "wikimedia_photo_n", "geosearch over the AOI extent, tiled and split on a full page" + tail)
    status(src, "wikimedia_camera_heading_deg", "EXIF GPSImgDirection in imageinfo metadata, sample of up to 120 files per AOI" + tail)


# ---------------------------------------------------------------- inaturalist
INAT = "https://api.inaturalist.org/v1/observations"


def inat():
    src = "inaturalist"; lic = "per observation license_code (cc-by, cc-by-nc, cc0, ...)"; ep = INAT + "?nelat&nelng&swlat&swlng&photos=true"
    url = "https://www.inaturalist.org/observations"
    fails = 0
    for aid, g, b in aoi_geoms():
        w, s, e, n = b
        base = dict(nelat=n, nelng=e, swlat=s, swlng=w, photos="true")
        r = get(INAT, dict(base, per_page=1), gap=1.1)
        if r is None or r.status_code != 200:
            fails += 1; continue
        tot = r.json()["total_results"]
        row(aid, src, "inat_observation_n", tot, "count", TODAY, "", "iNaturalist observations with photos inside the AOI extent (snapshot; obscured records are shifted up to ~27 km)", url, lic, ep)
        if not tot:
            continue
        # time span of the sample only: newest 200 by observed date
        r = get(INAT, dict(base, per_page=200, order_by="observed_on", order="desc"), gap=1.1)
        if r is not None and r.status_code == 200:
            res = r.json()["results"]
            acc = [o["positional_accuracy"] for o in res if o.get("positional_accuracy") is not None]
            ts = [parse_t(o["time_observed_at"]) if o.get("time_observed_at") else dt.datetime.fromisoformat(o["observed_on"]).replace(tzinfo=dt.timezone.utc) for o in res if o.get("observed_on")]
            if acc and ts:
                tm, ta = span(ts)
                row(aid, src, "inat_gps_accuracy_m", round(statistics.median(acc), 1), "m", tm, ta,
                    f"Median positional_accuracy of the newest {len(res)} observations ({len(acc)} carry it; {tot} in the AOI)", url, lic, ep + "&order_by=observed_on&order=desc&per_page=200")
        parts = []
        for q in ("research", "needs_id", "casual"):
            rq = get(INAT, dict(base, per_page=1, quality_grade=q), gap=1.1)
            if rq is not None and rq.status_code == 200:
                parts.append(f"{q}:{rq.json()['total_results']}")
        if len(parts) == 3:
            row(aid, src, "inat_quality_grade", ";".join(parts), "text", TODAY, "", "Observation counts by community quality_grade in the AOI (snapshot)", url, lic, ep + "&quality_grade={research|needs_id|casual}")
    tail = f"; {fails} AOIs failed after backoff" if fails else ""
    status(src, "inat_observation_n", "total_results of /v1/observations over the AOI extent" + tail)
    status(src, "inat_gps_accuracy_m", "median positional_accuracy of the newest 200 observations per AOI" + tail)
    status(src, "inat_quality_grade", "three quality_grade-filtered total_results over the AOI extent" + tail)


# ---------------------------------------------------------------- gbif media
GB = "https://api.gbif.org/v1/occurrence/search"


def gbif_media():
    src = "gbif_media"; lic = "per record (CC0, CC-BY, CC-BY-NC)"; ep = GB + "?mediaType=StillImage&geometry=POLYGON(...)"
    url = "https://www.gbif.org/occurrence/search?media_type=StillImage"
    fails = 0
    for aid, g, b in aoi_geoms():
        w, s, e, n = b
        geom = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
        r = get(GB, dict(geometry=geom, mediaType="StillImage", limit=300), gap=0.3)
        if r is None or r.status_code != 200:
            fails += 1; continue
        j = r.json(); cnt = j["count"]
        row(aid, src, "gbifmedia_image_n", cnt, "count", TODAY, "", "GBIF occurrences with a StillImage inside the AOI extent (snapshot; mostly iNaturalist copies)", url, lic, ep)
        res = j["results"]
        unc = [o["coordinateUncertaintyInMeters"] for o in res if o.get("coordinateUncertaintyInMeters") is not None]
        ts = []
        for o in res:
            try:
                if o.get("eventDate"):
                    ts.append(parse_t(o["eventDate"][:19] if "T" in o["eventDate"] else o["eventDate"][:10] + "T12:00:00"))
            except ValueError:
                pass
        if unc and ts:
            tm, acc = span(ts)
            row(aid, src, "gbifmedia_coordinate_uncertainty_m", round(statistics.median(unc), 1), "m", tm, acc,
                f"Median coordinateUncertaintyInMeters of the first {len(res)} records ({len(unc)} carry it; {cnt} in the AOI); time = span of eventDate in the sample", url, lic, ep + "&limit=300")
    tail = f"; {fails} AOIs failed after backoff" if fails else ""
    status(src, "gbifmedia_image_n", "count of /occurrence/search mediaType=StillImage over the AOI polygon" + tail)
    status(src, "gbifmedia_coordinate_uncertainty_m", "median coordinateUncertaintyInMeters over the first 300 records per AOI" + tail)


# ---------------------------------------------------------------- geograph
def geograph():
    src = "geograph"; ep = "https://www.geograph.org.uk/syndicator.php"
    ans = []
    for aid, g, b in aoi_geoms():
        r = get(ep, dict(format="JSON", q=f"{g.centroid.y},{g.centroid.x}"), gap=1.0)
        try:
            j = r.json(); ans.append(len(j.get("items", [])) if "items" in j else j.get("error", "?"))
        except Exception:
            ans.append("err")
    rc = get(ep, dict(format="JSON", q="51.5,-0.12"), gap=1.0)
    ctl = len(rc.json().get("items", [])) if rc is not None else "err"
    NOTES["geograph"] = f"AOI answers {sorted(set(map(str, ans)))}; London control {ctl} items"
    status(src, "geograph_photo_n", f"Geograph covers Britain and Ireland only; no AOI is inside it ({NOTES['geograph']}). Outside coverage is not a zero, so no value is written")


SOURCES = dict(panoramax=panoramax, drivebc_webcams=drivebc, phenocam=phenocam, gbif_media=gbif_media, geograph=geograph,
               inaturalist=inat, wikimedia_commons=wikimedia)

if __name__ == "__main__":
    which = sys.argv[1:] or list(SOURCES)
    for k in which:
        t0 = time.time()
        try:
            SOURCES[k]()
        except Exception as ex:
            import traceback; traceback.print_exc()
            STATUS.append(dict(source=k, feature="*", status="dropped", n_aois_with_value=0, reason=f"script error {ex!r}"))
        print(k, "done", round(time.time() - t0), "s", flush=True)
        suffix = "" if len(which) == len(SOURCES) else "." + "+".join(which)
        with open(os.path.join(HERE, f"poc_values{suffix}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(VALUES)
        with open(os.path.join(HERE, f"poc_status{suffix}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, "source,feature,status,n_aois_with_value,reason".split(",")); w.writeheader(); w.writerows(STATUS)

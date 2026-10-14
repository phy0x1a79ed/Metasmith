"""Q5: return item id plus asset hrefs per observation and prove the hrefs resolve.

Planetary Computer hrefs need a SAS token (planetary_computer.sign); Earth Search Sentinel-2 hrefs are
public https; Earth Search Landsat hrefs are s3:// requester-pays.
"""
import datetime as dtm
import json
from urllib.parse import parse_qs, urlparse

import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

import common as c

RANGE = ("2023-06-01", "2023-08-31")
KEYS = {
    ("PC", "sentinel-2-l2a"): ["B04", "B08", "B11", "SCL", "granule-metadata"],
    ("PC", "landsat-c2-l2"): ["red", "nir08", "swir16", "qa_pixel", "mtl.json"],
    ("ES", "sentinel-2-l2a"): ["red", "nir", "swir16", "scl", "granule_metadata"],
    ("ES", "landsat-c2-l2"): ["red", "nir08", "swir16", "qa_pixel", "mtl.json"],
}


def best_item(base, coll, bbox):
    body = {"collections": [coll], "bbox": bbox, "datetime": c.dt(*RANGE), "limit": 200}
    feats, n, st = c.search_all(base, body, max_pages=1)
    if not feats:
        return None, st
    return min(feats, key=lambda f: f["properties"].get("eo:cloud_cover", 101)), st


def observation(cat, item):
    """The proposed per-observation pointer: id, time, and one href per requested asset key."""
    keys = KEYS[(cat, item["collection"])]
    assets = {}
    for k in keys:
        a = item["assets"].get(k)
        if a:
            href = c.sign_pc(a["href"]) if cat == "PC" else a["href"]
            assets[k] = {"href": href, "type": a.get("type"), "requester_pays": a.get("storage:requester_pays", False)}
    return {"item_id": item["id"], "collection": item["collection"], "datetime": item["properties"]["datetime"],
            "self": next((l["href"] for l in item["links"] if l["rel"] == "self"), None), "assets": assets}


def range_probe(href):
    """HTTP range request for the first 1 KiB: 206 proves the href resolves and serves bytes."""
    if href.startswith("s3://"):
        return "s3://", None
    r = c.HTTP.get(href, headers={"Range": "bytes=0-1023"}, timeout=60)
    return r.status_code, len(r.content)


def sas_expiry(href):
    q = parse_qs(urlparse(href).query)
    se = q.get("se", [None])[0]
    if not se:
        return None
    t = dtm.datetime.fromisoformat(se.replace("Z", "+00:00"))
    return t, (t - dtm.datetime.now(dtm.timezone.utc)).total_seconds() / 60


def window_read(href, bbox, size=64):
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF"):
        with rasterio.open(href) as ds:
            b = transform_bounds("EPSG:4326", ds.crs, *bbox)
            w = from_bounds(*b, transform=ds.transform).round_offsets()
            w = Window(w.col_off, w.row_off, min(size, ds.width - w.col_off), min(size, ds.height - w.row_off))
            x = ds.read(1, window=w)
            return {"shape": x.shape, "dtype": str(x.dtype), "min": int(x.min()), "max": int(x.max()), "mean": round(float(x.mean()), 1),
                    "crs": str(ds.crs), "overviews": ds.overviews(1)[:3]}


def redact(o):
    """Drop SAS query strings before anything is written to disk."""
    if isinstance(o, dict):
        return {k: redact(v) for k, v in o.items()}
    if isinstance(o, list):
        return [redact(v) for v in o]
    if isinstance(o, str) and "sig=" in o:
        return o.split("?")[0] + "?<sas-redacted>"
    return o


def run(verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    out = {"observations": {}, "hits": {}, "window_read": {}, "expiry": {}, "unsigned": {}}
    for cat, base in c.CATALOGS.items():
        for coll in ("sentinel-2-l2a", "landsat-c2-l2"):
            hits = []
            for a in c.load_aois():
                item, st = best_item(base, coll, a["bbox"])
                if not item:
                    log(f"{cat}:{coll} {a['id']:26s} no item (http {st})")
                    continue
                ob = observation(cat, item)
                first = next(iter(ob["assets"].values()))["href"] if ob["assets"] else None
                code, nbytes = range_probe(first) if first else (None, None)
                ob["range_probe"] = {"status": code, "bytes": nbytes}
                out["observations"].setdefault(f"{cat}:{coll}", {})[a["id"]] = ob
                if code == 206:
                    hits.append(a["id"])
                log(f"{cat}:{coll} {a['id']:26s} {item['id']}  assets={len(ob['assets'])}  range GET -> {code} ({nbytes} B)")
            out["hits"][f"{cat}:{coll}"] = hits
    # window read through rasterio on the first AOI, one href per combo
    log("\n== rasterio 64x64 window read of one href per combo (first AOI whose range GET was 206, else farm_sk_quarter) ==")
    for combo, obs in out["observations"].items():
        aid = next((x for x in c.load_aois() if x["id"] in out["hits"][combo]), None) or c.aoi("farm_sk_quarter")
        aid = aid if isinstance(aid, dict) else c.aoi(aid)
        ob = obs.get(aid["id"])
        if not ob:
            continue
        key = next(iter(ob["assets"]))
        href = ob["assets"][key]["href"]
        try:
            r = window_read(href, aid["bbox"])
            out["window_read"][combo] = {"aoi": aid["id"], "asset": key, **r}
            log(f"{combo} {aid['id']} {ob['item_id']} {key}: {r}")
        except Exception as e:
            out["window_read"][combo] = {"aoi": aid["id"], "asset": key, "error": f"{type(e).__name__}: {str(e)[:140]}"}
            log(f"{combo} {aid['id']} {key}: FAILED {type(e).__name__}: {str(e)[:140]}")
    # unsigned PC href and SAS expiry
    log("\n== Planetary Computer SAS ==")
    ob = out["observations"]["PC:sentinel-2-l2a"]["farm_sk_quarter"]  # signed hrefs kept in memory only
    signed = ob["assets"]["B04"]["href"]
    unsigned = signed.split("?")[0]
    r = c.HTTP.get(unsigned, headers={"Range": "bytes=0-1023"})
    out["unsigned"] = {"status": r.status_code, "body": r.text[:120]}
    log(f"unsigned href -> HTTP {r.status_code} {r.text[:100]!r}")
    exp = sas_expiry(signed)
    if exp:
        out["expiry"] = {"se": exp[0].isoformat(), "minutes_remaining": round(exp[1], 1)}
        log(f"signed href query params: {sorted(parse_qs(urlparse(signed).query))}")
        log(f"SAS expiry se={exp[0].isoformat()}  ({exp[1]:.1f} min from now)")
    parsed = urlparse(unsigned)
    acct = parsed.netloc.split(".")[0]
    container = parsed.path.split("/")[1]
    t = c.HTTP.get(f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{acct}/{container}")
    if t.status_code == 200:
        j = t.json()
        out["expiry"]["token_endpoint"] = {k: v for k, v in j.items() if k != "token"}
        log(f"token endpoint /api/sas/v1/token/{acct}/{container}: {out['expiry']['token_endpoint']}")
    out["example_observation"] = ob
    log("\n== proposed observation.assets payload (PC Sentinel-2, SAS truncated) ==")
    log(json.dumps({**ob, "assets": {k: {**v, "href": v["href"][:110] + "..."} for k, v in ob["assets"].items()}}, indent=1))
    json.dump(redact(out), open(f"{c.OUT}/q5_result.json", "w"), indent=1, default=str)
    return out


if __name__ == "__main__":
    run()

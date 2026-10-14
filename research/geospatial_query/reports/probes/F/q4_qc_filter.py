"""Q4: push QC filters into the STAC search and prove each is honoured with differential counts.

Per filter F on a fixed AOI/year: N = unfiltered, F = filtered, notF = complement, imp = impossible
value. A dialect that ignores the filter returns N for F, notF and imp; a working one returns imp == 0
and F + notF <= N. Dialects tried: CQL2-JSON (filter-lang cql2-json) and the STAC query extension.
Also shows post-read AOI cloud filtering from the Sentinel-2 SCL band for one AOI.
"""
import json

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

import common as c

YEAR = ("2023-01-01", "2023-12-31")
PROBE_AOI = "farm_sk_quarter"
DIALECT_AOIS = ["farm_sk_quarter", "city_toronto_core"]

# name, collection, property, op, value, complement op, impossible (op, value)
FILTERS = [
    ("max_cloud_aoi_tile", "sentinel-2-l2a", "eo:cloud_cover", "<", 10, ">=", ("<", -1)),
    ("max_cloud_aoi_tile", "landsat-c2-l2", "eo:cloud_cover", "<", 10, ">=", ("<", -1)),
    ("min_sun_elevation_deg", "landsat-c2-l2", "view:sun_elevation", ">", 30, "<=", (">", 91)),
    ("max_off_nadir_deg", "landsat-c2-l2", "view:off_nadir", "<", 5, ">=", ("<", -1)),
    ("min_sun_elevation_deg", "sentinel-2-l2a", "view:sun_elevation", ">", 30, "<=", (">", 91)),
    ("off_nadir_responds", "landsat-c2-l2", "view:off_nadir", ">", 1, "<=", (">", 91)),
    ("max_solar_zenith_deg", "sentinel-2-l2a", "s2:mean_solar_zenith", "<", 60, ">=", ("<", -1)),
    ("processing_level", "landsat-c2-l2", "landsat:correction", "=", "L2SP", "<>", ("=", "XXXX")),
    ("processing_level", "sentinel-2-l2a", "s2:product_type", "=", "S2MSI2A", "<>", ("=", "XXXX")),
]
QOP = {"<": "lt", "<=": "lte", ">": "gt", ">=": "gte", "=": "eq", "<>": "neq"}


def fid(f):
    return f"{f[2]}{f[3]}{f[4]}"


def cql(prop, op, val):
    return {"filter-lang": "cql2-json", "filter": {"op": op, "args": [{"property": prop}, val]}}


def qext(prop, op, val):
    return {"query": {prop: {QOP[op]: val}}}


DIALECTS = {"cql2-json": cql, "query-ext": qext}


def base_body(coll, bbox):
    return {"collections": [coll], "bbox": bbox, "datetime": c.dt(*YEAR)}


def counts(base, coll, bbox, dialect, f, with_imp=True):
    _, _, prop, op, val, cop, (iop, ival) = f[:1] + f[1:]
    b = base_body(coll, bbox)
    out = {}
    for tag, o, v in (("F", op, val), ("notF", cop, val)) + ((("imp", iop, ival),) if with_imp else ()):
        n, st, req = c.count(base, {**b, **DIALECTS[dialect](prop, o, v)})
        out[tag] = n if st == 200 else f"HTTP{st}"
    return out


def verdict(N, r):
    if any(isinstance(v, str) for v in r.values()):
        return "error"
    if N == 0:
        return "no-data"
    if r["F"] + r["notF"] == 0:
        return "property-absent"
    if r.get("imp", 0) == N and r["F"] == N:
        return "IGNORED"
    if r.get("imp", 1) == 0:
        return "honoured"
    return "ambiguous"


def sample_props(base, coll, bbox):
    body = {**base_body(coll, bbox), "limit": 20}
    feats, _, _ = c.search_all(base, body, max_pages=1)
    return feats


def queryables(base, coll):
    r = c.HTTP.get(f"{base}/collections/{coll}/queryables")
    return sorted(r.json().get("properties", {})) if r.status_code == 200 else []


def scl_aoi_cloud(item, bbox):
    href = c.sign_pc(item["assets"]["SCL"]["href"])
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MAX_RETRY="3"):
        with rasterio.open(href) as ds:
            b = transform_bounds("EPSG:4326", ds.crs, *bbox)
            w = from_bounds(*b, transform=ds.transform).round_offsets().round_lengths()
            x = ds.read(1, window=w)
    valid = x > 0
    if not valid.any():
        return None
    cloud = np.isin(x, [8, 9, 10])  # medium, high probability cloud, thin cirrus
    shadow = x == 3
    return {"cloud_pct": 100 * cloud[valid].mean(), "shadow_pct": 100 * shadow[valid].mean(), "px": int(valid.sum())}


def scl_demo(log):
    a = c.aoi(PROBE_AOI)
    body = {**base_body("sentinel-2-l2a", a["bbox"]), "datetime": c.dt("2023-04-01", "2023-10-31"), "limit": 200}
    feats, n, _ = c.search_all(c.PC, body)
    feats.sort(key=lambda f: f["properties"]["datetime"])
    feats = feats[::max(1, len(feats) // 40)][:40]
    rows = []
    for f in feats:
        try:
            r = scl_aoi_cloud(f, a["bbox"])
        except Exception as e:
            r = None
            log(f"  SCL read failed {f['id']}: {type(e).__name__}")
        if r:
            rows.append((f["id"], f["properties"]["datetime"][:10], f["properties"]["eo:cloud_cover"], r["cloud_pct"], r["shadow_pct"]))
    tile_pass = sum(1 for r in rows if r[2] < 10)
    aoi_pass = sum(1 for r in rows if r[3] + r[4] < 10)
    disagree = [r for r in rows if (r[2] < 10) != (r[3] + r[4] < 10)]
    log(f"\n== post-read AOI cloud from SCL: {PROBE_AOI}, {len(rows)} S2 scenes Apr-Oct 2023 (PC, signed SCL, 20 m window) ==")
    log(f"tile eo:cloud_cover < 10 passes {tile_pass}; AOI (SCL cloud+shadow) < 10 passes {aoi_pass}; the two disagree on {len(disagree)}")
    for r in rows:
        mark = "  <-- differs" if r in disagree else ""
        log(f"  {r[1]} tile_cc={r[2]:6.2f} aoi_cloud={r[3]:6.2f} aoi_shadow={r[4]:5.2f}  {r[0]}{mark}")
    return {"scenes": len(rows), "tile_pass": tile_pass, "aoi_pass": aoi_pass, "disagree": len(disagree),
            "rows": rows, "search_requests": n}


def run(verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    out = {"year": YEAR, "queryables": {}, "props_present": {}, "dialect": {}, "per_aoi": {}, "control": {}, "scl": None}
    for cat, base in c.CATALOGS.items():
        for coll in ("sentinel-2-l2a", "landsat-c2-l2"):
            q = queryables(base, coll)
            out["queryables"][f"{cat}:{coll}"] = q
            feats = sample_props(base, coll, c.aoi(PROBE_AOI)["bbox"])
            props = feats[0]["properties"] if feats else {}
            wanted = ["eo:cloud_cover", "view:off_nadir", "view:sun_elevation", "s2:mean_solar_zenith", "landsat:correction", "s2:product_type"]
            out["props_present"][f"{cat}:{coll}"] = {p: (p in props) for p in wanted}
            log(f"{cat}:{coll} queryables({len(q)}): in queryables={[p for p in wanted if p in q]}  in item properties={[p for p in wanted if p in props]}")
    log("\n== dialect discovery (counts for 2023 over the AOI: N unfiltered | F filtered | notF complement | imp impossible) ==")
    best = {}
    for cat, base in c.CATALOGS.items():
        for f in FILTERS:
            name, coll, prop = f[0], f[1], f[2]
            for aid in DIALECT_AOIS:
                bbox = c.aoi(aid)["bbox"]
                N, st, _ = c.count(base, base_body(coll, bbox))
                for d in DIALECTS:
                    r = counts(base, coll, bbox, d, f)
                    v = verdict(N, r)
                    out["dialect"].setdefault(f"{cat}:{coll}:{fid(f)}", {}).setdefault(d, {})[aid] = {"N": N, **r, "verdict": v}
                    log(f"{cat} {coll:15s} {prop:22s} {f[3]}{f[4]!s:8s} {d:9s} {aid:18s} N={N} F={r['F']} notF={r['notF']} imp={r['imp']} -> {v}")
                    if v == "honoured" and aid == DIALECT_AOIS[0]:
                        best.setdefault((cat, coll, fid(f)), d)
    out["best_dialect"] = {f"{k[0]}:{k[1]}:{k[2]}": v for k, v in best.items()}
    log("\nworking dialect per catalogue/property:", json.dumps(out["best_dialect"], indent=1))
    log("\n== all 15 AOIs with the working dialect (2023) ==")
    hits = {cat: {} for cat in c.CATALOGS}
    for a in c.load_aois():
        for cat, base in c.CATALOGS.items():
            for f in FILTERS:
                d = best.get((cat, f[1], fid(f)))
                key = f"{f[1]}:{fid(f)}"
                if d is None:
                    hits[cat].setdefault(key, [])
                    continue
                N, st, _ = c.count(base, base_body(f[1], a["bbox"]))
                r = counts(base, f[1], a["bbox"], d, f, with_imp=False)
                ok = (N > 0 and not any(isinstance(v, str) for v in r.values()) and r["F"] + r["notF"] <= N and (r["F"] < N or r["notF"] < N or N == r["F"] + r["notF"]))
                out["per_aoi"].setdefault(a["id"], {}).setdefault(cat, {})[key] = {"N": N, **r, "dialect": d}
                hits[cat].setdefault(key, [])
                if ok and r["F"] + r["notF"] == N:
                    hits[cat][key].append(a["id"])
                log(f"{a['id']:26s} {cat} {f[1]:15s} {f[2]+f[3]+str(f[4]):26s} N={N:4d} F={r['F']!s:>4} notF={r['notF']!s:>4} {'ok' if ok else 'CHECK'}")
    out["aoi_hits"] = {cat: {k: len(v) for k, v in d.items()} for cat, d in hits.items()}
    # control: mid-Pacific must return nothing even with a trivially true filter
    for cat, base in c.CATALOGS.items():
        for coll in ("sentinel-2-l2a", "landsat-c2-l2"):
            n, st, _ = c.count(base, base_body(coll, c.CONTROL_BBOX))
            out["control"][f"{cat}:{coll}"] = n
            log(f"control mid-Pacific {cat}:{coll} items={n}")
    out["scl"] = scl_demo(log)
    json.dump(out, open(f"{c.OUT}/q4_result.json", "w"), indent=1, default=str)
    return out


if __name__ == "__main__":
    run()

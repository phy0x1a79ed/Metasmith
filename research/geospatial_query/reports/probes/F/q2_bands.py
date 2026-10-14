"""Q2: resolve band common names and spectral-index names to STAC assets, then compute an AOI mean.

One query spec drives both collections on both catalogues: band names are resolved through eo:bands,
index names through spyndex (formula -> spyndex band -> common_name/wavelength window -> asset).
"""
import json
import sys
import time

import numpy as np
import rasterio
import spyndex
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

import common as c

SPEC = {
    "aoi": "farm_sk_quarter",
    "time": "2023-07-01/2023-07-31",
    "collections": ["sentinel-2-l2a", "landsat-c2-l2"],
    "bands": ["red", "nir", "swir16"],
    "indices": ["NDVI", "NDWI", "NBR"],
    "max_cloud": 20,
}
EXTRA_INDICES = ["SAVI", "EVI"]  # need constants, shown in the resolve table only


def single_band_assets(assets):
    """Assets that hold exactly one band (excludes 'visual', the -jp2 duplicates and metadata)."""
    out = {}
    for k, a in assets.items():
        eb = a.get("eo:bands") or []
        if len(eb) == 1 and not k.endswith("-jp2") and "data" in (a.get("roles") or ["data"]):
            out[k] = eb[0]
    return out


def resolve_common_name(assets, name, wl_window=None):
    """Return (asset_key, how) for a STAC common name; falls back to a wavelength window (nm)."""
    cand = single_band_assets(assets)
    hits = [k for k, b in cand.items() if b.get("common_name") == name]
    if len(hits) == 1:
        return hits[0], "common_name"
    if len(hits) > 1:
        return hits, "ambiguous common_name"
    if wl_window:
        lo, hi = wl_window
        mid = (lo + hi) / 2
        inside = [(abs(b["center_wavelength"] * 1000 - mid), k) for k, b in cand.items()
                  if b.get("center_wavelength") and lo <= b["center_wavelength"] * 1000 <= hi]
        if inside:
            return sorted(inside)[0][1], f"wavelength {lo:.0f}-{hi:.0f}nm"
    return None, "unresolved"


def window_for_common_name(name):
    """Wavelength window (nm) of the spyndex band that carries this STAC common name, or None."""
    for b in spyndex.bands.values():
        if b.common_name == name:
            return (b.min_wavelength, b.max_wavelength)
    return None


def index_plan(index):
    """spyndex formula, the bands it needs (with STAC common name + wavelength window) and its constants."""
    idx = spyndex.indices[index]
    bands, consts = {}, {}
    for p in idx.bands:
        if p in spyndex.bands:
            b = spyndex.bands[p]
            bands[p] = {"common_name": b.common_name, "window": (b.min_wavelength, b.max_wavelength)}
        else:
            consts[p] = spyndex.constants[p].default
    return {"formula": idx.formula, "bands": bands, "constants": consts}


def resolve_spec(assets, spec):
    """Map every requested band and every index's bands to asset keys for one asset dictionary."""
    res = {"bands": {}, "indices": {}}
    for name in spec["bands"]:
        res["bands"][name] = resolve_common_name(assets, name, window_for_common_name(name))
    for ix in spec["indices"] + EXTRA_INDICES:
        plan = index_plan(ix)
        m = {}
        for p, info in plan["bands"].items():
            m[p] = resolve_common_name(assets, info["common_name"], info["window"])
        res["indices"][ix] = {"formula": plan["formula"], "constants": plan["constants"], "map": m}
    return res


def collection_assets(base, coll):
    r = c.HTTP.get(f"{base}/collections/{coll}")
    return r.json().get("item_assets", {}), r.json().get("license"), r.status_code


def pick_item(base, coll, bbox, rng, max_cloud):
    start, end = rng.split("/")
    body = {"collections": [coll], "bbox": bbox, "datetime": c.dt(start, end), "limit": 100}
    if base == c.PC:
        body["query"] = {"eo:cloud_cover": {"lt": max_cloud}}
    feats, n, st = c.search_all(base, body)
    if base != c.PC:
        feats = [f for f in feats if f["properties"].get("eo:cloud_cover", 100) < max_cloud]
    if not feats:
        return None, n, st
    feats.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
    return feats[0], n, st


def scale_offset(item, key):
    a = item["assets"][key]
    rb = (a.get("raster:bands") or [{}])[0]
    p = item["properties"]
    if "scale" in rb and not p.get("earthsearch:boa_offset_applied"):
        return rb["scale"], rb.get("offset", 0.0), "raster:bands"
    if p.get("earthsearch:boa_offset_applied"):  # ES declares offset -0.1 on the asset yet has already removed it
        return 1e-4, 0.0, "earthsearch:boa_offset_applied=true (asset raster:bands offset -0.1 ignored)"
    if item["collection"] == "sentinel-2-l2a":  # PC omits raster:bands on S2; baseline >= 04.00 adds -1000 DN
        base = float(str(p.get("s2:processing_baseline", "0")).split(".")[0] + "." + str(p.get("s2:processing_baseline", "0.0")).split(".")[-1])
        return 1e-4, (-0.1 if base >= 4.0 else 0.0), f"s2:processing_baseline={p.get('s2:processing_baseline')}"
    return 1.0, 0.0, "none"


def read_stack(item, keys, bbox, sign):
    """Read each asset over the AOI bbox on a common grid. Returns dict key -> masked float array (reflectance)."""
    hrefs = {k: (c.sign_pc(item["assets"][k]["href"]) if sign else item["assets"][k]["href"]) for k in keys}
    out, wins, dss = {}, {}, {}
    env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
               GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2")
    with rasterio.Env(**env):
        try:
            for k, h in hrefs.items():
                dss[k] = rasterio.open(h)
                b = transform_bounds("EPSG:4326", dss[k].crs, *bbox)
                wins[k] = from_bounds(*b, transform=dss[k].transform).round_offsets().round_lengths()
            H = max(int(w.height) for w in wins.values())
            W = max(int(w.width) for w in wins.values())
            for k, ds in dss.items():
                arr = ds.read(1, window=wins[k], out_shape=(H, W), resampling=Resampling.nearest, masked=True)
                sc, off, _ = scale_offset(item, k)
                out[k] = arr.astype("float64") * sc + off
        finally:
            for ds in dss.values():
                ds.close()
    return out, (H, W)


def aoi_means(item, res, spec, bbox, sign):
    keys = set()
    for ix in spec["indices"]:
        for p, (k, how) in res["indices"][ix]["map"].items():
            if isinstance(k, str):
                keys.add(k)
    for b in spec["bands"]:
        k = res["bands"][b][0]
        if isinstance(k, str):
            keys.add(k)
    arrays, shape = read_stack(item, sorted(keys), bbox, sign)
    vals = {}
    for b in spec["bands"]:
        k = res["bands"][b][0]
        if isinstance(k, str):
            vals[f"band:{b}"] = round(float(np.ma.mean(arrays[k])), 4)
    for ix in spec["indices"]:
        m = res["indices"][ix]["map"]
        if not all(isinstance(v[0], str) for v in m.values()):
            vals[ix] = None
            continue
        params = {p: arrays[v[0]] for p, v in m.items()}
        params.update(res["indices"][ix]["constants"])
        r = spyndex.computeIndex(ix, params=params)
        vals[ix] = round(float(np.ma.mean(np.ma.masked_invalid(r))), 4)
    return vals, shape


def run(verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    a = c.aoi(SPEC["aoi"])
    summary = {"spec": SPEC, "combos": {}, "all_aoi_resolution": {}}
    log("QUERY SPEC:", json.dumps(SPEC))
    log("\n== index plans (spyndex 0.12.0) ==")
    for ix in SPEC["indices"] + EXTRA_INDICES:
        p = index_plan(ix)
        log(f"{ix}: {p['formula']}  bands={ {k: v['common_name'] for k, v in p['bands'].items()} } constants={p['constants']}")
    for cat, base in c.CATALOGS.items():
        for coll in SPEC["collections"]:
            combo = f"{cat}:{coll}"
            log(f"\n== {combo} ==")
            ia, lic, st = collection_assets(base, coll)
            col_res = resolve_spec(ia, SPEC)
            col_ok = all(isinstance(v[0], str) for v in col_res["bands"].values())
            log(f"collection item_assets resolve bands: {col_res['bands']}  (collection HTTP {st}, licence {lic})")
            item, n, st = pick_item(base, coll, a["bbox"], SPEC["time"], SPEC["max_cloud"])
            if not item:
                log("no item"); summary["combos"][combo] = {"error": f"no item http {st}"}; continue
            res = resolve_spec(item["assets"], SPEC)
            log(f"item {item['id']} cloud={item['properties'].get('eo:cloud_cover')} (search pages={n})")
            for b, v in res["bands"].items():
                log(f"  band {b:7s} -> {v[0]} ({v[1]})")
            for ix, v in res["indices"].items():
                log(f"  {ix:5s} {v['formula']:28s} " + " ".join(f"{p}->{m[0]}({m[1]})" for p, m in v["map"].items()))
            entry = {"item": item["id"], "collection_level_ok": col_ok, "bands": {b: v[0] for b, v in res["bands"].items()},
                     "how": {b: v[1] for b, v in res["bands"].items()},
                     "indices": {ix: {p: m[0] for p, m in v["map"].items()} for ix, v in res["indices"].items()}}
            try:
                vals, shape = aoi_means(item, res, SPEC, a["bbox"], sign=(cat == "PC"))
                log(f"  AOI mean over {SPEC['aoi']} (window {shape[0]}x{shape[1]} px): {vals}")
                entry["aoi_mean"] = vals
                entry["read"] = "ok"
            except Exception as e:  # requester-pays or sandboxed reads end up here
                msg = f"{type(e).__name__}: {str(e)[:160]}"
                log(f"  READ FAILED: {msg}")
                entry["read"] = msg
                if item["assets"][next(iter(res['bands'].values()))[0]].get("storage:requester_pays"):
                    entry["read"] += " [storage:requester_pays=true]"
            summary["combos"][combo] = entry
    log("\n== resolution across all 15 AOIs (item assets, both catalogues, both collections) ==")
    ok = {k: [] for k in ("PC", "ES")}
    for ar in c.load_aois():
        if ar["tier"] != "test" and False:
            continue
        row = {}
        for cat, base in c.CATALOGS.items():
            good = True
            for coll in SPEC["collections"]:
                item, n, st = pick_item(base, coll, ar["bbox"], "2023-06-01/2023-08-31", 50)
                if not item:
                    good = False
                    continue
                res = resolve_spec(item["assets"], SPEC)
                miss = [b for b, v in res["bands"].items() if not isinstance(v[0], str)]
                miss += [ix for ix, v in res["indices"].items() if ix in SPEC["indices"] and not all(isinstance(m[0], str) for m in v["map"].values())]
                good = good and not miss
            row[cat] = good
            if good:
                ok[cat].append(ar["id"])
        log(f"  {ar['id']:26s} PC={row['PC']} ES={row['ES']}")
        summary["all_aoi_resolution"][ar["id"]] = row
    summary["control"] = {}
    for cat, base in c.CATALOGS.items():
        items = [pick_item(base, coll, c.CONTROL_BBOX, "2023-06-01/2023-08-31", 100)[0] for coll in SPEC["collections"]]
        summary["control"][cat] = sum(1 for i in items if i)
        log(f"control mid-Pacific {cat}: items found for both collections = {summary['control'][cat]} (expected 0)")
    summary["aoi_hits"] = {k: len(v) for k, v in ok.items()}
    log(f"AOIs where both collections resolved all bands and indices: PC {len(ok['PC'])}/15  ES {len(ok['ES'])}/15")
    json.dump(summary, open(f"{c.OUT}/q2_result.json", "w"), indent=1, default=str)
    return summary


if __name__ == "__main__":
    run()

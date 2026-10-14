"""Capella: the by-datetime tree holds one STAC item per product (GEO, GEC, SLC, SICD, SIDD, CPHD) of each collect.
Fetch one representative item per (satellite, acquisition minute) instead of all ~10k, which keeps the crawl near 1.7k requests."""
import json, re
from common import *

B = "https://capella-open-data.s3.us-west-2.amazonaws.com/"
_, keys = s3_list(B, "stac/capella-open-data-by-datetime/", delimiter=None, max_pages=60)
items = [k for k in keys if k.split("/")[-1].startswith("CAPELLA_")]
pref = {"GEO": 0, "GEC": 1, "SLC": 2, "SICD": 3, "SIDD": 4, "CPHD": 5}
best = {}
for k in items:
    m = re.match(r"CAPELLA_(C\d+)_(\w+?)_(\w+?)_(\w+?)_(\d{12})\d{2}_", k.split("/")[-1])
    if not m:
        continue
    g = (m.group(1), m.group(5))
    r = pref.get(m.group(3), 9)
    if g not in best or r < best[g][0]:
        best[g] = (r, k)
sel = [v[1] for v in best.values()]
print(len(items), "item keys,", len(sel), "acquisition groups", flush=True)
out = []
from concurrent.futures import ThreadPoolExecutor
def one(k):
    st, o = get_json(B + k)
    return o
with ThreadPoolExecutor(2) as ex:
    for o in ex.map(one, sel):
        if o:
            out.append({"id": o["id"], "bbox": o.get("bbox"), "geometry": o.get("geometry"), "properties": o["properties"], "assets": list(o.get("assets", {}))})
json.dump(out, open(CACHE / "sar_capella.json", "w"))
json.dump({"item_keys": len(items), "groups": len(sel)}, open(CACHE / "sar_capella_meta.json", "w"))
print("capella", len(out), flush=True)

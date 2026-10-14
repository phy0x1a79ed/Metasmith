"""Umbra: the STAC root links only 2024 and 2025, so enumerate items from the bucket listing and fetch each one (cached)."""
import json
from concurrent.futures import ThreadPoolExecutor
from common import *

B = "https://umbra-open-data-catalog.s3.amazonaws.com/"
_, keys = s3_list(B, "stac/", delimiter=None, max_pages=60)
items = [k for k in keys if not k.endswith("catalog.json")]
print(len(items), "item keys", flush=True)
out = []
def one(k):
    return get_json(B + k)[1]
with ThreadPoolExecutor(2) as ex:
    for i, o in enumerate(ex.map(one, items)):
        if o:
            out.append({"id": o["id"], "bbox": o.get("bbox"), "geometry": o.get("geometry"), "properties": o["properties"], "assets": list(o.get("assets", {}))})
        if i % 500 == 0:
            print(i, flush=True)
json.dump(out, open(CACHE / "sar_umbra.json", "w"))
json.dump({"item_keys": len(items), "fetched": len(out)}, open(CACHE / "sar_umbra_meta.json", "w"))
print("umbra", len(out), flush=True)

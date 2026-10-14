"""ICEYE: the collection links 589 items but the bucket holds more; fetch every stac-items/*.json key."""
import json
from common import *

B = "https://iceye-open-data-catalog.s3.amazonaws.com/"
_, keys = s3_list(B, "stac-items/", delimiter=None, max_pages=20)
out = []
for k in keys:
    o = get_json(B + k)[1]
    if o and o.get("type") == "Feature":
        out.append({"id": o["id"], "bbox": o.get("bbox"), "geometry": o.get("geometry"), "properties": o["properties"], "assets": list(o.get("assets", {}))})
json.dump(out, open(CACHE / "sar_iceye.json", "w"))
json.dump({"item_keys": len(keys), "fetched": len(out)}, open(CACHE / "sar_iceye_meta.json", "w"))
print("iceye", len(out))

"""Crawl the static open-SAR STAC trees once and store compact item summaries in cache/."""
import json, sys
from common import *

ROOTS = {
    "umbra": ("https://umbra-open-data-catalog.s3.amazonaws.com/stac/catalog.json", None),
    "capella": ("https://capella-open-data.s3.us-west-2.amazonaws.com/stac/capella-open-data-by-datetime/catalog.json", None),
    "planet": ("https://www.planet.com/data/stac/catalog.json", lambda h, p: not any(x in h for x in ("spacenet7", "/fusion/"))),
    "iceye": ("https://iceye-open-data-catalog.s3.amazonaws.com/collections/iceye-sar.json", None),
}
if __name__ == "__main__":
    for name in sys.argv[1:] or ROOTS:
        url, flt = ROOTS[name]
        items = crawl(url, flt, workers=2)
        slim = [{"id": i["id"], "bbox": i.get("bbox"), "geometry": i.get("geometry"), "properties": i["properties"],
                 "assets": list(i.get("assets", {}))} for i in items]
        json.dump(slim, open(CACHE / f"sar_{name}.json", "w"))
        print(name, len(slim), flush=True)

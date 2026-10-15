import json, requests
from urllib.parse import urljoin
from shapely.geometry import shape, box
R="/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/"
A={f["properties"]["aoi_id"]:shape(f["geometry"]) for f in json.load(open(R+"examples/test_aois.geojson"))["features"]}
base="https://maxar-opendata.s3.amazonaws.com/events/"
cat=requests.get(base+"catalog.json").json()
n=0
for l in cat["links"]:
    if l["rel"]!="child": continue
    c=requests.get(urljoin(base,l["href"])).json(); n+=1
    bbs=c["extent"]["spatial"]["bbox"]
    for k,a in A.items():
        if any(box(*b).intersects(a) for b in bbs): print("HIT",l["href"],k,bbs)
    if "Canada" in l["href"] or "Utah" in l["href"] or "Detroit" in l["href"]: print(l["href"],bbs)
print(n)

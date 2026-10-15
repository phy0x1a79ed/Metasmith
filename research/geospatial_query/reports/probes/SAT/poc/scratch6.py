import json, requests, re
from pyproj import Transformer
from shapely.geometry import shape, box
from shapely.ops import transform
R="/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/"
A={f["properties"]["aoi_id"]:shape(f["geometry"]) for f in json.load(open(R+"examples/test_aois.geojson"))["features"]}
B="https://satellogic-earthview.s3.us-west-2.amazonaws.com/"
def ls(prefix,delim="/"):
    r=requests.get(B,params={"list-type":2,"prefix":prefix,"delimiter":delim}); return re.findall(r"<Prefix>(.*?)</Prefix>",r.text),re.findall(r"<Key>(.*?)</Key>",r.text)
p,k=ls("data/"); print(p,k)
p,k=ls("data/json/"); print(p[:30])
g=A["mine_us_bingham_ut"]
tr=Transformer.from_crs("EPSG:4326","EPSG:32612",always_xy=True).transform
gg=transform(tr,g)
regs=json.load(open(R+"reports/probes/A/cache/satl_zone_12N.json"))
hit=[(e,n) for e,n in regs if box(e,n-384,e+384,n).intersects(gg)]
print(len(regs),hit)
for e,n in hit[:2]:
    p,k=ls(f"data/json/zone=12N/region={e}_{n}/"); print(p)
    for d in p[:1]:
        p2,k2=ls(d); print(k2)
for pre in ["data/","data/tif/","data/tiff/","data/image/","data/images/"]:
    p,k=ls(pre); print(pre,p[:10],k[:5])

import json, requests
from shapely.geometry import shape
R="/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/"
A={f["properties"]["aoi_id"]:shape(f["geometry"]) for f in json.load(open(R+"examples/test_aois.geojson"))["features"]}
g=A["farm_sk_quarter"]
r=requests.post("https://earth-search.aws.element84.com/v1/search",json={"collections":["sentinel-2-l1c"],"bbox":list(g.bounds),"datetime":"2024-07-01T00:00:00Z/2024-08-31T23:59:59Z","limit":2,"query":{"eo:cloud_cover":{"lt":10}}})
print(r.status_code,r.text[:300])
r=r.json()
it=r["features"][0]; print(it["id"],it["properties"]);
for k,v in it["assets"].items(): print(k,v["href"])
r=requests.post("https://landsatlook.usgs.gov/stac-server/search",json={"collections":["landsat-c2l1"],"bbox":list(g.bounds),"datetime":"2024-07-01T00:00:00Z/2024-08-31T23:59:59Z","limit":2})
print(r.status_code,r.text[:300])
it=r.json()["features"][0]; print(it["id"],it["properties"]);
for k,v in it["assets"].items(): print(k,v["href"])

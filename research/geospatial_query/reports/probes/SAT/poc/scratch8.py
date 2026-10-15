import json, requests, rasterio
from affine import Affine
from shapely.geometry import Polygon, shape
R="/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/"
A={f["properties"]["aoi_id"]:shape(f["geometry"]) for f in json.load(open(R+"examples/test_aois.geojson"))["features"]}
u="https://iceye-open-data-catalog.s3.amazonaws.com/data/stripmap/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM_GRD.json"
gj=requests.get(u).json()
c,a,b,f,d,e=gj["properties"]["proj:transform"]
inv=~Affine(a,b,c,d,e,f)
g=A["farm_us_ia_story"]
pp=Polygon([inv*(x,y) for x,y in g.exterior.coords]); print(pp.bounds, pp.area)
print(list(pp.exterior.coords))
import numpy as np
cf=gj["properties"]["iceye:calibration_factor"]; print(cf, gj["properties"].get("iceye:amplitude_mapping"), {k:v for k,v in gj["properties"].items() if "calib" in k or "noise" in k or "nesz" in k or "radiom" in k})
tif=gj["properties"]  # placeholder
with rasterio.open("https://iceye-open-data-catalog.s3.amazonaws.com/data/stripmap/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM_GRD.tif") as ds:
    print(ds.width, ds.height)
    # a crop-field region inside image: central 1000x1000
    arr=ds.read(1,window=rasterio.windows.Window(13000,10000,1000,1000)).astype(float)
    v=arr[arr>0]; print(np.percentile(v,[5,25,50,75,95]), 10*np.log10((v**2*cf).mean()), np.median(10*np.log10(v**2*cf)))
    b=pp.bounds
    arr=ds.read(1,window=rasterio.windows.Window(26400,17269,160,426)).astype(float)
    v=arr[arr>0]; print(len(v),np.percentile(v,[5,25,50,75,95]), 10*np.log10((v**2*cf).mean()), np.median(10*np.log10(v**2*cf)))

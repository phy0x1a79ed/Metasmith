import rasterio, requests, json, time, numpy as np
from urllib.parse import quote
from rasterio.windows import from_bounds
from pyproj import Transformer
from shapely.geometry import shape
R="/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/"
A={f["properties"]["aoi_id"]:shape(f["geometry"]) for f in json.load(open(R+"examples/test_aois.geojson"))["features"]}
def probe(url,aoi,name):
    t=time.time()
    with rasterio.open(url) as s:
        print(name,s.profile['driver'],s.shape,s.dtypes,s.crs,s.res,s.block_shapes[:1],s.overviews(1),s.nodata,s.tags(),time.time()-t)
        tr=Transformer.from_crs("EPSG:4326",s.crs,always_xy=True)
        b=A[aoi].bounds
        xs,ys=zip(*[tr.transform(x,y) for x,y in [(b[0],b[1]),(b[0],b[3]),(b[2],b[1]),(b[2],b[3])]])
        w=from_bounds(min(xs),min(ys),max(xs),max(ys),s.transform)
        print(w)
        w=w.intersection(rasterio.windows.Window(0,0,s.width,s.height))
        print(w)
        a=s.read(1,window=w,out_shape=(min(int(w.height),1000),min(int(w.width),1000)))
        print(a.shape,a.dtype,a.min(),a.max(),a.mean(),time.time()-t)
probe("https://capella-open-data.s3.amazonaws.com/data/2021/4/8/CAPELLA_C03_SP_GEO_HH_20210408172422_20210408172446/CAPELLA_C03_SP_GEO_HH_20210408172422_20210408172446.tif","stress_oilsands_region","capella")
probe("https://iceye-open-data-catalog.s3.amazonaws.com/data/stripmap/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM_GRD.tif","farm_us_ia_story","iceye")
probe("https://umbra-open-data-catalog.s3.amazonaws.com/"+quote("sar-data/tasks/Bingham Copper Mine/498fa33d-0ae1-4f14-9f20-2f072bc3c19a/2023-07-21-17-20-53_UMBRA-06/2023-07-21-17-20-53_UMBRA-06_GEC.tif"),"mine_us_bingham_ut","umbra")

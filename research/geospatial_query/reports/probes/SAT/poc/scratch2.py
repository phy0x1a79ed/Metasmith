import rasterio, planetary_computer as pc, math, requests, time
from rasterio.windows import from_bounds
from pyproj import Transformer
b=(-106.305868,51.996387,-106.294132,52.003613)
def win(src,b):
    t=Transformer.from_crs("EPSG:4326",src.crs,always_xy=True)
    x0,y0=t.transform(b[0],b[1]);x1,y1=t.transform(b[2],b[3])
    return from_bounds(min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1),src.transform)
t=time.time()
with rasterio.open("/vsicurl/https://sentinel-s2-l1c.s3.amazonaws.com/tiles/13/U/DT/2024/8/24/0/B04.jp2") as s:
    print(s.profile['driver'],s.shape,s.dtypes,s.crs)
    w=win(s,b); a=s.read(1,window=w,boundless=False); print(a.shape,a.mean(),time.time()-t)
t=time.time()
h="https://hls2euwest.blob.core.windows.net/hls2/S30/13/U/DT/2024/08/24/HLS.S30.T13UDT.2024237T180919.v2.0/HLS.S30.T13UDT.2024237T180919.v2.0.B04.tif"
with rasterio.open(pc.sign(h)) as s:
    print(s.shape,s.dtypes,s.scales,s.offsets,s.nodata)
    w=win(s,b); a=s.read(1,window=w); print(a.shape,a.mean(),time.time()-t)
r=requests.get("https://planetarycomputer.microsoft.com/api/stac/v1/collections/hls2-s30").json()
print(r.get("summaries",{}).get("raster:bands") or r["item_assets"]["B04"])

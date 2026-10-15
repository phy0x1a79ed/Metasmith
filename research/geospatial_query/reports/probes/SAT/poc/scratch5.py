import rasterio, json
u="https://iceye-open-data-catalog.s3.amazonaws.com/data/stripmap/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM_GRD.tif"
with rasterio.open(u) as s:
    print(s.transform, s.crs, len(s.gcps[0]), s.gcps[1], s.rpcs)
    print(s.gcps[0][:3])
    print(json.dumps(json.loads(s.tags()["ICEYE_PROPERTIES"]),indent=0)[:3000])
    print({k:(v[:200]) for k,v in s.tags().items()})

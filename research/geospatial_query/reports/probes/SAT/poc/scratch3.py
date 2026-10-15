import json, requests
B="https://iceye-open-data-catalog.s3.amazonaws.com/stac-items/"
for u in ["https://iceye-open-data-catalog.s3.amazonaws.com/stac-items/ICEYE_9ZT905_20250726T064148Z_5588547_X54_SM.json",
          "https://capella-open-data.s3.us-west-2.amazonaws.com/stac/capella-open-data-by-datetime/capella-open-data-2021/capella-open-data-2021-4/capella-open-data-2021-4-8/CAPELLA_C03_SP_GEO_HH_20210408172422_20210408172446/CAPELLA_C03_SP_GEO_HH_20210408172422_20210408172446.json"]:
    r=requests.get(u); print(u,r.status_code)
    if r.status_code==200:
        o=r.json(); print(json.dumps({k:v for k,v in o.items() if k!="geometry"},indent=0)[:3500])

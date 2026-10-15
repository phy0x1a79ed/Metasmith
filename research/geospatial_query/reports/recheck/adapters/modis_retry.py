import os, sys, json, time
sys.path.append(os.getcwd())
import pipeline as P
spec = [s for s in P.ADAPTERS if s[1] == "modis_13q1"][0]
aois = {a["aoi_id"]: a for a in P.load_aois(os.environ["AOI_PATH"])}
for k in ("farm_sk_quarter", "farm_on_essex"):
    time.sleep(5)
    r = P.run_one(aois[k], spec)
    print(k, r["status"], r["reason"], r["n_features"], flush=True)

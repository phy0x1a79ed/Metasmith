"""Score every preds/*.csv against testset.csv: haversine km, median, p25, share within 1/25/200/750/2500 km."""
import csv, glob, json, os, re
import numpy as np
from math import radians, sin, cos, asin, sqrt
H = os.path.dirname(os.path.abspath(__file__))
def hav(a, b, c, d):
    a, b, c, d = map(radians, (a, b, c, d)); h = sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(h))
T = {r["id"]: r for r in csv.DictReader(open(os.path.join(H, "testset.csv")))}
B = [1, 25, 200, 750, 2500]
res = []; per = []
for f in sorted(glob.glob(os.path.join(H, "preds", "*.csv"))):
    name = os.path.basename(f)[:-4]
    errs = {}; preds = {}
    for r in csv.DictReader(open(f)):
        if r["pred_lat"] in ("", None): continue
        preds[r["id"]] = (float(r["pred_lat"]), float(r["pred_lon"]))
        t = T[r["id"]]; errs[r["id"]] = hav(float(r["pred_lat"]), float(r["pred_lon"]), float(t["true_lat"]), float(t["true_lon"]))
        per.append(dict(model=name, id=r["id"], err_km=round(errs[r["id"]], 3)))
    for sub, pred in (("all", lambda t: True), ("aoi", lambda t: not t["aoi_id"].startswith("world")), ("world", lambda t: t["aoi_id"].startswith("world")),
                      ("ground", lambda t: not re.search(r"ISS0\d\d-E|ASTER|View of Earth", t["title"])),
                      ("noflickr", lambda t: not re.search(r"\(\d{8,12}\)|Flickr", t["title"]))):
        e = np.array([v for k, v in errs.items() if pred(T[k])])
        if not len(e): continue
        ids = [k for k in errs if pred(T[k])]; rng = np.random.default_rng(0); meds = []; w750 = []
        for _ in range(500):
            sh = rng.permutation(ids)
            ee = np.array([hav(*preds[a], float(T[b]["true_lat"]), float(T[b]["true_lon"])) for a, b in zip(ids, sh)]); meds.append(np.median(ee)); w750.append((ee <= 750).mean())
        res.append(dict(model=name, subset=sub, n=len(e), null_median_km=round(float(np.median(meds)), 1), p_median_vs_shuffled=round(float((np.array(meds) <= np.median(e)).mean()), 3),
                        null_within750_pct=round(float(np.mean(w750) * 100), 1), median_km=round(float(np.median(e)), 1), p25_km=round(float(np.percentile(e, 25)), 1),
                        **{f"within_{b}km": round(float((e <= b).mean() * 100), 1) for b in B}, hit25=int((e <= 25).sum())))
with open(os.path.join(H, "scores.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, list(res[0].keys())); w.writeheader(); w.writerows(res)
with open(os.path.join(H, "errors_per_image.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, ["model", "id", "err_km"]); w.writeheader(); w.writerows(per)
for r in res: print(r)

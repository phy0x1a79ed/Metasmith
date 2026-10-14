"""Plurality vote across the local coarse models: pick the prediction with most neighbours within 300 km (ties: highest-ranked model order). Writes preds/ensemble_vote.csv."""
import csv, json, os
from math import radians, sin, cos, asin, sqrt
H = os.path.dirname(os.path.abspath(__file__))
M = ["streetclip_flatcity", "plonk_yfcc", "geoclip", "g3_align", "plonk_osv_5m", "osv5m"]
def hav(a, b, c, d):
    a, b, c, d = map(radians, (a, b, c, d)); h = sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(h))
P = {m: {r["id"]: (float(r["pred_lat"]), float(r["pred_lon"])) for r in csv.DictReader(open(os.path.join(H, "preds", m + ".csv")))} for m in M}
out = []
for r in csv.DictReader(open(os.path.join(H, "testset.csv"))):
    c = [P[m][r["id"]] for m in M]
    sc = [sum(hav(*a, *b) <= 300 for b in c) for a in c]; k = max(range(len(c)), key=lambda i: (sc[i], -i))
    out.append(dict(id=r["id"], pred_lat=c[k][0], pred_lon=c[k][1], conf=sc[k] / len(M), topk=M[k]))
with open(os.path.join(H, "preds", "ensemble_vote.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)
print("ok")

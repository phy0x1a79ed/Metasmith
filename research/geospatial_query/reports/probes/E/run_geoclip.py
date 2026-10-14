import csv, os, time, json
from geoclip import GeoCLIP
HERE = os.path.dirname(os.path.abspath(__file__))
m = GeoCLIP(from_pretrained=True); m.to("cpu")
out = []
t0 = time.time()
for r in csv.DictReader(open(os.path.join(HERE, "testset.csv"))):
    gps, prob = m.predict(os.path.join(HERE, r["image_file"]), top_k=5)
    out.append(dict(id=r["id"], pred_lat=float(gps[0][0]), pred_lon=float(gps[0][1]), conf=float(prob[0]),
                    topk=json.dumps([[float(a), float(b), float(p)] for (a, b), p in zip(gps.tolist(), prob.tolist())])))
    print(r["id"], out[-1]["pred_lat"], out[-1]["pred_lon"], round(out[-1]["conf"], 3), flush=True)
with open(os.path.join(HERE, "preds", "geoclip.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)
print("sec/img", (time.time() - t0) / len(out))

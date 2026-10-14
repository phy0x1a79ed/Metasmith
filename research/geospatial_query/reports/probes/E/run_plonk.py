"""PLONK (Dufour et al. 2025): sample N locations per image, report the densest sample (most neighbours within 200 km) as the point estimate."""
import csv, json, os, sys, time, numpy as np, torch
from PIL import Image
from plonk import PlonkPipeline
torch.set_num_threads(6)
H = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 64
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 999
pipe = PlonkPipeline(f"nicolas-dufour/{name}")
def hav(a, b):
    a = np.radians(a); b = np.radians(b)
    h = np.sin((b[:, 0] - a[0]) / 2) ** 2 + np.cos(a[0]) * np.cos(b[:, 0]) * np.sin((b[:, 1] - a[1]) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(h))
out = []; t0 = time.time()
for r in list(csv.DictReader(open(os.path.join(H, "testset.csv"))))[:limit]:
    g = torch.Generator().manual_seed(0)
    s = np.asarray(pipe(Image.open(os.path.join(H, r["image_file"])).convert("RGB"), batch_size=N)).reshape(-1, 2)
    d = np.stack([hav(p, s) for p in s]); cnt = (d < 200).sum(1); k = int(cnt.argmax())
    out.append(dict(id=r["id"], pred_lat=float(s[k, 0]), pred_lon=float(s[k, 1]), conf=float(cnt[k] / len(s)), topk=json.dumps(s[:5].tolist())))
    print(r["id"], out[-1]["pred_lat"], out[-1]["pred_lon"], out[-1]["conf"], round(time.time() - t0), flush=True)
if limit >= 50:
    with open(os.path.join(H, "preds", f"{name.lower()}.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)

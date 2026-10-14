import csv, os, sys, time, math, torch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "osv5m_src"))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "osv5m_src"))
from PIL import Image
from models.huggingface import Geolocalizer
torch.set_num_threads(6)
H = os.path.join(os.path.dirname(os.path.abspath(__file__)))
H = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
g = Geolocalizer.from_pretrained("osv5m/baseline").eval()
out = []; t0 = time.time()
for r in csv.DictReader(open(os.path.join(H, "testset.csv"))):
    x = g.transform(Image.open(os.path.join(H, r["image_file"])).convert("RGB")).unsqueeze(0)
    with torch.no_grad(): gps = g(x)[0]
    lat, lon = [math.degrees(float(v)) for v in gps]
    out.append(dict(id=r["id"], pred_lat=lat, pred_lon=lon, conf="", topk=""))
    print(r["id"], lat, lon, flush=True)
with open(os.path.join(H, "preds", "osv5m.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)
print("sec/img", (time.time() - t0) / len(out))

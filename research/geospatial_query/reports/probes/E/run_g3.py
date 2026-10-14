"""G3 geo-alignment only (Jia et al., NeurIPS 2024): public g3.pth scored against a 34k-point GeoNames city gallery.
The full G3 adds a retrieval index (38 GB) and GPT-4V prompting, which are not run here."""
import csv, glob, json, os, sys, time, numpy as np, pandas as pd, torch
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "models", "g3_src"))
from utils.G3 import G3
torch.set_num_threads(6)
ck = glob.glob(os.path.join(H, "models", "hf", "hub", "models--Jia-py--G3-checkpoint", "snapshots", "*", "g3.pth"))[0]
m = G3("cpu"); print(m.load_state_dict(torch.load(ck, map_location="cpu")), flush=True); m.eval()
cols = ["geonameid","name","asciiname","alt","lat","lon","fc","fcode","cc","cc2","a1","a2","a3","a4","pop","elev","dem","tz","mod"]
c = pd.read_csv(os.path.join(H, "labels", "cities15000.txt"), sep="\t", header=None, names=cols, keep_default_na=False)
gps = torch.tensor(c[["lat", "lon"]].values, dtype=torch.float32)
t0 = time.time()
with torch.no_grad():
    L = []
    for i in range(0, len(gps), 2048):
        e = m.location_projection_else(m.location_encoder(gps[i:i+2048])); L.append(e / e.norm(dim=-1, keepdim=True))
    L = torch.cat(L)
print("gallery", L.shape, round(time.time() - t0), flush=True)
out = []
for r in csv.DictReader(open(os.path.join(H, "testset.csv"))):
    im = Image.open(os.path.join(H, r["image_file"])).convert("RGB")
    x = m.vision_processor(images=im, return_tensors="pt")["pixel_values"]
    with torch.no_grad():
        e = m.vision_projection_else_2(m.vision_projection(m.vision_model(x)[1])); e = e / e.norm(dim=-1, keepdim=True)
        s = (e @ L.T)[0]; k = s.topk(5)
    j = int(k.indices[0])
    out.append(dict(id=r["id"], pred_lat=float(gps[j, 0]), pred_lon=float(gps[j, 1]), conf=float(k.values[0]), topk=json.dumps([[float(gps[q, 0]), float(gps[q, 1]), float(v)] for v, q in zip(k.values, k.indices)])))
    print(r["id"], c.asciiname[j], c.cc[j], round(float(k.values[0]), 3), flush=True)
with open(os.path.join(H, "preds", "g3_align.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)

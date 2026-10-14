"""Content-free control images (grey, black, noise): what does each coarse model say when there is nothing to see?"""
import json, math, os, sys
import numpy as np, torch
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__)); C = os.path.join(H, "controls")
rng = np.random.default_rng(0)
imgs = {"grey": np.full((480, 640, 3), 128, np.uint8), "black": np.zeros((480, 640, 3), np.uint8), "noise": rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)}
for k, v in imgs.items(): Image.fromarray(v).save(os.path.join(C, k + ".jpg"), quality=90)
out = {}
from geoclip import GeoCLIP
g = GeoCLIP(from_pretrained=True)
for k in imgs:
    gps, p = g.predict(os.path.join(C, k + ".jpg"), top_k=1); out.setdefault("geoclip", {})[k] = [float(gps[0][0]), float(gps[0][1]), float(p[0])]
sys.path.insert(0, os.path.join(H, "models", "osv5m_src")); os.chdir(os.path.join(H, "models", "osv5m_src"))
from models.huggingface import Geolocalizer
o = Geolocalizer.from_pretrained("osv5m/baseline").eval()
for k in imgs:
    with torch.no_grad(): gp = o(o.transform(Image.open(os.path.join(C, k + ".jpg")).convert("RGB")).unsqueeze(0))[0]
    out.setdefault("osv5m", {})[k] = [math.degrees(float(gp[0])), math.degrees(float(gp[1]))]
from plonk import PlonkPipeline
pl = PlonkPipeline("nicolas-dufour/PLONK_YFCC")
for k in imgs:
    s = np.asarray(pl(Image.open(os.path.join(C, k + ".jpg")).convert("RGB"), batch_size=64)).reshape(-1, 2)
    out.setdefault("plonk_yfcc", {})[k] = [float(np.median(s[:, 0])), float(np.median(s[:, 1])), float(s[:, 0].std())]
json.dump(out, open(os.path.join(H, "controls.json"), "w"), indent=1); print(json.dumps(out, indent=1))

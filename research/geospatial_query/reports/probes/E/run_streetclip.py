"""StreetCLIP zero-shot. Stage 1: 237 country labels. Stage 2: top-60 most populous GeoNames cities of the winning country.
Also a flat pass over all 7402 city labels. Emits three prediction files."""
import csv, json, os, time, torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
torch.set_num_threads(6)
H = os.path.dirname(os.path.abspath(__file__))
labels = json.load(open(os.path.join(H, "labels", "labels.json")))
m = CLIPModel.from_pretrained("geolocal/StreetCLIP").eval(); proc = CLIPProcessor.from_pretrained("geolocal/StreetCLIP")
def temb(texts, bs=256):
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            t = proc(text=texts[i:i+bs], return_tensors="pt", padding=True, truncation=True)
            e = m.get_text_features(**t); e = e.pooler_output if hasattr(e, "pooler_output") else e
            out.append(torch.nn.functional.normalize(e, dim=-1))
    return torch.cat(out)
t0 = time.time()
isos = list(labels); cemb = temb([f"a photo from {labels[i]['name']}." for i in isos])
cityemb = {}
flat = [(i, c) for i in isos for c in labels[i]["cities"]]
fl_emb = temb([f"a photo from {c['name']}, {labels[i]['name']}." for i, c in flat])
print("text emb done", time.time() - t0, flush=True)
scale = m.logit_scale.exp().item()
rows = {k: [] for k in ("country", "city", "flatcity")}
for r in csv.DictReader(open(os.path.join(H, "testset.csv"))):
    im = Image.open(os.path.join(H, r["image_file"])).convert("RGB")
    with torch.no_grad():
        e = m.get_image_features(**proc(images=im, return_tensors="pt")); e = e.pooler_output if hasattr(e, "pooler_output") else e
        e = torch.nn.functional.normalize(e, dim=-1)
    p = (scale * e @ cemb.T).softmax(-1)[0]; k = int(p.argmax()); iso = isos[k]
    top3 = [[isos[j], float(p[j])] for j in p.topk(3).indices.tolist()]
    rows["country"].append(dict(id=r["id"], pred_lat=labels[iso]["lat"], pred_lon=labels[iso]["lon"], conf=float(p[k]), label=labels[iso]["name"], topk=json.dumps(top3)))
    cs = labels[iso]["cities"]
    if cs:
        if iso not in cityemb: cityemb[iso] = temb([f"a photo from {c['name']}, {labels[iso]['name']}." for c in cs])
        q = (scale * e @ cityemb[iso].T).softmax(-1)[0]; j = int(q.argmax())
        rows["city"].append(dict(id=r["id"], pred_lat=cs[j]["lat"], pred_lon=cs[j]["lon"], conf=float(p[k] * q[j]), label=f'{cs[j]["name"]}, {labels[iso]["name"]}', topk=""))
    else:
        rows["city"].append(dict(rows["country"][-1]))
    q = (scale * e @ fl_emb.T).softmax(-1)[0]; j = int(q.argmax()); i2, c2 = flat[j]
    rows["flatcity"].append(dict(id=r["id"], pred_lat=c2["lat"], pred_lon=c2["lon"], conf=float(q[j]), label=f'{c2["name"]}, {labels[i2]["name"]}', topk=""))
    print(r["id"], rows["country"][-1]["label"], "|", rows["city"][-1]["label"], "|", rows["flatcity"][-1]["label"], flush=True)
for k, v in rows.items():
    with open(os.path.join(H, "preds", f"streetclip_{k}.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(v[0].keys())); w.writeheader(); w.writerows(v)
print("total sec", time.time() - t0)

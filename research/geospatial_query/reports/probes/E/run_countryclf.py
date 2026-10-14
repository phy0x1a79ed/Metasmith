"""Community 55-country GeoGuessr (Street View) image classifiers from the HF hub; predicted point = Natural Earth representative point of the country."""
import csv, json, os, sys, time, torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification
torch.set_num_threads(4)
H = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(H, "labels", "labels.json")))
byname = {v["name"].lower(): v for v in L.values()}
alias = {"united states": "United States of America", "usa": "United States of America", "uk": "United Kingdom", "south korea": "South Korea", "uae": "United Arab Emirates", "czechia": "Czechia", "russia": "Russia", "eswatini": "eSwatini", "north macedonia": "North Macedonia"}
def find(n):
    k = n.lower().strip()
    return byname.get(k) or byname.get(alias.get(k, "").lower())
for repo, tag in [("prithivMLmods/GeoGuessr-55", "clf_prithiv_siglip2"), ("Jordiett/convnextv2-geoguessr", "clf_jordiett_convnextv2"),
                  ("Simon-Kotchou/dinov3-convnext-small-geoguessr-25k-384", "clf_kotchou_dinov3"), ("marcelomoreno26/vit-base-patch-16-384-geoguessr", "clf_moreno_vit")]:
    try:
        p = AutoImageProcessor.from_pretrained(repo); m = AutoModelForImageClassification.from_pretrained(repo).eval()
    except Exception as e:
        print("FAIL", repo, repr(e)[:300]); continue
    out = []; miss = set()
    for r in csv.DictReader(open(os.path.join(H, "testset.csv"))):
        x = p(images=Image.open(os.path.join(H, r["image_file"])).convert("RGB"), return_tensors="pt")
        with torch.no_grad(): pr = m(**x).logits.softmax(-1)[0]
        k = int(pr.argmax()); lab = m.config.id2label[k]; c = find(lab)
        if c is None: miss.add(lab); out.append(dict(id=r["id"], pred_lat="", pred_lon="", conf=float(pr[k]), topk=lab)); continue
        out.append(dict(id=r["id"], pred_lat=c["lat"], pred_lon=c["lon"], conf=float(pr[k]), topk=lab))
    print(repo, "unmapped labels:", miss, flush=True)
    with open(os.path.join(H, "preds", f"{tag}.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)

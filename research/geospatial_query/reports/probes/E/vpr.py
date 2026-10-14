"""Visual place recognition refinement: Panoramax references near a centre point, DINOv2 (GeM) global retrieval,
SuperPoint+LightGlue local matching, MAGSAC fundamental-matrix inliers. Usage: vpr.py <condition: model|oracle> <id> [<id>...]"""
import csv, io, json, math, os, random, sys, time
import numpy as np, requests, torch, cv2
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from lightglue import LightGlue, SuperPoint
from lightglue.utils import numpy_image_to_torch
torch.set_num_threads(4)
H = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(H, "models", "vpr_cache"); os.makedirs(CACHE, exist_ok=True)
UA = {"User-Agent": "geoprobe/0.1 (research)"}
R_M = 3000; CELL_M = 25; MAX_POS = 300; TOPK = 20; MIN_INL = 40

def hav(a, b, c, d):
    a, b, c, d = map(math.radians, (a, b, c, d)); h = math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))

def fetch_refs(lat, lon, exclude, radius):
    feats = {}
    for lo in range(0, radius, 500):
        for attempt in range(3):
            r = requests.get("https://api.panoramax.xyz/api/search", params=dict(place_position=f"{lon},{lat}", place_distance=f"{lo}-{lo+500}", limit=1000), headers=UA, timeout=120)
            if r.status_code == 200: break
            time.sleep(5)
        for f in r.json().get("features", []):
            if f["collection"] != exclude: feats[f["id"]] = f
        time.sleep(0.5)
    cells = {}
    for f in feats.values():
        x, y = f["geometry"]["coordinates"]
        pano = f["properties"].get("pers:interior_orientation", {}).get("field_of_view") == 360
        key = (round(y * 111320 / CELL_M), round(x * 111320 * math.cos(math.radians(y)) / CELL_M), pano or round((f["properties"].get("view:azimuth") or 0) / 90) % 4)
        cells.setdefault(key, f)
    refs = list(cells.values()); random.Random(0).shuffle(refs)
    out = []
    for f in refs[:MAX_POS * 3]:
        p = f["properties"]; x, y = f["geometry"]["coordinates"]
        pano = p.get("pers:interior_orientation", {}).get("field_of_view") == 360
        out.append(dict(id=f["id"], lat=y, lon=x, pano=bool(pano), collection=f["collection"], url=f["assets"]["sd" if pano else "thumb"]["href"]))
    return out, len(feats)

def get_img(ref):
    fn = os.path.join(CACHE, ref["id"] + ".jpg")
    if not os.path.exists(fn):
        for _ in range(3):
            try:
                r = requests.get(ref["url"], headers=UA, timeout=60)
                if r.status_code == 200: open(fn, "wb").write(r.content); break
            except Exception: time.sleep(2)
    try: return np.array(Image.open(fn).convert("RGB"))
    except Exception: return None

def persp(eq, yaw, fov=75, size=512):
    h, w = eq.shape[:2]; f = 0.5 * size / math.tan(math.radians(fov) / 2)
    xs, ys = np.meshgrid(np.arange(size) - size / 2, np.arange(size) - size / 2)
    d = np.stack([xs, ys, np.full_like(xs, f)], -1).astype(np.float64)
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    dx, dz = d[..., 0] * c + d[..., 2] * s, -d[..., 0] * s + d[..., 2] * c
    lon = np.arctan2(dx, dz); lat = np.arctan2(d[..., 1], np.hypot(dx, dz))
    mx = ((lon / (2 * math.pi) + 0.5) * w).astype(np.float32); my = ((lat / math.pi + 0.5) * h).astype(np.float32)
    return cv2.remap(eq, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

proc = AutoImageProcessor.from_pretrained("facebook/dinov2-base", do_center_crop=False, size={"height": 224, "width": 224}); dino = AutoModel.from_pretrained("facebook/dinov2-base").eval()
def describe(imgs, bs=16):
    out = []
    for i in range(0, len(imgs), bs):
        x = proc(images=[Image.fromarray(a) for a in imgs[i:i+bs]], return_tensors="pt")
        with torch.no_grad(): t = dino(**x).last_hidden_state
        gem = t[:, 1:].clamp(min=1e-6).pow(3).mean(1).pow(1 / 3)
        out.append(torch.nn.functional.normalize(torch.cat([torch.nn.functional.normalize(t[:, 0], dim=-1), torch.nn.functional.normalize(gem, dim=-1)], -1), dim=-1))
    return torch.cat(out)

ext = SuperPoint(max_num_keypoints=1024).eval(); mat = LightGlue(features="superpoint").eval()
def feats(a):
    s = 640 / max(a.shape[:2]); a = cv2.resize(a, None, fx=s, fy=s) if s < 1 else a
    with torch.no_grad(): return ext.extract(numpy_image_to_torch(a))
def inliers(fq, fr):
    with torch.no_grad(): m = mat({"image0": fq, "image1": fr})
    mm = m["matches"][0]
    if len(mm) < 8: return len(mm), 0
    p0 = fq["keypoints"][0][mm[:, 0]].numpy(); p1 = fr["keypoints"][0][mm[:, 1]].numpy()
    _, mask = cv2.findFundamentalMat(p0, p1, cv2.USAC_MAGSAC, 1.5, 0.999, 10000)
    return len(mm), int(mask.sum()) if mask is not None else 0

def run(cond, qid, T, guess):
    t0 = time.time(); t = T[qid]; tl, tn = float(t["true_lat"]), float(t["true_lon"])
    if cond == "oracle":
        ang = random.Random(qid).uniform(0, 2 * math.pi); clat = tl + 800 * math.cos(ang) / 111320; clon = tn + 800 * math.sin(ang) / (111320 * math.cos(math.radians(tl)))
    else: clat, clon = guess
    own = t["source_url"].split("/collections/")[1].split("/")[0] if t["source"] == "panoramax" else ""
    res = dict(id=qid, condition=cond, centre_lat=clat, centre_lon=clon, centre_err_km=hav(clat, clon, tl, tn))
    radius = {"oracle": 1500, "model": R_M, "city": 8000}[cond]
    refs, nfeat = fetch_refs(clat, clon, own, radius); res["search_radius_m"] = radius; res["n_ref_pictures_in_disc"] = nfeat; res["n_ref_positions_used"] = len(refs[:MAX_POS * 3])
    if res["centre_err_km"] > radius / 1000:
        res["note"] = "true location is outside the reference search disc"
    with ThreadPoolExecutor(4) as ex: imgs = list(ex.map(get_img, refs))
    views, meta = [], []
    for r, a in zip(refs, imgs):
        if a is None: continue
        if r["pano"]:
            for yaw in range(0, 360, 60): views.append(persp(a, yaw)); meta.append((r, yaw))
        else: views.append(a); meta.append((r, None))
        if len(views) >= 1800: break
    res["n_views"] = len(views)
    if not views:
        res.update(note=res.get("note", "") + "; no Panoramax pictures within the search disc", best_inliers=0, accepted=False, accepted_within_1km=False, sec=round(time.time() - t0)); return res
    q = np.array(Image.open(os.path.join(H, t["image_file"])).convert("RGB"))
    dq = describe([q])[0]; dr = describe(views); sim = (dr @ dq).numpy(); order = np.argsort(-sim)
    seen, top = set(), []
    for i in order:
        if len(top) >= TOPK: break
        top.append(int(i))
    fq = feats(q); best = (-1, None, 0, 0); rows = []
    for i in top:
        r, yaw = meta[i]; nm, ni = inliers(fq, feats(views[i]))
        rows.append(dict(ref=r["id"], lat=r["lat"], lon=r["lon"], sim=float(sim[i]), matches=nm, inliers=ni, err_km=hav(r["lat"], r["lon"], tl, tn)))
        if ni > best[0]: best = (ni, r, nm, i)
    r1 = meta[int(order[0])][0]
    res["retrieval_top1_err_km"] = hav(r1["lat"], r1["lon"], tl, tn)
    res["nearest_ref_to_truth_km"] = min(hav(r["lat"], r["lon"], tl, tn) for r in refs) if refs else None
    res["best_inliers"] = best[0]
    if best[1] is not None:
        res["best_ref_err_km"] = hav(best[1]["lat"], best[1]["lon"], tl, tn); res["best_ref_id"] = best[1]["id"]
        res["accepted"] = best[0] >= MIN_INL
        res["accepted_within_1km"] = bool(best[0] >= MIN_INL and res["best_ref_err_km"] <= 1)
    res["top_candidates"] = sorted(rows, key=lambda x: -x["inliers"])[:5]; res["sec"] = round(time.time() - t0)
    return res

if __name__ == "__main__":
    cond = sys.argv[1]; T = {r["id"]: r for r in csv.DictReader(open(os.path.join(H, "testset.csv")))}
    G = {r["id"]: (float(r["pred_lat"]), float(r["pred_lon"])) for r in csv.DictReader(open(os.path.join(H, "preds", "streetclip_flatcity.csv" if cond == "city" else "geoclip.csv")))}
    os.makedirs(os.path.join(H, "vpr"), exist_ok=True)
    for qid in sys.argv[2:]:
        res = run(cond, qid, T, G[qid]); json.dump(res, open(os.path.join(H, "vpr", f"{cond}_{qid}.json"), "w"), indent=1)
        print(json.dumps({k: v for k, v in res.items() if k != "top_candidates"}), flush=True)

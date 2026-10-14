"""Append photos to testset.csv until it holds 50 (Panoramax outside the first draw)."""
import csv, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_testset as b
from PIL import Image, ImageOps

rows = list(csv.DictReader(open(os.path.join(b.HERE, "testset.csv"))))
used = [(float(r["true_lat"]), float(r["true_lon"])) for r in rows]
cands = []
for tag, bb in [("world:Vancouver", (-123.2, 49.2, -123.0, 49.3)), ("world:Ottawa", (-75.8, 45.35, -75.6, 45.45)),
                ("world:Madrid", (-3.75, 40.38, -3.65, 40.45)), ("world:Strasbourg", (7.7, 48.55, 7.8, 48.62)),
                ("world:Lille", (3.0, 50.6, 3.12, 50.66))]:
    cands += b.panoramax_candidates(bb, 1, tag, used)
for r in cands:
    if len(rows) >= 50: break
    pid = f"p{len(rows)+1:02d}"
    d = b.get(r["download_url"]); fn = os.path.join(b.ORIG, f"{pid}.jpg"); open(fn, "wb").write(d.content)
    im = ImageOps.exif_transpose(Image.open(fn)).convert("RGB")
    if im.width / im.height > 1.9: continue
    im2 = im.resize((640, round(im.height * 640 / im.width)), Image.LANCZOS)
    clean = Image.new("RGB", im2.size); clean.putdata(list(im2.get_flattened_data() if hasattr(im2, "get_flattened_data") else im2.getdata()))
    clean.save(os.path.join(b.IMG, f"{pid}.jpg"), quality=90)
    r.update(id=pid, orig_file=f"orig/{pid}.jpg", image_file=f"images/{pid}.jpg"); rows.append(r); time.sleep(0.5)
cols = list(rows[0].keys())
with open(os.path.join(b.HERE, "testset.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print(len(rows))

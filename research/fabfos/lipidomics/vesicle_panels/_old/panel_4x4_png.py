from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# This scope's own view of the project data — `.awm/data`, the DVC-pinned data
# tree on this scope's branch. It raises rather than falling back: reading
# another scope's tree silently bypasses this scope's own pins, which is the
# exact failure mode this repoint exists to remove.
def _resolve_scadc_data():
    for _p in Path(__file__).resolve().parents:
        _d = _p / ".awm" / "data"
        if _d.exists():
            return _d
    raise RuntimeError(
        f"no .awm/data found above {Path(__file__).resolve()} — fix the path "
        f"resolution here; do not restore a hardcoded cross-scope path."
    )


DATA = _resolve_scadc_data() / "scadc" / "microscopy" / "vesicle_imaging_May_22_2026"

GRID = [
    ("EPI300",  "rep1 no-tol", "exported rep 1/Epi_1"),
    ("EPI300",  "rep2 no-tol", "exported rep 2/ep2"),
    ("EPI300",  "rep1 +tol",   "exported rep 1/Epi_tol_1"),
    ("EPI300",  "rep2 +tol",   "exported rep 2/ep_tol_2"),
    ("pCC1",    "rep1 no-tol", "exported rep 1/pcc1_1"),
    ("pCC1",    "rep2 no-tol", "exported rep 2/pCC1_2"),
    ("pCC1",    "rep1 +tol",   "exported rep 1/pcc1_tol_1"),
    ("pCC1",    "rep2 +tol",   "exported rep 2/pCC1_tol_2"),
    ("clone1",  "rep1 no-tol", "exported rep 1/clon1_2"),
    ("clone1",  "rep2 no-tol", "exported rep 2/clon1_1"),
    ("clone1",  "rep1 +tol",   "exported rep 1/clon1_tol_2"),
    ("clone1",  "rep2 +tol",   "exported rep 2/clon1_tol_1"),
    ("clone2",  "rep1 no-tol", "exported rep 1/clon2_"),
    ("clone2",  "rep2 no-tol", "exported rep 2/clon2_3"),
    ("clone2",  "rep1 +tol",   "exported rep 1/clon2_tol_2"),
    ("clone2",  "rep2 +tol",   "exported rep 2/clon2_tol_3"),
]

TILE = 320
LABEL_H = 28

def first_tif(folder: Path):
    for s in sorted(p for p in folder.iterdir() if p.is_dir() and p.name.startswith("Series")):
        tifs = sorted(s.glob("*_ch00.tif"))
        if tifs:
            return tifs[0]
    return None

def norm(img):
    lo, hi = np.percentile(img, (1, 99.5))
    if hi <= lo:
        return np.zeros_like(img, dtype=np.uint8)
    return np.clip((img.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)

canvas = Image.new("RGB", (TILE * 4, (TILE + LABEL_H) * 4), "black")
draw = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
except Exception:
    font = ImageFont.load_default()

for i, (row, col, sub) in enumerate(GRID):
    r, c = i // 4, i % 4
    tif = first_tif(DATA / sub)
    if tif is None:
        continue
    arr = norm(np.array(Image.open(tif)))
    im = Image.fromarray(arr).convert("RGB").resize((TILE, TILE), Image.LANCZOS)
    y0 = r * (TILE + LABEL_H)
    x0 = c * TILE
    draw.text((x0 + 4, y0 + 4), f"{row} | {col}", fill="white", font=font)
    canvas.paste(im, (x0, y0 + LABEL_H))

out = Path(__file__).parent / "panel_4x4.png"
canvas.save(out)
print(out)

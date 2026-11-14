from pathlib import Path
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Archived under _old/, but the pixel pitch and the scale-bar rule must keep one
# home in the live vesicle_common.py — duplicating them here is exactly how the
# hardcoded 0.09 drifted away from the measured 0.0901 in the first place.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vesicle_common import background_um_per_px, sample_um_per_px, scale_bar

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

ROWS = [
    ("EPI300 rep1 no-tol", "exported rep 1/Epi_1"),
    ("EPI300 rep2 no-tol", "exported rep 2/ep2"),
    ("EPI300 rep1 +tol",   "exported rep 1/Epi_tol_1"),
    ("EPI300 rep2 +tol",   "exported rep 2/ep_tol_2"),
    ("pCC1   rep1 no-tol", "exported rep 1/pcc1_1"),
    ("pCC1   rep2 no-tol", "exported rep 2/pCC1_2"),
    ("pCC1   rep1 +tol",   "exported rep 1/pcc1_tol_1"),
    ("pCC1   rep2 +tol",   "exported rep 2/pCC1_tol_2"),
    ("clone1 rep1 no-tol", "exported rep 1/clon1_2"),
    ("clone1 rep2 no-tol", "exported rep 2/clon1_1"),
    ("clone1 rep1 +tol",   "exported rep 1/clon1_tol_2"),
    ("clone1 rep2 +tol",   "exported rep 2/clon1_tol_1"),
    ("clone2 rep1 no-tol", "exported rep 1/clon2_"),
    ("clone2 rep2 no-tol", "exported rep 2/clon2_3"),
    ("clone2 rep1 +tol",   "exported rep 1/clon2_tol_2"),
    ("clone2 rep2 +tol",   "exported rep 2/clon2_tol_3"),
    ("background rep1",    "exported rep 1/Backgroundlif"),
]

TILE = 260
LABEL_H = 22
ROW_LABEL_W = 170
SERIES_RE = re.compile(r"Series(\d+)_ch00\.tif$")

# Acquisition physics, measured from the .lif headers via fov_geometry.csv.
UM_PER_PX_STD = sample_um_per_px()      # 63x / 2x zoom — every condition series
UM_PER_PX_BG  = background_um_per_px()  # background-only zoom-out
FOV_UM = 1024 * UM_PER_PX_STD  # the FOV all condition tiles share

# Scale bar: the pixel run is chosen first and the label derived from it, so the
# printed length is exactly what is painted. See vesicle_common.scale_bar.
SCALE_PX, SCALE_LABEL = scale_bar(20.0, FOV_UM / TILE)
SCALE_THICK = 4
SCALE_PAD = 8

# Background sits at a coarser pitch than the samples. Crop the centre down to
# the same physical FOV so it renders at the same zoom as the rest — and so the
# one shared scale bar is true for it too.
BG_CROP_PX = int(round(1024 * UM_PER_PX_STD / UM_PER_PX_BG))


def series_tifs(folder: Path):
    out = []
    for s in sorted(p for p in folder.iterdir() if p.is_dir() and p.name.startswith("Series")):
        for t in s.glob("*_ch00.tif"):
            m = SERIES_RE.search(t.name)
            if m:
                out.append((int(m.group(1)), t))
    out.sort()
    return out


def load_raw(tif: Path, is_bg: bool) -> np.ndarray:
    arr = np.array(Image.open(tif))
    if is_bg:
        h, w = arr.shape
        y = (h - BG_CROP_PX) // 2
        x = (w - BG_CROP_PX) // 2
        arr = arr[y:y + BG_CROP_PX, x:x + BG_CROP_PX]
    return arr


rows_data = [(label, series_tifs(DATA / sub), "background" in label) for label, sub in ROWS]


def to_u8(arr):
    lo, hi = np.percentile(arr, (1, 99.5))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.uint8)
    return np.clip((arr.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)


loaded = [(label, [(idx, load_raw(tif, is_bg)) for idx, tif in tifs]) for label, tifs, is_bg in rows_data]
max_cols = max(len(r[1]) for r in loaded)
W = ROW_LABEL_W + TILE * max_cols
H = (TILE + LABEL_H) * len(loaded)
canvas = Image.new("RGB", (W, H), "black")
draw = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
except Exception:
    font = big = ImageFont.load_default()

for r, (label, row_imgs) in enumerate(loaded):
    y0 = r * (TILE + LABEL_H)
    draw.text((6, y0 + TILE // 2), label, fill="white", font=big)
    for c, (idx, arr) in enumerate(row_imgs):
        im = Image.fromarray(to_u8(arr)).convert("RGB").resize((TILE, TILE), Image.LANCZOS)
        x0 = ROW_LABEL_W + c * TILE
        canvas.paste(im, (x0, y0 + LABEL_H))
        draw.rectangle([x0, y0, x0 + TILE, y0 + LABEL_H], fill="black")
        draw.text((x0 + 4, y0 + 3), f"S{idx:03d}", fill="white", font=font)
        # scale bar — bottom-right of each tile. rectangle() is inclusive at
        # both ends, so the span is n-1 wide to paint exactly n columns.
        bx1 = x0 + TILE - SCALE_PAD
        bx0 = bx1 - SCALE_PX + 1
        by1 = y0 + LABEL_H + TILE - SCALE_PAD
        by0 = by1 - SCALE_THICK + 1
        draw.rectangle([bx0, by0, bx1, by1], fill="white")

# Scale-bar legend in the top-left corner.
legend = f"scale bar = {SCALE_LABEL}   |   per-tile contrast (p1, p99.5)"
draw.text((6, 4), legend, fill="white", font=font)

out = Path(__file__).parent / "raw_all.png"
canvas.save(out)
print(out, W, H)

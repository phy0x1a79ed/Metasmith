from pathlib import Path
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Archived under _old/, but the pixel pitch and the scale-bar rule keep one home
# in the live vesicle_common.py — see the note in raw_all.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vesicle_common import sample_um_per_px, scale_bar

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
    ("epi300", "r1", "notol", "exported rep 1/Epi_1"),
    ("epi300", "r2", "notol", "exported rep 2/ep2"),
    ("epi300", "r1", "tol",   "exported rep 1/Epi_tol_1"),
    ("epi300", "r2", "tol",   "exported rep 2/ep_tol_2"),
    ("pcc1",   "r1", "notol", "exported rep 1/pcc1_1"),
    ("pcc1",   "r2", "notol", "exported rep 2/pCC1_2"),
    ("pcc1",   "r1", "tol",   "exported rep 1/pcc1_tol_1"),
    ("pcc1",   "r2", "tol",   "exported rep 2/pCC1_tol_2"),
    ("clone1", "r1", "notol", "exported rep 1/clon1_2"),
    ("clone1", "r2", "notol", "exported rep 2/clon1_1"),
    ("clone1", "r1", "tol",   "exported rep 1/clon1_tol_2"),
    ("clone1", "r2", "tol",   "exported rep 2/clon1_tol_1"),
    ("clone2", "r1", "notol", "exported rep 1/clon2_"),
    ("clone2", "r2", "notol", "exported rep 2/clon2_3"),
    ("clone2", "r1", "tol",   "exported rep 1/clon2_tol_2"),
    ("clone2", "r2", "tol",   "exported rep 2/clon2_tol_3"),
]

STRAIN_LABEL = {"epi300": "EPI300", "pcc1": "PCC1", "clone1": "Clone1", "clone2": "Clone2"}
REP_LABEL    = {"r1": "R1", "r2": "R2"}
TOL_LABEL    = {"tol": "Tol+", "notol": "Tol-"}

SEED = 42
EXCLUDE = (
    {("exported rep 1/Epi_1", 12)}
    | {("exported rep 2/ep2", 6)}
    | {("exported rep 2/ep_tol_2", 6)}
    | {("exported rep 2/pCC1_2", 6)}
    | {("exported rep 2/pCC1_tol_2", 6)}
    | {("exported rep 2/clon1_1", s) for s in (1, 2, 3, 6, 7, 8, 9)}
    | {("exported rep 2/clon1_tol_1", 6)}
    | {("exported rep 2/clon2_3", 6)}
    | {("exported rep 2/clon2_tol_3", 7)}
)

TILE = 320
SUB = TILE // 2
LABEL_H = 28
SERIES_RE = re.compile(r"Series(\d+)_ch00\.tif$")

UM_PER_PX_STD = sample_um_per_px()                  # measured, not assumed
FOV_UM = 1024 * UM_PER_PX_STD                       # source FOV
CROP_PX = 256                                       # 4x linear zoom from 1024-px source
SUB_FOV_UM = CROP_PX * UM_PER_PX_STD                # per sub-tile

# Pixel run first, label derived from it — see vesicle_common.scale_bar.
SCALE_PX, SCALE_LABEL = scale_bar(2.0, SUB_FOV_UM / SUB)
SCALE_THICK = 3
SCALE_PAD = 6

SEP_COLOR = "red"
FADED_RED = (140, 40, 40)
THIN_W = 1
THICK_W = 4


def series_tifs(folder: Path):
    out = []
    for s in sorted(p for p in folder.iterdir() if p.is_dir() and p.name.startswith("Series")):
        for t in s.glob("*_ch00.tif"):
            m = SERIES_RE.search(t.name)
            if m:
                out.append((int(m.group(1)), t))
    out.sort()
    return out


def eligible(sub: str):
    return [(idx, t) for idx, t in series_tifs(DATA / sub) if (sub, idx) not in EXCLUDE]


def to_u8(arr):
    lo, hi = np.percentile(arr, (1, 99.5))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.uint8)
    return np.clip((arr.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)


pool = []
labels = []
for strain, rep, tol, sub in GRID:
    label = f"{STRAIN_LABEL[strain]} | {REP_LABEL[rep]} | {TOL_LABEL[tol]}"
    labels.append(label)
    series = eligible(sub)
    if not series:
        raise RuntimeError(f"no eligible series for cell {label} ({sub})")
    print(f"{label:22s} | {sub:32s}  →  {len(series)} series")
    pool.append(series)

rng = np.random.default_rng(SEED)
W = TILE * 4
H = (TILE + LABEL_H) * 4
canvas = Image.new("RGB", (W, H), "black")
draw = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    legend_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    scale_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
except Exception:
    font = legend_font = scale_font = ImageFont.load_default()

for i, (strain, rep, tol, sub) in enumerate(GRID):
    r, c = i // 4, i % 4
    y0 = r * (TILE + LABEL_H)
    x0 = c * TILE
    draw.rectangle([x0, y0, x0 + TILE, y0 + LABEL_H], fill="black")
    draw.text((x0 + 4, y0 + 4), labels[i], fill=SEP_COLOR, font=font)

    scale_text = SCALE_LABEL
    tl, tt, tr, tb = draw.textbbox((0, 0), scale_text, font=scale_font)
    tw = tr - tl
    th = tb - tt
    # rectangle() is inclusive at both ends: span n-1 to paint exactly n columns.
    bx1 = x0 + TILE - SCALE_PAD - 60
    bx0 = bx1 - SCALE_PX + 1
    by0 = y0 + (LABEL_H - SCALE_THICK) // 2
    by1 = by0 + SCALE_THICK - 1
    draw.rectangle([bx0, by0, bx1, by1], fill=SEP_COLOR)
    tx = bx0 - tw - 4
    ty = y0 + (LABEL_H - th) // 2 - 1
    draw.text((tx, ty), scale_text, fill=SEP_COLOR, font=scale_font)

    candidates = pool[i]
    picks = rng.integers(0, len(candidates), size=4)
    placed = []
    for k in range(4):
        sid = candidates[int(picks[k])][0]
        for _ in range(500):
            x = int(rng.integers(0, 1024 - CROP_PX + 1))
            y = int(rng.integers(0, 1024 - CROP_PX + 1))
            if all(not (s == sid and abs(x - px) < CROP_PX and abs(y - py) < CROP_PX)
                   for s, px, py in placed):
                break
        placed.append((sid, x, y))
    xs = [p[1] for p in placed]
    ys = [p[2] for p in placed]
    selected = [f"S{s:03d}@({x},{y})" for s, x, y in placed]
    print(f"  {labels[i]:22s}  {'  '.join(selected)}")

    for k in range(4):
        idx, path = candidates[int(picks[k])]
        arr = np.array(Image.open(path))
        x, y = int(xs[k]), int(ys[k])
        crop = arr[y:y + CROP_PX, x:x + CROP_PX]
        im = Image.fromarray(to_u8(crop)).convert("RGB").resize((SUB, SUB), Image.LANCZOS)
        sub_r, sub_c = k // 2, k % 2
        sx0 = x0 + sub_c * SUB
        sy0 = y0 + LABEL_H + sub_r * SUB
        canvas.paste(im, (sx0, sy0))

for i in range(16):
    r, c = i // 4, i % 4
    y0 = r * (TILE + LABEL_H)
    x0 = c * TILE
    midx = x0 + SUB
    midy = y0 + LABEL_H + SUB
    draw.line([(midx, y0 + LABEL_H), (midx, y0 + LABEL_H + TILE - 1)], fill=FADED_RED, width=THIN_W)
    draw.line([(x0, midy), (x0 + TILE - 1, midy)], fill=FADED_RED, width=THIN_W)

for c in range(1, 4):
    x = c * TILE
    draw.line([(x, 0), (x, H - 1)], fill=SEP_COLOR, width=THIN_W)
for r in range(1, 4):
    y = r * (TILE + LABEL_H)
    draw.line([(0, y), (W - 1, y)], fill=SEP_COLOR, width=THIN_W)

out = Path(__file__).parent / "panel_4x4_mosaic.png"
canvas.save(out)
print(out, W, H)

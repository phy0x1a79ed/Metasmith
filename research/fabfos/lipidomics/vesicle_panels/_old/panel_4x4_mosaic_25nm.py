from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Archived under _old/; vesicle_common still lives one level up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vesicle_common import (
    DATA, EXCLUDE, GRID, REP_LABEL, SERIES_RE, STRAIN_LABEL, TOL_LABEL,
    sample_um_per_px, scale_bar, series_tifs,
)

SEED = 42

TILE = 320
SUB = TILE // 2
LABEL_H = 28

# Measured, not assumed: read from fov_geometry.csv, which lif_geometry.py
# extracts from the .lif originals. Raises if the sample acquisitions ever
# span more than one scale.
UM_PER_PX_STD = sample_um_per_px()

# The crop is a whole number of source pixels, so the display scale it produces
# is not exactly the 25 nm/px asked for. Derive the real one from the *rounded*
# crop and use that everywhere downstream; the nominal figure survives only in
# this file's name.
TARGET_NM_PER_PX = 25.0
CROP_PX = int(round(SUB * TARGET_NM_PER_PX / 1000.0 / UM_PER_PX_STD))
SUB_FOV_UM = CROP_PX * UM_PER_PX_STD                # what a sub-tile spans
DISPLAY_UM_PER_PX = SUB_FOV_UM / SUB                # what a display pixel means

# Pixel run first, label derived from it — see vesicle_common.scale_bar.
SCALE_PX, SCALE_LABEL = scale_bar(0.1, DISPLAY_UM_PER_PX)
SCALE_THICK = 3
SCALE_PAD = 6

SEP_COLOR = "red"
FADED_RED = (140, 40, 40)
THIN_W = 1
THICK_W = 4


def eligible(sub: str):
    return [(idx, t) for idx, t in series_tifs(sub) if (sub, idx) not in EXCLUDE]


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

print(f"CROP_PX={CROP_PX}  SUB_FOV_UM={SUB_FOV_UM:.3f} µm  "
      f"display={DISPLAY_UM_PER_PX * 1000:.2f} nm/px (target {TARGET_NM_PER_PX:.0f})  "
      f"scale={SCALE_LABEL} = {SCALE_PX} px")

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
    arr_cache = {}
    placed = []
    rejects = 0
    for k in range(4):
        for attempt in range(2000):
            pick = int(rng.integers(0, len(candidates)))
            sid, path = candidates[pick]
            if sid not in arr_cache:
                a = np.array(Image.open(path))
                lo_s, hi_s = np.percentile(a, (1, 99.5))
                arr_cache[sid] = (a, float(lo_s), float(hi_s))
            arr, lo_s, hi_s = arr_cache[sid]
            x = int(rng.integers(0, 1024 - CROP_PX + 1))
            y = int(rng.integers(0, 1024 - CROP_PX + 1))
            if any(s == sid and abs(x - px) < CROP_PX and abs(y - py) < CROP_PX
                   for s, px, py, *_ in placed):
                rejects += 1
                continue
            crop = arr[y:y + CROP_PX, x:x + CROP_PX]
            if hi_s > lo_s:
                thresh = lo_s + 0.25 * (hi_s - lo_s)
                signal_frac = float((crop >= thresh).mean())
            else:
                signal_frac = 0.0
            if signal_frac >= 0.005:
                break
            rejects += 1
        placed.append((sid, x, y, arr))

    selected = [f"S{s:03d}@({x},{y})" for s, x, y, _ in placed]
    print(f"  {labels[i]:22s}  {'  '.join(selected)}   (rejected {rejects})")

    for k, (sid, x, y, arr) in enumerate(placed):
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

out = Path(__file__).parent / "panel_4x4_mosaic_25nm.png"
canvas.save(out)
print(out, W, H)

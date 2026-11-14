"""Draw what a segmentation backend found, on real fields, as SVG.

One stroked circle per detected particle at its sub-pixel centroid, at its
*measured* radius, over the field itself as a raster background. The circles come
from `segmenters.segment()`, the same call the measurement tables use, so
approving these pictures approves the numbers. Drawing them from a
re-implementation, or inflating the radius to make them easier to see, would make
that approval meaningless.

Why SVG. The check is "is that circle the right size, on a real vesicle?", which
needs zoom. In an SVG the raster background pixellates as you zoom while the
circles stay sharp vector outlines, so the comparison survives to any
magnification. `vector-effect: non-scaling-stroke` keeps the outlines a constant
width on screen at every zoom, which is what makes a 1-px-radius circle visible
at 1:1 without drawing it bigger than it is.

This module is the renderer. bakeoff.py drives it across backends and fields.
"""

import base64
import html
import io

import numpy as np
from PIL import Image

from segmenters import BACKENDS
from vesicle_common import scale_bar

# Contrast for the background raster only — it never touches what is measured.
DISPLAY_PCTL = (1, 99.5)

HEADER_H = 46          # image-pixel units reserved above the field for the caption

# A stroke thin enough to read the pixel under it. `non-scaling-stroke` makes
# this a fraction of a *screen* pixel at 1:1 and a constant hairline at any zoom,
# which is the point: the circle must not hide the spot it is measuring.
STROKE_W = 0.5
LEGEND_STROKE_W = 0.7

STROKE_PLAIN = "#00e5ff"   # an ordinary, cleanly sized particle
STROKE_FLAG = "#ffd400"    # backend flagged it: deblended, merged, or sharing pixels
STROKE_CAPPED = "#ff4d4d"  # measurement truncated — this radius is a lower bound

BAR_TARGET_UM = 10.0
BAR_THICK = 4
BAR_PAD = 14


def to_u8(arr: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(arr, DISPLAY_PCTL)
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.uint8)
    return np.clip((arr.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)


def png_data_uri(arr_u8: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(arr_u8, mode="L").save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _classify(row: dict) -> str:
    """Colour by whatever the backend itself flagged, without inventing a flag
    for a backend that has no equivalent — an absent key means "not reported",
    which is not the same as "clean"."""
    if row.get("region_capped"):
        return STROKE_CAPPED
    if row.get("n_centers_in_region", 1) > 1 or row.get("deblended") or row.get("merged"):
        return STROKE_FLAG
    return STROKE_PLAIN


def build_svg(arr: np.ndarray, seg, um_per_px: float, caption: str) -> str:
    """One field, one backend. `seg` is a segmenters.Segmentation."""
    h, w = arr.shape
    bar_px, bar_label = scale_bar(BAR_TARGET_UM, um_per_px)
    be = BACKENDS[seg.backend]

    circles = []
    for r in seg.rows:
        # Centroids index pixel centres from 0; SVG puts the centre of pixel i at
        # i+0.5, so the half-pixel shift is real, not cosmetic.
        circles.append(
            f'<circle cx="{r["x_px"] + 0.5:.2f}" cy="{r["y_px"] + 0.5:.2f}" '
            f'r="{r["radius_px"]:.2f}" stroke="{_classify(r)}"/>'
        )

    n_flag = sum(1 for r in seg.rows if _classify(r) == STROKE_FLAG)
    n_cap = sum(1 for r in seg.rows if _classify(r) == STROKE_CAPPED)
    legend = [
        (STROKE_PLAIN, "particle, drawn at its measured radius"),
        (STROKE_FLAG, f"backend flagged it: deblended / merged / shared ({n_flag})"),
        (STROKE_CAPPED, f"measurement truncated, radius is a lower bound ({n_cap})"),
    ]
    legend_svg = "".join(
        f'<circle cx="26" cy="{h - 76 + 24*i}" r="7" fill="none" stroke="{c}" '
        f'stroke-width="{LEGEND_STROKE_W}"/>'
        f'<text x="40" y="{h - 71 + 24*i}" fill="#eee" font-size="13">{html.escape(t)}</text>'
        for i, (c, t) in enumerate(legend)
    )

    bx1, by1 = w - BAR_PAD, h - BAR_PAD
    bx0, by0 = bx1 - bar_px, by1 - BAR_THICK
    radii = np.array([r["radius_nm"] for r in seg.rows] or [0.0], dtype=float)
    stats = (f"{len(seg.rows)} particles of {seg.n_features} detections — "
             f"radius median {np.median(radii):.0f} nm, p90 "
             f"{np.percentile(radii, 90):.0f} nm, max {radii.max():.0f} nm")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h + HEADER_H}"
     viewBox="0 0 {w} {h + HEADER_H}" font-family="DejaVu Sans, sans-serif">
  <rect width="{w}" height="{h + HEADER_H}" fill="#111"/>
  <text x="10" y="19" fill="#eee" font-size="15">{html.escape(caption)}</text>
  <text x="10" y="37" fill="#aaa" font-size="13">{html.escape(seg.backend)} \
{html.escape(be.knob_name)}={seg.knob:g} — {stats}</text>
  <g transform="translate(0,{HEADER_H})">
    <image href="{png_data_uri(to_u8(arr))}" x="0" y="0" width="{w}" height="{h}"
           image-rendering="pixelated"/>
    <g fill="none" stroke-width="{STROKE_W}" vector-effect="non-scaling-stroke">
      {"".join(circles)}
    </g>
    <rect x="{bx0}" y="{by0}" width="{bar_px}" height="{BAR_THICK}" fill="#fff"/>
    <text x="{bx1}" y="{by0 - 6}" fill="#fff" font-size="15" text-anchor="end">{bar_label}</text>
    {legend_svg}
  </g>
</svg>
"""

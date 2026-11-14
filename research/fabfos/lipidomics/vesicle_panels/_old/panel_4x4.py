from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image

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

# (row_label, col_label, folder)
GRID = [
    ("EPI300",   "rep1 no-tol", "exported rep 1/Epi_1"),
    ("EPI300",   "rep2 no-tol", "exported rep 2/ep2"),
    ("EPI300",   "rep1 +tol",   "exported rep 1/Epi_tol_1"),
    ("EPI300",   "rep2 +tol",   "exported rep 2/ep_tol_2"),
    ("pCC1",     "rep1 no-tol", "exported rep 1/pcc1_1"),
    ("pCC1",     "rep2 no-tol", "exported rep 2/pCC1_2"),
    ("pCC1",     "rep1 +tol",   "exported rep 1/pcc1_tol_1"),
    ("pCC1",     "rep2 +tol",   "exported rep 2/pCC1_tol_2"),
    ("clone1",   "rep1 no-tol", "exported rep 1/clon1_2"),
    ("clone1",   "rep2 no-tol", "exported rep 2/clon1_1"),
    ("clone1",   "rep1 +tol",   "exported rep 1/clon1_tol_2"),
    ("clone1",   "rep2 +tol",   "exported rep 2/clon1_tol_1"),
    ("clone2",   "rep1 no-tol", "exported rep 1/clon2_"),
    ("clone2",   "rep2 no-tol", "exported rep 2/clon2_3"),
    ("clone2",   "rep1 +tol",   "exported rep 1/clon2_tol_2"),
    ("clone2",   "rep2 +tol",   "exported rep 2/clon2_tol_3"),
]

def first_tif(folder: Path) -> Path | None:
    series = sorted(p for p in folder.iterdir() if p.is_dir() and p.name.startswith("Series"))
    for s in series:
        tifs = sorted(s.glob("*_ch00.tif"))
        if tifs:
            return tifs[0]
    return None

titles = [f"{row}<br>{col}" for row, col, _ in GRID]
fig = make_subplots(rows=4, cols=4, subplot_titles=titles,
                    horizontal_spacing=0.01, vertical_spacing=0.05)

for i, (row, col, sub) in enumerate(GRID):
    r, c = i // 4 + 1, i % 4 + 1
    tif = first_tif(DATA / sub)
    if tif is None:
        continue
    img = np.array(Image.open(tif))
    # normalize to 0-255 for display contrast
    lo, hi = np.percentile(img, (1, 99.5))
    if hi > lo:
        img = np.clip((img.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)
    fig.add_trace(
        go.Heatmap(z=img[::-1], colorscale="gray", showscale=False, hoverinfo="skip"),
        row=r, col=c,
    )
    fig.update_xaxes(visible=False, row=r, col=c)
    fig.update_yaxes(visible=False, row=r, col=c, scaleanchor=f"x{i+1 if i else ''}", scaleratio=1)

fig.update_layout(
    height=1100, width=1100,
    title_text="Vesicle imaging — May 22 2026 — first Series per condition",
    plot_bgcolor="black", paper_bgcolor="black", font_color="white",
    margin=dict(l=20, r=20, t=80, b=20),
)
for ann in fig.layout.annotations:
    ann.font.size = 11
    ann.font.color = "white"

out = Path(__file__).parent / "panel_4x4.html"
fig.write_html(str(out), include_plotlyjs="cdn")
print(out)

"""Sum-intensity bar chart across strains x toluene.

For each condition folder, computes the total pixel intensity of every
Series*_ch00.tif (one field of view per Series), then takes the mean across
fields of view to get a per-replicate mean. Finally averages across the two
biological replicates and plots a grouped bar chart with rep points overlaid.
"""

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from PIL import Image

import sys
# Archived under _old/: vesicle_common lives one level up, and this script's
# own tables and renders belong beside it here, not in the live directory
# where the current chain writes files under the same names.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
OLD = Path(__file__).resolve().parent

from vesicle_common import DATA

OUT_DIR = Path(__file__).parent

# (strain, toluene, rep, folder)
CONDITIONS = [
    ("EPI300", "no tol", "rep1", "exported rep 1/Epi_1"),
    ("EPI300", "no tol", "rep2", "exported rep 2/ep2"),
    ("EPI300", "+tol",   "rep1", "exported rep 1/Epi_tol_1"),
    ("EPI300", "+tol",   "rep2", "exported rep 2/ep_tol_2"),
    ("pCC1",   "no tol", "rep1", "exported rep 1/pcc1_1"),
    ("pCC1",   "no tol", "rep2", "exported rep 2/pCC1_2"),
    ("pCC1",   "+tol",   "rep1", "exported rep 1/pcc1_tol_1"),
    ("pCC1",   "+tol",   "rep2", "exported rep 2/pCC1_tol_2"),
    ("clone1", "no tol", "rep1", "exported rep 1/clon1_2"),
    ("clone1", "no tol", "rep2", "exported rep 2/clon1_1"),
    ("clone1", "+tol",   "rep1", "exported rep 1/clon1_tol_2"),
    ("clone1", "+tol",   "rep2", "exported rep 2/clon1_tol_1"),
    ("clone2", "no tol", "rep1", "exported rep 1/clon2_"),
    ("clone2", "no tol", "rep2", "exported rep 2/clon2_3"),
    ("clone2", "+tol",   "rep1", "exported rep 1/clon2_tol_2"),
    ("clone2", "+tol",   "rep2", "exported rep 2/clon2_tol_3"),
]

STRAINS = ["EPI300", "pCC1", "clone1", "clone2"]
TOL_LEVELS = ["no tol", "+tol"]


def series_sums(folder: Path) -> list[float]:
    sums = []
    for s in sorted(p for p in folder.iterdir() if p.is_dir() and p.name.startswith("Series")):
        for tif in sorted(s.glob("*_ch00.tif")):
            img = np.array(Image.open(tif), dtype=np.float64)
            sums.append(float(img.sum()))
    return sums


# Collect per-replicate mean sum-intensity (mean across fields of view).
rep_means: dict[tuple[str, str], list[float]] = {}
fov_counts: dict[tuple[str, str, str], int] = {}
for strain, tol, rep, sub in CONDITIONS:
    sums = series_sums(DATA / sub)
    fov_counts[(strain, tol, rep)] = len(sums)
    mean_sum = float(np.mean(sums)) if sums else float("nan")
    rep_means.setdefault((strain, tol), []).append(mean_sum)
    print(f"  {strain:7s} {tol:7s} {rep}  n_fov={len(sums)}  mean_sum={mean_sum:.3g}  ({sub})")

# Aggregate across replicates: mean and (n=2) std for error bars.
fig = go.Figure()
colors = {"no tol": "#5b8def", "+tol": "#e07a5f"}

for tol in TOL_LEVELS:
    means = []
    stds = []
    rep_points = {"rep1": [], "rep2": []}
    for strain in STRAINS:
        vals = rep_means[(strain, tol)]
        means.append(np.mean(vals))
        stds.append(np.std(vals, ddof=0))
        for rep, v in zip(["rep1", "rep2"], vals):
            rep_points[rep].append(v)

    fig.add_trace(go.Bar(
        name=tol,
        x=list(range(len(STRAINS))),
        y=means,
        error_y=dict(type="data", array=stds, visible=True, color="black", thickness=1.2, width=6),
        marker_color=colors[tol],
        opacity=0.85,
    ))

# Overlay individual replicate points, x-aligned with their bar group.
# With 2 grouped bars and bargap=0.25, bar centers sit at strain_index ± 0.2.
BAR_OFFSET = {"no tol": -0.2, "+tol": 0.2}
for tol in TOL_LEVELS:
    xs, ys = [], []
    for si, strain in enumerate(STRAINS):
        for v in rep_means[(strain, tol)]:
            xs.append(si + BAR_OFFSET[tol])
            ys.append(v)
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers",
        marker=dict(color="black", size=7, symbol="circle-open", line=dict(width=1.5)),
        name=f"{tol} reps", showlegend=False,
    ))

fig.update_xaxes(
    tickmode="array",
    tickvals=list(range(len(STRAINS))),
    ticktext=STRAINS,
)

fig.update_layout(
    barmode="group",
    title="Sum intensity per image (mean of FOVs, then mean of 2 reps)",
    xaxis_title="strain",
    yaxis_title="sum pixel intensity (a.u.)",
    legend_title="toluene",
    width=820, height=520,
    template="plotly_white",
    bargap=0.25,
)

html = OUT_DIR / "sum_intensity_bar.html"
png = OUT_DIR / "sum_intensity_bar.png"
fig.write_html(str(html), include_plotlyjs="cdn")
try:
    fig.write_image(str(png), scale=2)
    print(f"\nwrote {png}")
except Exception as e:
    print(f"\n(png export skipped: {e})")
print(f"wrote {html}")

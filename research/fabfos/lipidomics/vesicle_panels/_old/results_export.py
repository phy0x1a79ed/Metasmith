"""Export the headline density table and bar chart into the acquisition itself.

Everything else in this directory writes beside the code, where a developer
looks. This writes into
`data/fabfos/runs/scadc_microscopy/vesicle_imaging_May_22_2026/results/`, where someone
opening the imaging dataset looks — a standalone table, one figure, and a README
that explains them without reference to this repo.

Nothing is recomputed here. The source is vesicle_density.csv; this selects the
primary field-of-view set, relabels for human readers, and renders.

On writing into a DVC chunk
---------------------------
The destination is inside a DVC-tracked directory. Once the chunk is re-added,
these files become read-only hardlinks into the workspace-shared cache: writing
through one would corrupt that cached object for every other scope and every
commit that pins it. Every output is therefore unlinked before it is opened, so
a rerun replaces the link rather than editing through it.
"""

import csv
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

import sys
# Archived under _old/: vesicle_common lives one level up, and this script's
# own tables and renders belong beside it here, not in the live directory
# where the current chain writes files under the same names.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
OLD = Path(__file__).resolve().parent

from vesicle_common import DATA, PANELS, STRAIN_LABEL, STRAINS, TOL_LEVELS

RESULTS = DATA / "results"
SRC = OLD / "vesicle_density.csv"
FOV_SET = "nonempty"

TREATMENT = {"notol": "-toluene", "tol": "+toluene"}
COLORS = {"notol": "#5b8def", "tol": "#e07a5f"}
REPS = ("r1", "r2")

# Grouped bars split (1 - BARGAP) between the two treatments, so a bar's centre
# sits this far off the strain's tick. Derived, not eyeballed — the replicate
# markers have to land on their own bar.
BARGAP = 0.25
BAR_OFFSET = (1.0 - BARGAP) / 4.0

COLUMNS = ["strain", "treatment", "replicate", "n_fov", "mean_per_1000um2",
           "sd_per_1000um2", "od600", "density_per_od"]


def fresh(path: Path) -> Path:
    """Break the hardlink before writing. See the module docstring."""
    if path.exists():
        path.unlink()
    return path


def read_commented_csv(path: Path) -> pd.DataFrame:
    with path.open() as fh:
        return pd.read_csv(StringIO("".join(l for l in fh if not l.startswith("#"))))


def write_table(d: pd.DataFrame) -> list[dict]:
    rows = []
    for strain in STRAINS:
        for tol in TOL_LEVELS:
            for rep in REPS:
                g = d[(d.strain == strain) & (d.tol == tol) & (d.rep == rep)]
                if len(g) != 1:
                    raise RuntimeError(f"expected one row for {strain}/{tol}/{rep}, got {len(g)}")
                r = g.iloc[0]
                rows.append({
                    "strain": STRAIN_LABEL[strain],
                    "treatment": TREATMENT[tol],
                    "replicate": rep.upper(),
                    "n_fov": int(r.n_fov),
                    "mean_per_1000um2": round(float(r.mean_per_1000um2), 2),
                    "sd_per_1000um2": round(float(r.sd_per_1000um2), 2),
                    "od600": float(r.od600),
                    "density_per_od": round(float(r.density_per_od), 2),
                })

    out = fresh(RESULTS / "vesicle_density.csv")
    with out.open("w", newline="") as fh:
        fh.write(TABLE_HEADER)
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.name}  ({len(rows)} rows)")
    return rows


def write_figure(d: pd.DataFrame) -> None:
    fig = go.Figure()
    for tol in TOL_LEVELS:
        means, px, py = [], [], []
        for si, strain in enumerate(STRAINS):
            g = d[(d.strain == strain) & (d.tol == tol)]
            means.append(float(g["density_per_od"].mean()))
            offset = -BAR_OFFSET if tol == "notol" else BAR_OFFSET
            for v in g["density_per_od"]:
                px.append(si + offset)
                py.append(float(v))
        fig.add_trace(go.Bar(
            name=TREATMENT[tol], x=list(range(len(STRAINS))), y=means,
            marker_color=COLORS[tol], opacity=0.85, legendgroup=tol,
        ))
        fig.add_trace(go.Scatter(
            x=px, y=py, mode="markers", showlegend=False, legendgroup=tol,
            name=f"{TREATMENT[tol]} replicates",
            marker=dict(color="black", size=9, symbol="circle-open",
                        line=dict(width=1.6)),
        ))

    fig.update_xaxes(tickmode="array", tickvals=list(range(len(STRAINS))),
                     ticktext=[STRAIN_LABEL[s] for s in STRAINS])
    fig.update_yaxes(title_text="particles per 1000 µm² per OD600")
    fig.update_layout(
        barmode="group", bargap=BARGAP, template="plotly_white",
        width=860, height=600, legend_title="treatment",
        title=("Vesicle density normalized to culture OD600<br>"
               "<sup>22 May 2026 GUV imaging — threshold 10/255, blank fields "
               "dropped</sup>"),
        margin=dict(t=110, b=200),
    )
    # Line breaks are placed by hand: the annotation does not wrap, and at this
    # width a line much past ~95 characters runs off the right edge of the plot.
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-52,
        showarrow=False, align="left", font=dict(size=11, color="#666"),
        text=("Bars are the mean of 2 biological replicates; open circles are the "
              "replicates themselves.<br>n=2, so no significance test is warranted. "
              "<b>OD600 is not from the imaging day</b> — it is the<br>lipidomics "
              "culture set (6 d post-challenge), and the replicate index is assumed "
              "to correspond.<br><b>PCC1 +toluene is the one to distrust</b>: its "
              "OD600 (0.099, 0.103) is the lowest recorded, so<br>normalizing "
              "divides by a very small number and lifts it from third-highest raw "
              "to highest<br>normalized. That gap is the denominator, not the "
              "imaging."),
    )

    html = fresh(RESULTS / "vesicle_density_per_od.html")
    fig.write_html(str(html), include_plotlyjs="cdn")
    png = fresh(RESULTS / "vesicle_density_per_od.png")
    fig.write_image(str(png), scale=2)
    print(f"wrote {png.name} + {html.name}")


TABLE_HEADER = (
    "# Vesicle particle density from the 22 May 2026 GUV imaging of this\n"
    "# acquisition: four strains x +/- toluene x 2 biological replicates.\n"
    "#\n"
    "# mean_per_1000um2  particles detected per 1000 um^2 of imaged area, averaged\n"
    "#                   over that replicate's fields of view. Each field is a\n"
    "#                   measured constant 8512.26 um^2 (1024x1024 px at\n"
    "#                   0.0901 um/px, HC PL APO CS2 63x/1.40 OIL, zoom 2).\n"
    "# sd_per_1000um2    spread across those fields, NOT across replicates.\n"
    "# density_per_od    mean_per_1000um2 / od600.\n"
    "#\n"
    "# Particles are 8-connected components at or above a fixed absolute 8-bit\n"
    "# level of 10/255, with a minimum area of 0.02 um^2. Background in these\n"
    "# images is exactly zero, so the threshold is an absolute signal level rather\n"
    "# than a multiple of background; per-image Otsu was tested and rejected as\n"
    "# unstable (it returns thresholds an order of magnitude apart on adjacent\n"
    "# fields of one sample).\n"
    "#\n"
    "# n_fov excludes the 11 blank acquisitions -- each rep-2 acquisition ends\n"
    "# with a frame containing zero particles at every threshold.\n"
    "#\n"
    "# CAVEAT: the OD600 values are NOT from the imaging day. They are the\n"
    "# lipidomics culture set, measured 6 d post-challenge and forwarded\n"
    "# 2026-07-08, against imaging dated 2026-05-22, and their replicate index is\n"
    "# assumed to correspond to the imaging replicate index. Treat density_per_od\n"
    "# as a cross-experiment estimate, not a measured ratio.\n"
    "# n=2 biological replicates throughout -- no significance test is warranted.\n"
    "#\n"
    "# Written by research/fabfos/lipidomics/vesicle_panels/results_export.py in the scadc/lipidomics\n"
    "# code repo; see results/README.md.\n"
)

README = """# Results — 22 May 2026 GUV imaging

Quantification of this acquisition: how many vesicle particles each strain
produced per unit imaged area, normalized to culture density.

| file | what it is |
|---|---|
| `vesicle_density.csv` | 4 strains × ±toluene × 2 replicates, 16 rows |
| `vesicle_density_per_od.png` / `.html` | the same numbers as a bar chart, replicates drawn as points |

The CSV's comment header states the threshold rule, the field area, and the OD
caveat. Read it before quoting a number.

## How these were made

`research/fabfos/lipidomics/vesicle_panels/` in the `scadc/lipidomics` code repo, four steps ending in
`results_export.py`, all under the `imaging` conda env. Field-of-view geometry is
read from the Leica `.lif` originals in `rep1/` and `rep2/` and cross-checked
against the exported `MetaData/*_Properties.xml`; particles are 8-connected
components at a fixed absolute threshold of 10/255.

## Three limits on these numbers

**n = 2.** Every bar is two biological replicates and both are plotted. Nothing
here supports a significance test and none was computed.

**The OD600 is cross-experiment.** There is no OD record from the imaging day, so
the normalization uses the lipidomics culture set. PCC1 +toluene is the value
distorted most — its OD is the lowest in that table, so dividing by it moves PCC1
from third-highest raw density to highest normalized.

**One threshold cannot show whether a ranking is real.** Under toluene the
ordering PCC1 > Clone1 > EPI300 > Clone2 holds across thresholds 3–40. Without
toluene it does not: PCC1, Clone2 and Clone1 exchange places between thresholds,
and only "EPI300 lowest" survives. The figure is a single threshold and cannot
show this — see `threshold_sweep.csv` in the code repo before quoting a
no-toluene ordering.

## Not exported here

The code repo also holds the per-particle table (34,430 particles, with apparent
sizes), the per-field table, the full threshold sweep, and a second field-of-view
set that additionally drops four non-empty fields rejected by eye when the image
mosaic was built. That alternative set moves exactly one condition
(Clone1/R2/−toluene, 128.7 → 69.5 particles per 1000 µm² per OD) and leaves the
strain ranking unchanged.
"""


def main() -> int:
    if not RESULTS.exists():
        RESULTS.mkdir(parents=True)
    if not SRC.exists():
        raise RuntimeError(f"{SRC} missing — run density_normalize.py first")

    d = read_commented_csv(SRC)
    d = d[d.fov_set == FOV_SET]
    if len(d) != 16:
        raise RuntimeError(f"expected 16 rows for fov_set={FOV_SET}, got {len(d)}")

    write_table(d)
    write_figure(d)

    readme = fresh(RESULTS / "README.md")
    readme.write_text(README)
    print(f"wrote {readme.name}")
    print(f"\nin {RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

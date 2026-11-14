"""T5 — the three figures: density, particle size distribution, threshold sweep.

Reads the tables written by particle_measure.py and density_normalize.py and
renders beside this file, matching the idiom of sum_intensity_bar.py. Every mean
carries its two replicate points: n=2, and a bar alone would hide that.
"""

import gzip
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sys
# Archived under _old/: vesicle_common lives one level up, and this script's
# own tables and renders belong beside it here, not in the live directory
# where the current chain writes files under the same names.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
OLD = Path(__file__).resolve().parent

from vesicle_common import EXCLUDE, PANELS, STRAIN_LABEL, STRAINS, TOL_LEVELS

PRIMARY_SET = "nonempty"
TOL_LABEL = {"notol": "no toluene", "tol": "+toluene"}
COLORS = {"notol": "#5b8def", "tol": "#e07a5f"}
SWEEP_ORDER = [3, 5, 10, 20, 40, 80]


def rd(path: Path) -> pd.DataFrame:
    opener = (lambda: gzip.open(path, "rt")) if path.suffix == ".gz" else path.open
    with opener() as fh:
        return pd.read_csv(StringIO("".join(l for l in fh if not l.startswith("#"))))


def save(fig, stem: str) -> None:
    fig.write_html(str(OLD / f"{stem}.html"), include_plotlyjs="cdn")
    try:
        fig.write_image(str(OLD / f"{stem}.png"), scale=2)
        print(f"  wrote {stem}.png + .html")
    except Exception as e:
        print(f"  wrote {stem}.html (png export skipped: {e})")


def grouped_bars(fig, dens, value_col, row, col, showlegend):
    """Bars = mean of the two replicates; open circles = the replicates."""
    for tol in TOL_LEVELS:
        means, points_x, points_y = [], [], []
        for si, strain in enumerate(STRAINS):
            g = dens[(dens.strain == strain) & (dens.tol == tol)]
            means.append(float(g[value_col].mean()))
            offset = -0.2 if tol == "notol" else 0.2
            for v in g[value_col]:
                points_x.append(si + offset)
                points_y.append(float(v))
        fig.add_trace(go.Bar(
            name=TOL_LABEL[tol], x=list(range(len(STRAINS))), y=means,
            marker_color=COLORS[tol], opacity=0.85, showlegend=showlegend,
            legendgroup=tol,
        ), row=row, col=col)
        fig.add_trace(go.Scatter(
            x=points_x, y=points_y, mode="markers",
            marker=dict(color="black", size=8, symbol="circle-open",
                        line=dict(width=1.6)),
            showlegend=False, legendgroup=tol, name=f"{TOL_LABEL[tol]} reps",
        ), row=row, col=col)


def density_figure(dens: pd.DataFrame) -> None:
    d = dens[dens.fov_set == PRIMARY_SET]
    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.12,
        subplot_titles=("Particle density",
                        "Density normalized to culture OD600"),
    )
    grouped_bars(fig, d, "mean_per_1000um2", 1, 1, showlegend=True)
    grouped_bars(fig, d, "density_per_od", 1, 2, showlegend=False)

    for c in (1, 2):
        fig.update_xaxes(tickmode="array", tickvals=list(range(len(STRAINS))),
                         ticktext=[STRAIN_LABEL[s] for s in STRAINS],
                         row=1, col=c)
    fig.update_yaxes(title_text="particles per 1000 µm²", row=1, col=1)
    fig.update_yaxes(title_text="particles per 1000 µm² per OD600", row=1, col=2)
    fig.update_layout(
        barmode="group", bargap=0.25, template="plotly_white",
        width=1000, height=580, legend_title="treatment",
        title=("Vesicle particle density, 22 May 2026 GUV imaging "
               "(threshold 10/255, blank fields dropped)"),
        margin=dict(t=110, b=185),
    )
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-58,
        showarrow=False, align="left", font=dict(size=11, color="#666"),
        text=("Bars are the mean of 2 biological replicates; open circles are the "
              "replicates themselves. Area is a measured constant 8512.26 µm² per "
              "field.<br><b>OD600 is not from the imaging day</b> — it is the "
              "lipidomics culture set (6 d post-challenge, fwd 2026-07-08) against "
              "imaging dated 2026-05-22, and the replicate<br>index is assumed to "
              "correspond. Read the right panel as a cross-experiment estimate."
              "<br><b>PCC1 +toluene is the one to distrust</b>: its OD600 (0.099, "
              "0.103) is the lowest in the table, so normalizing divides by a very "
              "small number and lifts it from<br>third-highest raw to highest "
              "normalized. That gap is the denominator, not the imaging."),
    )
    save(fig, "vesicle_density")


def size_figure(particles: pd.DataFrame) -> None:
    """Cumulative distribution, log size axis.

    An ECDF rather than a violin: the distribution is a narrow bulk at the
    resolution limit with a long heavy tail, which a KDE either flattens or
    clips, and plotly's violin does not transform its density onto a log axis at
    all. On an ECDF the bulk, the median and the tail are all readable, and
    "strain A has more big particles" is a visible vertical gap.
    """
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.07,
                        subplot_titles=(TOL_LABEL["notol"], TOL_LABEL["tol"]))
    palette = {"epi300": "#888888", "pcc1": "#5b8def",
               "clone1": "#2a9d8f", "clone2": "#e07a5f"}

    for ci, tol in enumerate(TOL_LEVELS, start=1):
        for strain in STRAINS:
            d = np.sort(particles[(particles.strain == strain)
                                  & (particles.tol == tol)]["equiv_diam_nm"].values)
            if not len(d):
                continue
            y = np.arange(1, len(d) + 1) / len(d)
            fig.add_trace(go.Scatter(
                x=d, y=y, mode="lines", name=STRAIN_LABEL[strain],
                legendgroup=strain, showlegend=(ci == 1),
                line=dict(color=palette[strain], width=2),
                hovertemplate=f"{STRAIN_LABEL[strain]}<br>%{{x:.0f}} nm<br>"
                              "%{y:.1%} of particles smaller<extra></extra>",
            ), row=1, col=ci)
        fig.add_vline(x=250, line_dash="dot", line_color="#999", row=1, col=ci)
        fig.update_xaxes(title_text="equivalent circular diameter (nm)", type="log",
                         tickvals=[200, 300, 500, 1000, 2000, 4000],
                         ticktext=["200", "300", "500", "1000", "2000", "4000"],
                         row=1, col=ci)
    fig.update_yaxes(title_text="cumulative fraction of particles", row=1, col=1,
                     tickformat=".0%")
    fig.add_annotation(x=np.log10(250), y=0.04, xref="x", yref="y", text="≈250 nm<br>resolution limit",
                       showarrow=False, xanchor="left", xshift=6,
                       font=dict(size=10, color="#666"))
    fig.update_layout(
        template="plotly_white", width=1000, height=620, legend_title="strain",
        title="Apparent particle size distribution (threshold 10/255)",
        margin=dict(t=90, b=150),
    )
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-58,
        showarrow=False, align="left", font=dict(size=11, color="#666"),
        text=("Most of the distribution sits at or below the diffraction limit, so "
              "these are point-spread-function-limited spot sizes, <b>not physical "
              "vesicle diameters</b>.<br>The upper tail is the informative part: it "
              "is where merged or clumped particles appear."),
    )
    save(fig, "particle_size_dist")


def sweep_figure(sweep: pd.DataFrame, fov: pd.DataFrame, dens: pd.DataFrame) -> None:
    blanks = set(zip(fov[fov.n_particles == 0].exported_dir,
                     fov[fov.n_particles == 0].series))
    s = sweep[[(a, b) not in blanks
               for a, b in zip(sweep.exported_dir, sweep.series)]]

    od = {(r.strain, r.tol, r.rep): r.od600
          for r in dens[dens.fov_set == PRIMARY_SET].itertuples()}

    fig = make_subplots(rows=1, cols=2, shared_yaxes=False, horizontal_spacing=0.12,
                        subplot_titles=(TOL_LABEL["notol"], TOL_LABEL["tol"]))
    palette = {"epi300": "#888888", "pcc1": "#5b8def",
               "clone1": "#2a9d8f", "clone2": "#e07a5f"}

    for ci, tol in enumerate(TOL_LEVELS, start=1):
        for strain in STRAINS:
            ys = []
            for thr in SWEEP_ORDER:
                g = s[(s.threshold_kind == "absolute") & (s.threshold == thr)
                      & (s.strain == strain) & (s.tol == tol)]
                per_rep = [g[g.rep == rep]["per_1000um2"].mean() / od[(strain, tol, rep)]
                           for rep in ("r1", "r2")]
                ys.append(float(np.mean(per_rep)))
            fig.add_trace(go.Scatter(
                x=SWEEP_ORDER, y=ys, mode="lines+markers", name=STRAIN_LABEL[strain],
                legendgroup=strain, showlegend=(ci == 1),
                line=dict(color=palette[strain], width=2),
                marker=dict(size=7),
            ), row=1, col=ci)
        fig.update_xaxes(title_text="threshold (8-bit level)", type="log",
                         tickvals=SWEEP_ORDER, ticktext=[str(t) for t in SWEEP_ORDER],
                         row=1, col=ci)
        fig.update_yaxes(title_text="particles per 1000 µm² per OD600",
                         type="log", row=1, col=ci,
                         tickmode="array",
                         tickvals=[2, 5, 10, 20, 50, 100, 200, 500, 1000],
                         ticktext=["2", "5", "10", "20", "50", "100", "200",
                                   "500", "1000"])

    fig.update_layout(
        template="plotly_white", width=1000, height=620, legend_title="strain",
        title="Threshold sensitivity: does the between-strain ranking hold?",
        margin=dict(t=90, b=170),
    )
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-58,
        showarrow=False, align="left", font=dict(size=11, color="#666"),
        text=("<b>Under toluene the ranking is stable</b> — PCC1 &gt; Clone1 &gt; "
              "EPI300 &gt; Clone2 holds at every level from 3 to 40. "
              "<b>Without toluene it is not</b>: PCC1, Clone2<br>and Clone1 exchange "
              "places between levels, and only EPI300-lowest survives throughout. "
              "Per-image Otsu is not plotted — it returns thresholds an order of<br>"
              "magnitude apart on adjacent fields of one sample, so its line would "
              "not be a threshold series at all. Its counts are in "
              "fov_measurements.csv."),
    )
    save(fig, "threshold_sweep")


def main() -> int:
    particles = rd(OLD / "particles.csv.gz")
    fov = rd(OLD / "fov_measurements.csv")
    dens = rd(OLD / "vesicle_density.csv")

    # Figures use the primary field-of-view set: blank acquisitions dropped.
    blanks = set(zip(fov[fov.n_particles == 0].exported_dir,
                     fov[fov.n_particles == 0].series))
    particles = particles[[(a, b) not in blanks
                           for a, b in zip(particles.exported_dir, particles.series)]]

    density_figure(dens)
    size_figure(particles)
    sweep_figure(rd(OLD / "threshold_sweep.csv"), fov, dens)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

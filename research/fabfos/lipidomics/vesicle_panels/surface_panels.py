"""The figures: membrane area per OD, the size distribution, the threshold sweep.

Reads the tables written by particle_segment.py, control_floor.py and
surface_normalize.py and renders beside this file. Every mean carries its two
replicate points — n=2, and a bar alone would hide that.

Three things appear on these figures that are not in the archived density
figures, because the analysis now knows them:

* **The control floor**, drawn as a horizontal line on the density panel. A real
  acquisition with no sample in it still yields ~76 particles per 1000 µm², and a
  bar under that line is not a measurement. Two conditions are under it.
* **The resolution limit**, drawn on the size distribution. Most of this
  population sits at or below the ~211 nm these optics resolve, so the plotted
  radii are apparent spot sizes and the curve left of that line is not a size
  distribution of anything.
* **Resolved versus all particles**, side by side on the size figure, because the
  difference between them is a single-photon detection floor rather than a
  population of small vesicles.
"""

import gzip
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from segmenters import PSF_FWHM_NM, PSF_RADIUS_NM
from vesicle_common import PANELS, RESULTS, STRAIN_LABEL, STRAINS, TOL_LEVELS

PRIMARY_SET = "nonempty"
PRIMARY_POP = "resolved"
TOL_LABEL = {"notol": "no toluene", "tol": "+toluene"}
COLORS = {"notol": "#5b8def", "tol": "#e07a5f"}
PALETTE = {"epi300": "#888888", "pcc1": "#5b8def",
           "clone1": "#2a9d8f", "clone2": "#e07a5f"}
FLOOR_COLOR = "#c0392b"


def rd(path: Path) -> pd.DataFrame:
    opener = (lambda: gzip.open(path, "rt")) if path.suffix == ".gz" else path.open
    with opener() as fh:
        return pd.read_csv(StringIO("".join(l for l in fh if not l.startswith("#"))))


def save(fig, stem: str) -> None:
    fig.write_html(str(PANELS / f"{stem}.html"), include_plotlyjs="cdn")
    try:
        fig.write_image(str(PANELS / f"{stem}.png"), scale=2)
        print(f"  wrote {stem}.png + .html")
    except Exception as e:
        print(f"  wrote {stem}.html (png export skipped: {e})")


def grouped_bars(fig, d, value_col, row, col, showlegend):
    """Bars = mean of the two replicates; open circles = the replicates."""
    for tol in TOL_LEVELS:
        means, px, py = [], [], []
        for si, strain in enumerate(STRAINS):
            g = d[(d.strain == strain) & (d.tol == tol)]
            means.append(float(g[value_col].mean()))
            offset = -0.2 if tol == "notol" else 0.2
            for v in g[value_col]:
                px.append(si + offset)
                py.append(float(v))
        fig.add_trace(go.Bar(
            name=TOL_LABEL[tol], x=list(range(len(STRAINS))), y=means,
            marker_color=COLORS[tol], opacity=0.85, showlegend=showlegend,
            legendgroup=tol,
        ), row=row, col=col)
        fig.add_trace(go.Scatter(
            x=px, y=py, mode="markers",
            marker=dict(color="black", size=8, symbol="circle-open",
                        line=dict(width=1.6)),
            showlegend=False, legendgroup=tol, name=f"{TOL_LABEL[tol]} reps",
        ), row=row, col=col)


def surface_figure(surf: pd.DataFrame, floor_per_1000: float) -> None:
    d = surf[(surf.fov_set == PRIMARY_SET) & (surf.population == PRIMARY_POP)]
    fig = make_subplots(
        rows=1, cols=3, horizontal_spacing=0.075,
        subplot_titles=("Particle density",
                        "Membrane surface area",
                        "Membrane area per culture OD600"),
    )
    grouped_bars(fig, d, "mean_per_1000um2", 1, 1, showlegend=True)
    grouped_bars(fig, d, "mean_surface_um2_per_1000um2", 1, 2, showlegend=False)
    grouped_bars(fig, d, "surface_um2_per_1000um2_per_od", 1, 3, showlegend=False)

    # The floor belongs on the density panel only: it is a count, and the
    # control's areas are not comparable across the zoom change.
    fig.add_hline(y=floor_per_1000, line_dash="dash", line_color=FLOOR_COLOR,
                  line_width=2, row=1, col=1,
                  annotation_text="sample-free control", annotation_position="top left",
                  annotation_font=dict(size=10, color=FLOOR_COLOR))

    for c in (1, 2, 3):
        fig.update_xaxes(tickmode="array", tickvals=list(range(len(STRAINS))),
                         ticktext=[STRAIN_LABEL[s] for s in STRAINS], row=1, col=c)
    fig.update_yaxes(title_text="particles per 1000 µm²", row=1, col=1)
    fig.update_yaxes(title_text="µm² membrane per 1000 µm²", row=1, col=2)
    fig.update_yaxes(title_text="µm² membrane per 1000 µm² per OD600", row=1, col=3)
    fig.update_layout(
        barmode="group", bargap=0.25, template="plotly_white",
        width=1320, height=620, legend_title="treatment",
        title=("Vesicle membrane surface area, 22 May 2026 GUV imaging "
               "(sep segmentation, resolved particles, blank fields dropped)"),
        margin=dict(t=110, b=215),
    )
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-60,
        showarrow=False, align="left", font=dict(size=11, color="#666"),
        text=(
            "Bars are the mean of 2 biological replicates; open circles are the "
            "replicates themselves. Field area is a measured constant 8512.26 µm².<br>"
            f"<b>Dashed line = the detection floor</b>: a sample-free control "
            f"acquisition, at matched laser power, gain and pinhole, still yields "
            f"{floor_per_1000:.0f} particles per 1000 µm². EPI300 sits at or under it "
            "in both<br>treatments, and so does Clone2 +toluene; those bars are not "
            "measurements. The floor is drawn on counts only — the control is at a "
            "coarser zoom, so its areas are not comparable.<br>"
            "<b>Surface area is exactly 4x projected area</b> by algebra, so the "
            "middle and left panels carry much the same information; what differs "
            "between them is particle size.<br>"
            "<b>OD600 is not from the imaging day</b> — it is the lipidomics culture "
            "set (6 d post-challenge, fwd 2026-07-08) against imaging dated "
            "2026-05-22, and the replicate index is assumed to correspond.<br>"
            "<b>PCC1 +toluene is the one to distrust</b>: its OD600 (0.099, 0.103) is "
            "the lowest in the table, so normalizing divides by a very small number. "
            "That gap is the denominator, not the imaging."),
    )
    save(fig, "vesicle_surface_area")


def size_figure(particles: pd.DataFrame) -> None:
    """Cumulative distribution of radius, log axis, resolved and all side by side.

    An ECDF rather than a violin: the distribution is a narrow bulk at the
    resolution limit with a long heavy tail, which a KDE either flattens or
    clips, and plotly's violin does not transform its density onto a log axis at
    all. On an ECDF the bulk, the median and the tail are all readable, and
    "this strain has more big particles" is a visible vertical gap.
    """
    fig = make_subplots(
        rows=2, cols=2, shared_yaxes=True, shared_xaxes=True,
        horizontal_spacing=0.07, vertical_spacing=0.11,
        subplot_titles=(f"{TOL_LABEL['notol']} — all detections",
                        f"{TOL_LABEL['tol']} — all detections",
                        f"{TOL_LABEL['notol']} — resolved only",
                        f"{TOL_LABEL['tol']} — resolved only"),
    )
    resolved = particles[particles.radius_nm >= PSF_RADIUS_NM]
    for ri, (src, _tag) in enumerate([(particles, "all"), (resolved, "resolved")], start=1):
        for ci, tol in enumerate(TOL_LEVELS, start=1):
            for strain in STRAINS:
                d = np.sort(src[(src.strain == strain)
                                & (src.tol == tol)]["radius_nm"].values)
                if not len(d):
                    continue
                # One point per 200 particles: an ECDF over 200k rows is
                # indistinguishable from its subsample and 200x the file.
                step = max(1, len(d) // 2000)
                y = np.arange(1, len(d) + 1) / len(d)
                fig.add_trace(go.Scatter(
                    x=d[::step], y=y[::step], mode="lines",
                    name=STRAIN_LABEL[strain], legendgroup=strain,
                    showlegend=(ri == 1 and ci == 1),
                    line=dict(color=PALETTE[strain], width=2),
                    hovertemplate=f"{STRAIN_LABEL[strain]}<br>%{{x:.0f}} nm<br>"
                                  "%{y:.1%} smaller<extra></extra>",
                ), row=ri, col=ci)
            fig.add_vline(x=PSF_RADIUS_NM, line_dash="dot", line_color=FLOOR_COLOR,
                          row=ri, col=ci)
            fig.update_xaxes(type="log", range=[np.log10(20), np.log10(2000)],
                             title_text="apparent radius (nm)" if ri == 2 else None,
                             row=ri, col=ci)
        # Pinned: a cumulative fraction cannot leave [0, 1], and plotly's
        # autorange pads it to -100..400% which makes the curves unreadable.
        for ci in (1, 2):
            fig.update_yaxes(range=[0, 1.02], tickformat=".0%", row=ri, col=ci)
        fig.update_yaxes(title_text="fraction of particles smaller", row=ri, col=1)

    fig.update_layout(
        template="plotly_white", width=1120, height=820, legend_title="strain",
        title="Apparent particle radius, 22 May 2026 GUV imaging (sep segmentation)",
        margin=dict(t=110, b=215),
    )
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-52,
        showarrow=False, align="left", font=dict(size=11, color="#666"),
        text=(
            f"<b>Dotted line = {PSF_RADIUS_NM:.0f} nm</b>, half the "
            f"{PSF_FWHM_NM:.0f} nm point-spread function of this acquisition<br>"
            "(63x/1.40 NA, 580 nm emission, 1.0 Airy unit pinhole). Nothing imaged "
            "through this optic can be smaller.<br>"
            "<b>The top row is not a size distribution below that line</b> — those "
            "detections are spatially anti-clustered relative to<br>real particles and "
            "half of them peak at a single photon count, which is a detector floor.<br>"
            "The bottom row is the population every number in "
            "vesicle_surface_area.csv is built from.<br>"
            "<b>No deconvolution is applied</b>: radii are apparent spot sizes "
            "convolved with the PSF, so they are upper bounds."),
    )
    save(fig, "vesicle_size_distribution")


def sweep_figure(sweep: pd.DataFrame) -> None:
    """Is the between-strain ranking a property of the data or of the threshold?"""
    # Blank acquisitions only: they contribute a zero at every threshold and
    # would drag every strain's mean by however many blanks it happens to have.
    s = sweep[sweep.n_particles > 0]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1,
                        subplot_titles=(TOL_LABEL["notol"], TOL_LABEL["tol"]))
    knobs = sorted(s.knob.unique())
    for ci, tol in enumerate(TOL_LEVELS, start=1):
        for strain in STRAINS:
            ys = [float(s[(s.strain == strain) & (s.tol == tol)
                          & (s.knob == k)]["resolved_per_1000um2"].mean())
                  for k in knobs]
            fig.add_trace(go.Scatter(
                x=knobs, y=ys, mode="lines+markers", name=STRAIN_LABEL[strain],
                legendgroup=strain, showlegend=(ci == 1),
                line=dict(color=PALETTE[strain], width=2),
                marker=dict(size=7),
            ), row=1, col=ci)
        fig.add_vline(x=3.0, line_dash="dash", line_color="#999", row=1, col=ci)
        fig.update_xaxes(title_text="sep detection threshold (nsigma)", row=1, col=ci)
    fig.update_yaxes(title_text="resolved particles per 1000 µm²", row=1, col=1)
    fig.update_layout(
        template="plotly_white", width=1040, height=560, legend_title="strain",
        title="Ranking stability against the detection threshold",
        margin=dict(t=100, b=150),
    )
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-52,
        showarrow=False, align="left", font=dict(size=11, color="#666"),
        text=(
            "Dashed line is the threshold every other figure uses.<br>"
            "<b>The lines are nearly flat because they should be</b>: the threshold is "
            "a multiple of the measured local noise, and on the ~100 fields<br>"
            "whose background is exactly zero that is zero at every setting. The three "
            "hazy clon1_1 fields are the only place this dial does<br>"
            "anything — which is why an ordering that holds here is evidence about the "
            "data and not about the threshold.<br>"
            "The ranking does not change anywhere on the sweep. Blank acquisitions are "
            "excluded."),
    )
    save(fig, "vesicle_threshold_sweep")


def main() -> int:
    surf = rd(RESULTS / "vesicle_surface_area.csv")
    particles = rd(RESULTS / "particles.csv.gz")
    sweep = rd(RESULTS / "sensitivity_sweep.csv")
    floor = rd(RESULTS / "control_floor.csv")
    floor_per_1000 = float(
        floor[floor["series"] == "Series001"]["resolved_per_1000um2"].iloc[0])

    print(f"{len(particles)} particles, {len(surf)} normalized rows; "
          f"control floor {floor_per_1000:.1f} resolved particles per 1000 µm²")
    surface_figure(surf, floor_per_1000)
    size_figure(particles)
    sweep_figure(sweep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Per-feature volcano panels: each clone against two references —
strain-vs-control and its own toluene response — pellet and supernatant
combined into one figure.

  rows    = 4 : Clone1 volcano, Clone1 density, Clone2 volcano, Clone2 density
  columns = 4 : (1) pellet   -tol clone vs -tol EpCC1 (empty vector)
                (2) pellet   +tol clone vs -tol clone (own toluene response)
                (3) sup      -tol clone vs -tol ESCC1 (empty vector)
                (4) sup      +tol clone vs -tol clone (own toluene response)
  each dot = one lipid feature, OD-normalized (group-geomean biomass),
             median log2FC per lipidio-style Welch contrast (see
             od_strain_volcano.contrast_median), Storey's q-value (estimated
             pi0, the metabolomics/lipidomics-standard less-conservative
             correction — see od_strain_volcano.contrast_median's docstring).

Under each volcano row sits a density row on the SAME fold-change axis, carrying
three unit-area kernel density curves: all features in that contrast, the
membrane-called subset, and the curvature-forcing subset. Unit area rather than
counts, because the curvature-forcing set is a small minority and a count-scaled
curve would be invisible; per-curve n is in the legend so the nesting stays
legible, and one bandwidth (computed on the all-features set) is reused for all
three so a difference in shape is a difference in the data, not in smoothing.

COVERAGE, stated here because it is the figure's main limitation: the membrane
and curvature curves come from `identification/membrane_calls.csv`, which is
NEGATIVE MODE ONLY -- 800 of the 2180 features the volcano plots. The two lower
curves are therefore drawn from a subset of the points above them, not from all
of them, and the caption says so. An attempt to lift that limit with MS2Lipid is
recorded in `identify/ms2lipid_validate.py`; it did not survive its own
validation gate, so the neg-mode lane remains the best available call set.

This script does not touch od_strain_volcano.py's own 04_volcano_species
figures.

Writes png+svg to .awm/data/figures/publish/04_lipidomics/05_clone_response/
  clone_response_storey.{png,svg}
Env: p312.  Run:  mamba run -n p312 python research/fabfos/lipidomics/od_clone_response_volcano.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lipidio import load_bio, od_normalize, log2, PROCESSED
from od_strain_volcano import (
    cols_for, contrast_median, final_class,
    XLIM, XLIM_PAD, C_ANN,
)

CALLS_CSV = PROCESSED / "identification" / "membrane_calls.csv"
# curvature_prior reads the PE/PC group as PE, which rests on E. coli having no
# phosphatidylcholine synthase. curvature_strict assumes nothing and consequently
# resolves 9.8% of features -- too few to draw. The prior column is used and the
# assumption is named in the caption rather than buried.
CURVATURE_COL = "curvature_prior"

C_POS = "#C0392B"  # significant, +log2FC
C_NEG = "#2255AA"  # significant, -log2FC

# Density curves. Deliberately not the volcano's red/blue: those encode direction
# of change, and reusing them here would read as "this curve is the up-regulated
# one" when it means a lipid set.
C_ALL = "#666666"
C_MEMB = "#1B7F5E"
C_CURV = "#B8860B"
DENSITY_ROW_RATIO = 0.42     # density row height as a fraction of a volcano row

PUB = Path(".awm/data/figures/publish/04_lipidomics/05_clone_response")
PUB.mkdir(parents=True, exist_ok=True)

CLONES = ["Clone1", "Clone2"]
CTRL_STRAIN_BY_FRACTION = {"P": "EpCC1", "S": "ESCC1"}
FRACTION_TITLE = {"P": "pellet", "S": "supernatant"}
PRIMARY_OD = "group_geomean"

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def draw_panel_q(ax, df, xlim=XLIM):
    """Same as od_strain_volcano.draw_panel, but plots -log10(QVALUE) on the
    y-axis instead of -log10(pvalue), so the significance threshold line and
    dot coloring (both q-based) agree. Significant points are colored by
    direction (red = +log2FC, blue = -log2FC); non-significant points stay
    grey regardless of direction."""
    fc = df["log2fc_clone_vs_ctrl"].to_numpy()
    logq = -np.log10(df["qvalue"].to_numpy())
    sig = ((df.qvalue < 0.05) & (df["log2fc_clone_vs_ctrl"].abs() > 1)).to_numpy()
    sig_pos, sig_neg = sig & (fc > 0), sig & (fc < 0)
    x_plot = np.clip(fc, -xlim, xlim)
    out_hi, out_lo = fc > xlim, fc < -xlim
    inb = ~(out_hi | out_lo)

    def grp(mask, marker, size, color, alpha, label=None):
        if mask.any():
            ax.scatter(x_plot[mask], logq[mask], marker=marker, s=size, c=color,
                       alpha=alpha, lw=0, label=label)

    grp(inb & ~sig, "o", 8, C_ANN, 0.6, "not significant")
    grp(out_hi & ~sig, ">", 9, C_ANN, 0.6)
    grp(out_lo & ~sig, "<", 9, C_ANN, 0.6)
    grp(inb & sig_pos, "o", 24, C_POS, 0.85, "q<0.05, log$_2$FC>1")
    grp(out_hi & sig_pos, ">", 30, C_POS, 0.9)
    grp(inb & sig_neg, "o", 24, C_NEG, 0.85, "q<0.05, log$_2$FC<-1")
    grp(out_lo & sig_neg, "<", 30, C_NEG, 0.9)

    dash = (6, 4)
    ax.axhline(-np.log10(0.05), dashes=dash, lw=0.6, c="k", alpha=0.35, zorder=0)
    ax.axvline(1, dashes=dash, lw=0.6, c="k", alpha=0.35, zorder=0)
    ax.axvline(-1, dashes=dash, lw=0.6, c="k", alpha=0.35, zorder=0)
    ax.set_xlim(-xlim - XLIM_PAD, xlim + XLIM_PAD)


def load_lipid_sets():
    """feature_id sets for the two density overlays, plus their coverage.

    Returns (membrane_ids, curvature_ids, note). `note` is the disclosure string
    that goes into the caption -- it is returned rather than printed so the figure
    cannot be drawn without it.
    """
    calls = CALLS_CSV
    if not calls.exists():
        return set(), set(), f"membrane calls not found at {calls}"
    m = pd.read_csv(calls)
    memb = set(m.loc[m.membrane == "yes", "feature_id"])
    curv = set(m.loc[m[CURVATURE_COL] == "curvature-forcing", "feature_id"])
    pol = ", ".join(sorted(m.polarity.dropna().unique()))
    note = (f"membrane/curvature from {calls.name} ({len(m)} features, {pol} mode only); "
            f"membrane n={len(memb)}, curvature-forcing n={len(curv)} "
            f"by {CURVATURE_COL}")
    return memb, curv, note


def robust_bw(u: np.ndarray) -> float:
    """Robust Silverman bandwidth, h = 0.9 * min(sd, IQR/1.34) * n^(-1/5).

    Same rule as main/ecspr/nullfit/40_kde_style.py. The IQR term is what keeps a
    handful of extreme fold changes from over-smoothing the bulk.
    """
    n = u.size
    sd = float(np.std(u, ddof=1))
    iqr = float(np.subtract(*np.percentile(u, [75, 25])))
    scale = min(sd, iqr / 1.34) if iqr > 0 else sd
    if not np.isfinite(scale) or scale <= 0:
        scale = sd if sd > 0 else 1.0
    return 0.9 * scale * n ** (-0.2)


def gaussian_density(u: np.ndarray, grid: np.ndarray, h: float) -> np.ndarray:
    """Unit-area Gaussian KDE evaluated on `grid`. No scipy: the rest of the OD
    figure family is plain matplotlib/numpy and this is four lines."""
    z = (grid[:, None] - u[None, :]) / h
    return np.exp(-0.5 * z * z).sum(axis=1) / (u.size * h * np.sqrt(2 * np.pi))


def draw_density(ax, df, memb_ids, curv_ids, xlim=XLIM):
    """Three unit-area densities over log2FC, sharing the volcano's x-axis.

    Densities are evaluated from UNCLIPPED fold changes on a grid that spans the
    data, then displayed over the visible window. Feeding the clipped values in
    would pile every runaway feature onto +-xlim and grow a fake mode at the panel
    edge exactly where the eye is drawn.
    """
    fid = df["feature_id"]
    fc_all = df["log2fc_clone_vs_ctrl"].to_numpy(dtype=float)
    ok = np.isfinite(fc_all)
    fc_all = fc_all[ok]
    fid = fid[ok]
    if fc_all.size < 3:
        ax.set_axis_off()
        return

    pad = 3 * robust_bw(fc_all)
    grid = np.linspace(min(-xlim, fc_all.min()) - pad,
                       max(xlim, fc_all.max()) + pad, 800)
    # One bandwidth for all three curves, from the all-features set. Per-curve
    # bandwidths would make the small sets smoother purely because they are small,
    # and the panel's whole job is comparing their shapes.
    h = robust_bw(fc_all)

    series = [("all features", fc_all, C_ALL),
              ("membrane", fc_all[fid.isin(memb_ids).to_numpy()], C_MEMB),
              ("curvature-forcing", fc_all[fid.isin(curv_ids).to_numpy()], C_CURV)]

    peak = 0.0
    for label, u, color in series:
        if u.size < 3:
            continue
        y = gaussian_density(u, grid, h)
        peak = max(peak, float(y.max()))
        ax.fill_between(grid, 0, y, color=color, alpha=0.16, lw=0, zorder=1)
        ax.plot(grid, y, color=color, lw=1.2, zorder=2,
                label=f"{label} (n={u.size})")

    dash = (6, 4)
    for x in (-1, 1):
        ax.axvline(x, dashes=dash, lw=0.6, c="k", alpha=0.35, zorder=0)
    ax.set_xlim(-xlim - XLIM_PAD, xlim + XLIM_PAD)
    ax.set_ylim(0, peak * 1.18 if peak > 0 else 1)
    ax.set_yticks([])
    for side in ("left", "right", "top"):
        ax.spines[side].set_visible(False)


def make_figure(feats, abund_od, lg_od, bio_od, fclass):
    columns = []
    for fraction in ("P", "S"):
        group = FRACTION_TITLE[fraction]
        ctrl_strain = CTRL_STRAIN_BY_FRACTION[fraction]
        columns.append((
            group, "Clone vs PCC1 (-Tol.)",
            lambda clone, fraction=fraction, ctrl_strain=ctrl_strain: (
                cols_for(bio_od, clone, fraction, "ctrl"),
                cols_for(bio_od, ctrl_strain, fraction, "ctrl")),
        ))
        columns.append((
            group, "+Tol. vs -Tol",
            lambda clone, fraction=fraction: (
                cols_for(bio_od, clone, fraction, "tol"),
                cols_for(bio_od, clone, fraction, "ctrl")),
        ))

    memb_ids, curv_ids, cov_note = load_lipid_sets()

    # Four rows: volcano, density, volcano, density. sharey is set per row kind,
    # NOT globally -- the two kinds carry different quantities (-log10 q against
    # probability density) and a global sharey would force one scale on both.
    nrow, ncol = 2 * len(CLONES), len(columns)
    fig, axes = plt.subplots(
        nrow, ncol, figsize=(17.0, 11.4), sharex=True, sharey=False,
        gridspec_kw={"height_ratios": [1, DENSITY_ROW_RATIO] * len(CLONES)})
    vol_rows = [2 * i for i in range(len(CLONES))]
    den_rows = [2 * i + 1 for i in range(len(CLONES))]
    for r in vol_rows[1:]:                     # link the volcanoes to each other
        for c in range(ncol):
            axes[r, c].sharey(axes[vol_rows[0], 0])
    for c in range(1, ncol):
        axes[vol_rows[0], c].sharey(axes[vol_rows[0], 0])

    any_panel = False
    for i, clone in enumerate(CLONES):
        vr, dr = vol_rows[i], den_rows[i]
        for c, (group, col_label, idx_fn) in enumerate(columns):
            ax, dax = axes[vr, c], axes[dr, c]
            a_idx, b_idx = idx_fn(clone)
            if len(a_idx) < 2 or len(b_idx) < 2:
                ax.text(0.5, 0.5, "insufficient replicates", ha="center", va="center",
                        transform=ax.transAxes, fontsize=8, color="#999")
                ax.set_axis_off()
                dax.set_axis_off()
                continue
            df = contrast_median(feats, abund_od, lg_od, a_idx, b_idx,
                                  fc_col="log2fc_clone_vs_ctrl", fdr="storey")
            df["final_class"] = fclass.reindex(df["feature_id"]).values
            draw_panel_q(ax, df)
            draw_density(dax, df, memb_ids, curv_ids)
            any_panel = True
            if dr == nrow - 1:
                dax.set_xlabel(col_label)
            if c == 0:
                ax.set_ylabel(clone)
    axes[vol_rows[0], 0].set_yticks([0, 1, 2])
    strip_grid(axes, vol_rows, den_rows)
    add_legend(fig, axes, vol_rows, den_rows)
    fig.tight_layout(rect=[0.055, 0.15, 1, 0.96])
    hug_density_rows(axes, vol_rows, den_rows)

    # Two more spanning-label tiers beyond each axes' own labels: a group
    # label ("pellet"/"supernatant") centered over its 2 columns, and one
    # "log2(FC)" label centered under the whole row of 4 — positions are
    # read back from the finalized axes so they track tight_layout's result
    # rather than a hand-guessed fraction of the figure.
    bl, br = axes[-1, 0].get_position(), axes[-1, 1].get_position()
    sl, sr = axes[-1, 2].get_position(), axes[-1, 3].get_position()
    y_group = bl.y0 - 0.07
    y_line = y_group + 0.008
    fig.add_artist(plt.Line2D([bl.x0, br.x1], [y_line, y_line],
                               transform=fig.transFigure, color="black", lw=0.4))
    fig.add_artist(plt.Line2D([sl.x0, sr.x1], [y_line, y_line],
                               transform=fig.transFigure, color="black", lw=0.4))
    fig.text((bl.x0 + br.x1) / 2, y_group, "pellet", ha="center", va="top", fontsize=10)
    fig.text((sl.x0 + sr.x1) / 2, y_group, "supernatant", ha="center", va="top", fontsize=10)
    y_axis_label = y_group - 0.05
    fig.text((bl.x0 + sr.x1) / 2, y_axis_label, "log$_2$(FC)", ha="center", va="top", fontsize=11)

    # One rotated label per row rather than one spanning the figure: the two row
    # kinds are interleaved, so a single centred label would sit against a
    # density panel and read as its axis.
    x_lab = bl.x0 - 0.045
    for r, text in [(r, "-log$_{10}$(q)") for r in vol_rows] + \
                   [(r, "density") for r in den_rows]:
        p = axes[r, 0].get_position()
        fig.text(x_lab, (p.y0 + p.y1) / 2, text, rotation=90,
                 ha="center", va="center", fontsize=11 if text.startswith("-") else 9)

    fig.text(bl.x0, y_axis_label - 0.035, cov_note, ha="left", va="top",
             fontsize=7.5, color="#555")
    return fig, any_panel


def hug_density_rows(axes, vol_rows, den_rows, gap=0.006):
    """Slide each density row up until it nearly touches its own volcano.

    tight_layout spaces all four rows evenly, which leaves every density panel
    floating halfway between the volcano it belongs to and the next clone's --
    so the reader has to be told which pairs go together instead of seeing it.
    Positions are read back and rewritten after tight_layout has run, the same
    way the figure-level labels are anchored, so this survives a figsize change.
    """
    for vr, dr in zip(vol_rows, den_rows):
        v = axes[vr, 0].get_position()
        d = axes[dr, 0].get_position()
        shift = (v.y0 - gap) - d.y1
        if shift <= 0:
            continue
        for c in range(axes.shape[1]):
            p = axes[dr, c].get_position()
            axes[dr, c].set_position([p.x0, p.y0 + shift, p.width, p.height])


def strip_grid(axes, vol_rows, den_rows):
    """Like od_strain_volcano.strip_inner_axes, but row-kind aware.

    The imported version keeps x-ticks on the LAST row only, which with four
    interleaved rows would strip them from both volcanoes and both upper density
    panels. Here the x-axis survives on the bottom row of each fraction block --
    i.e. each density row -- because that is the row the reader scans against, and
    the y-axis is dropped everywhere it only repeats column 0.
    """
    last_den = den_rows[-1]
    for r in range(axes.shape[0]):
        for c in range(axes.shape[1]):
            ax = axes[r, c]
            if not ax.axison:
                continue
            if c != 0:
                ax.spines["left"].set_visible(False)
                ax.tick_params(axis="y", left=False, labelleft=False)
            if r != last_den:
                ax.spines["bottom"].set_visible(r in den_rows)
                ax.tick_params(axis="x", bottom=False, labelbottom=False)


def add_legend(fig, axes, vol_rows, den_rows):
    """Two figure-level legends, one per row kind, each built from ALL panels of
    that kind and deduped by label.

    Two rather than one because the marker legend and the density legend describe
    different things; sweeping every labelled artist into a single box -- which is
    what this function used to do -- would put "curvature-forcing (n=130)" in the
    volcano's key. A per-axis legend is still wrong for either: it silently drops
    an entry whenever that one panel happens to have zero points of that kind.
    """
    def collect(rows):
        handles, labels = [], []
        for r in rows:
            for ax in axes[r]:
                for h, l in zip(*ax.get_legend_handles_labels()):
                    if l not in labels:
                        handles.append(h)
                        labels.append(l)
        return handles, labels

    vh, vl = collect(vol_rows)
    if vh:
        fig.legend(vh, vl, loc="upper right", bbox_to_anchor=(0.995, 0.995),
                   frameon=True, fontsize=7.5, markerscale=1.3)
    dh, dl = collect(den_rows)
    if dh:
        fig.add_artist(fig.legend(
            dh, dl, loc="upper right", bbox_to_anchor=(0.995, 0.915),
            frameon=True, fontsize=7.5, title="density curves",
            title_fontsize=7.5))


def main():
    feats, abund_raw, bio = load_bio(source="metaboscape", polarity="merged")
    fclass = final_class(feats)

    abund_od = od_normalize(abund_raw, PRIMARY_OD)
    bio_od = bio.loc[abund_od.columns]
    lg_od = log2(abund_od)

    fig, any_panel = make_figure(feats, abund_od, lg_od, bio_od, fclass)
    if not any_panel:
        print("[skip] clone_response_storey: no eligible comparisons")
        plt.close(fig)
        return
    for ext in ("png", "svg"):
        fig.savefig(PUB / f"clone_response_storey.{ext}", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"[publish] wrote {PUB / 'clone_response_storey'}.png (+ .svg)")


if __name__ == "__main__":
    main()

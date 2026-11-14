"""Two publish-tree figures that resolve the OD-vs-composition question:

  01_lipid_per_cell        absolute total lipid signal PER OD (per cell), ctrl vs
                           toluene, per culture x fraction. The "quantity" axis:
                           bars rise under toluene in the parent/empty-vector
                           background, stay flat in the clones.
  02_composition_invariant group-mean relative class composition, same x-axis.
                           The "recipe" axis: the stacked bands are near-identical
                           ctrl->tol (total-variation distance annotated), so the
                           mix does not move even where the per-cell total does.

Together they make the point: under toluene the background upsizes its whole
membrane lipid pool per cell while keeping the same class proportions.

Reads only pre-computed CSVs (no re-analysis):
  processed/metaboscape/od/od_total_lipid.csv               (fig 1)
  processed/metaboscape/composition/group_composition_mean.csv    (fig 2)
  processed/metaboscape/composition/composition_tv_distance.csv   (fig 2 annot)

Writes png + svg into the shared SCADC publish tree:
  .awm/data/figures/publish/04_lipidomics/

Env: p312.  Run:  mamba run -n p312 python research/fabfos/lipidomics/od_publish_figs.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy import stats

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
PUB = Path(".awm/data/figures/publish/04_lipidomics")

# culture (OD table) -> lipidomics strain, by fraction; reversed for the per-sample join.
STRAIN_TO_CULTURE = {
    "Epi300": "EPI300", "ESi300": "EPI300",
    "EpCC1": "EpCC1", "ESCC1": "EpCC1",
    "Clone1": "Clone1", "Clone2": "Clone2",
}
PUB.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

# culture order + which parent/empty-vector label each fraction uses
CULT = {
    "P": ["Epi300", "EpCC1", "Clone1", "Clone2"],
    "S": ["ESi300", "ESCC1", "Clone1", "Clone2"],
}
FRAC_TITLE = {"P": "Pellet (cell) fraction", "S": "Supernatant fraction"}
DISPLAY_NAME = {"Epi300": "EPI300", "ESi300": "EPI300", "EpCC1": "PCC1", "ESCC1": "PCC1",
                "Clone1": "Clone1", "Clone2": "Clone2"}

# one group per culture; each group carries its pellet strain + supernatant strain
CULTURE_ORDER = ["EPI300", "PCC1", "Clone1", "Clone2"]
CULTURE_STRAIN = {
    "EPI300": {"P": "Epi300", "S": "ESi300"},
    "PCC1": {"P": "EpCC1", "S": "ESCC1"},
    "Clone1": {"P": "Clone1", "S": "Clone1"},
    "Clone2": {"P": "Clone2", "S": "Clone2"},
}
# darker shade = pellet, lighter shade = supernatant (boxed in the matching pellet shade);
# blue = ctrl, orange = tol
BAR_COLOR = {
    ("P", "ctrl"): "#4E77A8", ("P", "tol"): "#D08A50",
    ("S", "ctrl"): "#D7E4F5", ("S", "tol"): "#FAE3C9",
}
BAR_LABEL = {
    ("P", "ctrl"): "pellet − toluene", ("P", "tol"): "pellet + toluene",
    ("S", "ctrl"): "supernatant − toluene", ("S", "tol"): "supernatant + toluene",
}

# family stack order + colours (matches composition_per_sample.py)
FAM_ORDER = ["PE", "PG", "PC", "PS", "PA", "HBMP", "Lyso", "Neutral", "Redox/prenol", "Other"]
FAM_COLOR = {
    "PE": "#2a6f7f", "PG": "#3d9aab", "PC": "#e0a458", "PS": "#8c5a9e",
    "PA": "#c05746", "HBMP": "#6a8d3f", "Lyso": "#d94f4f", "Neutral": "#9a9a55",
    "Redox/prenol": "#4a7ab5", "Other": "#b8b8b8",
}


def _save(fig, stem):
    for ext in ("png", "svg"):
        fig.savefig(PUB / f"{stem}.{ext}", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"[publish] wrote {PUB / stem}.png (+ .svg)")


# --------------------------------------------------------------------------- #
# Figure 1 — lipid per cell (absolute total lipid signal / OD), per replicate
# --------------------------------------------------------------------------- #
def _per_sample_total_per_od() -> pd.DataFrame:
    """Per-sample raw total lipid signal / that sample's own OD600 (per_rep
    normalization — the literal "individual sample" recipe), joined to
    strain/fraction/treatment/replicate."""
    feats = pd.read_csv(M / "features_clean.csv", index_col="feature_id")
    md = pd.read_csv(M / "metadata_bio.csv")
    od = pd.read_csv(Path("research/fabfos/lipidomics/od_values.csv"), comment="#")

    sample_cols = [c for c in feats.columns if c in md.sample_basename.values]
    totals = feats[sample_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=0)
    df = md.set_index("sample_basename").loc[sample_cols].copy()
    df["total_raw"] = totals
    df["culture"] = df["strain"].map(STRAIN_TO_CULTURE)
    df = df.merge(od, left_on=["culture", "treatment", "replicate"],
                  right_on=["culture", "treatment", "rep"], how="left")
    df["total_per_od"] = df["total_raw"] / df["od600"]
    return df


YMAX = 10.0  # shared axis cap; the EPI300 pellet +toluene rep3 (v≈15.8) is off-scale, drawn as a triangle
OD_WIDTH_SCALE = 0.45  # data-x-units of line width per unit OD600 (see legend swatches 0.2/0.5/0.8)
OD_WIDTH_SCALE_LEGEND = 1.0  # separate scale for the legend inset's own (unrelated) coordinate system


def _od_line(ax, xc, y, od_val, zorder=3):
    hw = od_val * OD_WIDTH_SCALE / 2
    ax.plot([xc - hw, xc + hw], [y, y], color="black", linewidth=0.8, solid_capstyle="butt", zorder=zorder)


def _draw_legend(ax):
    """Hand-built combined legend: right-justified group labels, shared −/+ toluene column
    headers over the pellet/supernatant swatches (no divider needed there), and a stacked
    OD600 line-width key with a divider spanning just its own three rows."""
    lx = ax.inset_axes([0.60, 0.66, 0.36, 0.32])
    lx.set_xlim(0, 6.6); lx.set_ylim(0, 7.2)
    lx.axis("off")

    LABEL_X = 1.7
    COL_MINUS_X = 2.15
    COL_PLUS_X = 2.75
    COL_MID_X = (COL_MINUS_X + COL_PLUS_X) / 2

    def bar_swatch(cx, y, color, edgecolor=None):
        lx.add_patch(Rectangle((cx - 0.22, y - 0.28), 0.44, 0.56, facecolor=color,
                                edgecolor=edgecolor, linewidth=1.1 if edgecolor else 0))

    def od_tick(cx, y, od_val):
        hw = od_val * OD_WIDTH_SCALE_LEGEND / 2
        lx.plot([cx - hw, cx + hw], [y, y], color="black", linewidth=0.8, solid_capstyle="butt")

    # shared column headers for the two toluene swatch rows
    y_head = 6.7
    lx.text(COL_MINUS_X, y_head, "−", fontsize=8.5, va="center", ha="center")
    lx.text(COL_PLUS_X - 0.11, y_head, "+ toluene", fontsize=8.0, va="center", ha="left")

    y_pellet = 5.75
    lx.text(LABEL_X, y_pellet, "pellet", fontsize=8.5, va="center", ha="right")
    bar_swatch(COL_MINUS_X, y_pellet, BAR_COLOR[("P", "ctrl")], edgecolor=BAR_COLOR[("P", "ctrl")])
    bar_swatch(COL_PLUS_X, y_pellet, BAR_COLOR[("P", "tol")], edgecolor=BAR_COLOR[("P", "tol")])

    y_sup = 4.85
    lx.text(LABEL_X, y_sup, "supernatant", fontsize=8.5, va="center", ha="right")
    bar_swatch(COL_MINUS_X, y_sup, BAR_COLOR[("S", "ctrl")], edgecolor=BAR_COLOR[("P", "ctrl")])
    bar_swatch(COL_PLUS_X, y_sup, BAR_COLOR[("S", "tol")], edgecolor=BAR_COLOR[("P", "tol")])

    # OD600 key: stacked rows, divider spans only this block, ticks centered between the columns
    od_ys = [3.35, 2.55, 1.75]
    lx.plot([1.85, 1.85], [od_ys[-1] - 0.4, od_ys[0] + 0.4], color="black", linewidth=0.8)
    lx.text(LABEL_X, sum(od_ys) / 3, "OD$_{600}$", fontsize=8.5, va="center", ha="right")
    for od_val, y in zip((0.2, 0.5, 0.8), od_ys):
        od_tick(COL_MID_X, y, od_val)
        lx.text(COL_MID_X + 0.55, y, f"{od_val:.1f}", fontsize=8.0, va="center", ha="left")


def fig_per_cell():
    per_sample = _per_sample_total_per_od()
    fig, ax = plt.subplots(figsize=(8.67, 5.5))
    x = np.arange(len(CULTURE_ORDER)) * 2.0
    w = 0.32
    OUTLINE_LW = 1.1
    GAP = 0.016  # half the outline's data-space bleed; keeps adjacent bars' outlines from touching
    combos = [("P", "ctrl"), ("P", "tol"), ("S", "ctrl"), ("S", "tol")]
    offsets = np.linspace(-1.5 * (w + GAP), 1.5 * (w + GAP), 4)

    bar_xc, bar_vals = {}, {}  # keyed by (culture, fr, tr) -> xc / replicate values
    for i, cu in enumerate(CULTURE_ORDER):
        for (fr, tr), off in zip(combos, offsets):
            xc = x[i] + off
            strain = CULTURE_STRAIN[cu][fr]
            rows = per_sample[(per_sample.strain == strain) & (per_sample.fraction == fr) &
                              (per_sample.treatment == tr)].sort_values("replicate")
            vals = rows["total_per_od"].values / 1e8
            bar_xc[(cu, fr, tr)], bar_vals[(cu, fr, tr)] = xc, vals
            if cu == "EPI300" and tr == "tol" and len(vals) >= 2:
                bar_val = np.sort(vals)[:2].mean()  # drop the high outlier rep
            else:
                bar_val = vals.mean() if len(vals) else np.nan
            color = BAR_COLOR[(fr, tr)]
            edgecolor = BAR_COLOR[("P", tr)] if fr == "S" else color
            ax.bar(xc, bar_val if not np.isnan(bar_val) else 0, w, facecolor=color,
                   edgecolor=edgecolor, linewidth=OUTLINE_LW,
                   label=BAR_LABEL[(fr, tr)] if i == 0 else None)
            # one horizontal "I"-beam per replicate, centered on the bar; width ∝ OD600
            for v, od_val in zip(vals, rows["od600"].values):
                if cu == "EPI300" and fr == "P" and tr == "tol" and v > YMAX:
                    yy = YMAX * 0.96
                    _od_line(ax, xc, yy - 0.25, od_val, zorder=4)
                    ax.scatter([xc], [yy], s=26, marker="^", color=color, edgecolor="black",
                               linewidth=0.8, zorder=4)
                    ax.annotate(f"y={v:.1f}", xy=(xc, yy), xytext=(6, 0),
                                textcoords="offset points", fontsize=6.0, color="black",
                                ha="left", va="center", zorder=4)
                else:
                    _od_line(ax, xc, v, od_val)

    _, pval = stats.ttest_ind(bar_vals[("Clone2", "S", "ctrl")], bar_vals[("PCC1", "S", "ctrl")],
                              equal_var=False)
    x1, x2 = bar_xc[("PCC1", "S", "ctrl")], bar_xc[("Clone2", "S", "ctrl")]
    ybar = 5.0
    ax.plot([x1, x1, x2, x2], [ybar - 0.15, ybar, ybar, ybar - 0.15], color="black", linewidth=0.8)
    ax.text((x1 + x2) / 2, ybar + 0.08, f"p = {pval:.2f}", ha="center", va="bottom", fontsize=7.5)

    ax.set_ylim(0, YMAX)
    ax.set_xticks(x); ax.set_xticklabels(CULTURE_ORDER)
    ax.set_xlim(x[0] - 1.0, x[-1] + 1.6)
    ax.set_ylabel("total lipid signal per OD$_{600}$")

    _draw_legend(ax)

    fig.tight_layout()
    _save(fig, "01_lipid_per_cell")


# --------------------------------------------------------------------------- #
# Figure 2 — composition stays flat (group-mean stacked class fractions)
# --------------------------------------------------------------------------- #
def fig_composition():
    grp = pd.read_csv(M / "composition" / "group_composition_mean.csv")
    grp = grp[grp.family.isin(FAM_ORDER)]        # drop the anionic_frac pseudo-row
    tv = pd.read_csv(M / "composition" / "composition_tv_distance.csv")
    tv_tc = tv[tv.treatment == "tol_vs_ctrl"].set_index(["fraction", "strain"])["tv_vs_parent"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, fr in zip(axes, ("P", "S")):
        cults = CULT[fr]
        labels, xs = [], []
        pos = 0
        for cu in cults:
            for tr in ("ctrl", "tol"):
                xs.append((cu, tr, pos)); labels.append(f"{cu}\n{tr}"); pos += 1
            pos += 0.4                             # gap between cultures
        bottoms = {x[2]: 0.0 for x in xs}
        for fam in FAM_ORDER:
            heights = []
            for cu, tr, p in xs:
                r = grp[(grp.fraction == fr) & (grp.strain == cu) &
                        (grp.treatment == tr) & (grp.family == fam)]
                heights.append(float(r["mean"].iloc[0]) if len(r) else 0.0)
            xpos = [x[2] for x in xs]
            ax.bar(xpos, heights, width=0.85, bottom=[bottoms[p] for p in xpos],
                   color=FAM_COLOR[fam], label=fam if fr == "P" else None,
                   edgecolor="white", linewidth=0.4)
            for p, h in zip(xpos, heights):
                bottoms[p] += h
        # annotate tol-vs-ctrl composition shift (total variation distance)
        for cu in cults:
            d = tv_tc.get((fr, cu), np.nan)
            if not np.isnan(d):
                p_ctrl = [x[2] for x in xs if x[0] == cu and x[1] == "ctrl"][0]
                ax.text(p_ctrl + 0.5, 1.03, f"Δ={d:.02f}", ha="center", va="bottom",
                        fontsize=7.5, color="#444")
        ax.set_xticks([x[2] for x in xs]); ax.set_xticklabels(labels, fontsize=7.5)
        ax.set_ylim(0, 1.10); ax.set_title(FRAC_TITLE[fr], fontsize=10)
        if fr == "P":
            ax.set_ylabel("fraction of mapped lipid signal")
    handles, labs = axes[0].get_legend_handles_labels()
    axes[1].legend(handles, labs, loc="center left", bbox_to_anchor=(1.01, 0.5),
                   frameon=False, fontsize=8, title="class family", title_fontsize=8.5)
    fig.suptitle("Membrane recipe is invariant — class proportions barely move ctrl→toluene "
                 "(Δ = total-variation distance)", fontsize=11.5, y=1.02)
    fig.tight_layout(rect=[0, 0, 0.9, 1])
    _save(fig, "02_composition_invariant")


if __name__ == "__main__":
    fig_per_cell()
    fig_composition()

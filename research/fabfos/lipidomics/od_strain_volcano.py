"""Per-feature volcano panels: each clone vs each control, OD-normalized.

  rows    = clones    : Clone1, Clone2
  columns = controls  : EPI300 (parent), EpCC1 (empty vector)
  each dot = one lipid feature (all annotated + unannotated), OD-normalized
             (group-geomean biomass, same primary scheme as od_analysis.py)

One 2x2 figure per (fraction, treatment) — pellet/supernatant x ctrl/toluene,
written separately because a clone's phenotype relative to its parent is not
assumed to be the same across fraction or treatment (see composition_per_sample
/ od_lfc_scatter findings: the clones' constitutive divergence is fraction- and
treatment- sensitive).

Writes png+svg to .awm/data/figures/publish/04_lipidomics/04_volcano_species/
Env: p312.  Run:  mamba run -n p312 python research/fabfos/lipidomics/od_strain_volcano.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lipidio import load_bio, od_map, od_normalize, log2, METABOSCAPE_DIR

PUB = Path(".awm/data/figures/publish/04_lipidomics/04_volcano_species")
PUB.mkdir(parents=True, exist_ok=True)

CLONES = ["Clone1", "Clone2"]
# culture -> per-fraction sample strain code (mirrors lipidio.CULTURE_TO_STRAINS)
CONTROL_GROUPS = {
    "EPI300 (parent)": {"P": "Epi300", "S": "ESi300"},
    "EpCC1 (empty vector)": {"P": "EpCC1", "S": "ESCC1"},
}
FRACTION_TITLE = {"P": "pellet (cell)", "S": "supernatant"}
TREATMENT_TITLE = {"ctrl": "control", "tol": "+toluene"}
PRIMARY_OD = "group_geomean"

C_ANN, C_DARK, C_SIG = "#B8B8B8", "#2A6F7F", "#C0392B"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def cols_for(bio, strain, fraction, treatment):
    c = bio[(bio.strain == strain) & (bio.fraction == fraction) & (bio.treatment == treatment)]
    return c.index.tolist()


def estimate_pi0(pvals):
    """Storey's pi0 (fraction of true nulls): fit a natural cubic smoothing
    spline to pi0_hat(lambda) = #{p > lambda} / (m*(1-lambda)) over
    lambda in [0.05..0.95] and evaluate at the largest lambda — the standard
    recipe from Storey & Tibshirani 2003 / R's `qvalue` package. Falls back
    to the last raw pi0_hat (or 1.0, fully BH-conservative) if the spline
    fit is degenerate (e.g. too few finite p-values)."""
    from scipy.interpolate import UnivariateSpline

    p = np.asarray(pvals, dtype=float)
    p = p[np.isfinite(p)]
    if len(p) == 0:
        return 1.0
    lambdas = np.arange(0.05, 0.96, 0.05)
    pi0_hat = np.array([(p > lam).mean() / (1 - lam) for lam in lambdas])
    try:
        spline = UnivariateSpline(lambdas, pi0_hat, k=3, s=len(lambdas))
        pi0 = float(spline(lambdas[-1]))
    except Exception:
        pi0 = float(pi0_hat[-1])
    return float(np.clip(pi0, 0.0, 1.0))


def storey_qvalues(pvals, pi0=None):
    """Storey's q-value: like BH, but scaled by the estimated null fraction
    pi0 instead of assuming pi0=1 — less conservative whenever real signal
    is present (the standard in MS metabolomics/proteomics/lipidomics vs.
    BH's worst-case assumption). Returns (qvalues, pi0_used); NaN in -> NaN out."""
    p = np.asarray(pvals, dtype=float)
    ok = np.isfinite(p)
    pv = p[ok]
    m = len(pv)
    if m == 0:
        return np.full_like(p, np.nan), np.nan
    if pi0 is None:
        pi0 = estimate_pi0(pv)
    order = np.argsort(pv)
    ranked = pv[order]
    raw = pi0 * m * ranked / (np.arange(m) + 1)
    raw = np.minimum.accumulate(raw[::-1])[::-1]  # enforce monotonicity from p=1 down
    raw = np.clip(raw, 0, 1)
    qq = np.empty(m)
    qq[order] = raw
    q = np.full_like(p, np.nan)
    q[ok] = qq
    return q, pi0


def contrast_median(feats, abund_raw, lg, idx_a, idx_b, fc_col, fdr="bh"):
    """Like lipidio.contrast(), but the reported fold-change is the per-group
    MEDIAN of the log2 values rather than the mean — more robust to a single
    outlier replicate at n=3. `fdr` selects "bh" (pi0 fixed at 1.0) or
    "storey" (estimated pi0, less conservative) — see estimate_pi0() /
    storey_qvalues() above.

    IMPORTANT: the FDR correction (either method) runs on the RAW p-values,
    BEFORE present_absent features are masked out — exactly like
    lipidio.contrast(). A present/absent feature's t-test often produces a
    spurious near-zero p-value (one side has zero variance), and those
    values legitimately occupy low ranks in the correction; masking them to
    p=1 first would silently change the ranking/pi0-estimation population
    and is NOT the same correction. present_absent is only scrubbed from
    the reported pvalue/qvalue columns afterward, for display."""
    from scipy import stats
    from statsmodels.stats.multitest import multipletests

    a, b = lg[idx_a].to_numpy(), lg[idx_b].to_numpy()
    _, pval_raw = stats.ttest_ind(a, b, axis=1, equal_var=False, nan_policy="omit")
    pval_raw = np.asarray(pval_raw, dtype=float)
    fc = np.nanmedian(a, axis=1) - np.nanmedian(b, axis=1)

    if fdr == "bh":
        _, qval, _, _ = multipletests(np.nan_to_num(pval_raw, nan=1.0), method="fdr_bh")
        pi0 = 1.0
    elif fdr == "storey":
        qval, pi0 = storey_qvalues(pval_raw)
    else:
        raise ValueError(f"unknown fdr method: {fdr!r}")

    a_off = abund_raw[idx_a].sum(axis=1).to_numpy() == 0
    b_off = abund_raw[idx_b].sum(axis=1).to_numpy() == 0
    present_absent = a_off ^ b_off
    pval = np.where(present_absent, np.nan, pval_raw)
    qval = np.where(present_absent, np.nan, qval)

    def col(name):
        return feats[name].reindex(abund_raw.index).values if name in feats.columns else None

    return pd.DataFrame({
        "feature_id": abund_raw.index,
        "lipid_name": col("lipid_name"),
        "lipid_class": col("lipid_class"),
        "mz": col("mz"),
        "rt": col("rt"),
        "n_a": len(idx_a),
        "n_b": len(idx_b),
        fc_col: fc,
        "pvalue": pval,
        "qvalue": qval,
        "pi0": pi0,
        "present_absent": present_absent,
    })


def final_class(feats: pd.DataFrame) -> pd.Series:
    mapped = METABOSCAPE_DIR / "features_mapped.csv"
    if mapped.exists():
        m = pd.read_csv(mapped, index_col="feature_id")
        if "final_class" in m.columns:
            return m["final_class"].reindex(feats.index)
    return feats.get("lipid_class", pd.Series(index=feats.index, dtype=object))


XLIM = 5.0        # data clip; points beyond it are drawn as edge triangles, not dropped
XLIM_PAD = 0.2    # extra axis margin beyond XLIM so clipped triangles aren't cut off by the frame


def draw_panel(ax, df, clone, group_label, xlim=XLIM):
    fc = df["log2fc_clone_vs_ctrl"].to_numpy()
    logp = -np.log10(df["pvalue"].to_numpy())
    sig = ((df.qvalue < 0.05) & (df["log2fc_clone_vs_ctrl"].abs() > 1)).to_numpy()
    x_plot = np.clip(fc, -xlim, xlim)
    out_hi, out_lo = fc > xlim, fc < -xlim
    inb = ~(out_hi | out_lo)

    def grp(mask, marker, size, color, alpha, label=None):
        if mask.any():
            ax.scatter(x_plot[mask], logp[mask], marker=marker, s=size, c=color,
                       alpha=alpha, lw=0, label=label)

    grp(inb & ~sig, "o", 8, C_ANN, 0.6, "not sig")
    grp(out_hi & ~sig, ">", 9, C_ANN, 0.6)
    grp(out_lo & ~sig, "<", 9, C_ANN, 0.6)
    grp(inb & sig, "o", 12, C_SIG, 0.85, "q<0.05 & |lfc|>1")
    grp(out_hi & sig, ">", 15, C_SIG, 0.9)
    grp(out_lo & sig, "<", 15, C_SIG, 0.9)

    n_pa = int(df.present_absent.sum())
    n_clip = int(out_hi.sum() + out_lo.sum())
    footer = f"+{n_pa} present/absent" if n_pa else ""
    if n_clip:
        footer = (footer + f", {n_clip} clipped at ±{xlim:g}") if footer else f"{n_clip} clipped at ±{xlim:g}"
    if footer:
        ax.text(0.98, 0.03, footer, transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6.5, color="#555")
    ax.axhline(-np.log10(0.05), ls="--", lw=0.6, c="k", zorder=0)
    ax.axvline(1, ls="--", lw=0.6, c="k", zorder=0)
    ax.axvline(-1, ls="--", lw=0.6, c="k", zorder=0)
    ax.set_xlim(-xlim - XLIM_PAD, xlim + XLIM_PAD)
    ax.text(0.02, 0.97,
            f"{clone} / {group_label}\nn={df.n_a.iloc[0]} vs {df.n_b.iloc[0]}, "
            f"sig={int(sig.sum())}, π0={df.pi0.iloc[0]:.2f}",
            transform=ax.transAxes, va="top", ha="left", fontsize=7.5,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#ccc", alpha=0.85))


def strip_inner_axes(axes):
    """R x C grid, sharex/sharey: drop the y-axis (spine+ticks) on every
    column but the first, and the x-axis (spine+ticks) on every row but the
    last — those ticks only ever repeat what the left column / bottom row
    already show."""
    for r in range(axes.shape[0]):
        for c in range(axes.shape[1]):
            ax = axes[r, c]
            if not ax.axison:  # an "insufficient replicates" panel already off
                continue
            if c != 0:
                ax.spines["left"].set_visible(False)
                ax.tick_params(axis="y", left=False, labelleft=False)
            if r != axes.shape[0] - 1:
                ax.spines["bottom"].set_visible(False)
                ax.tick_params(axis="x", bottom=False, labelbottom=False)


def add_legend(fig, axes):
    """Figure-level legend built from ALL panels' handles, deduped by label —
    a per-axis legend silently drops an entry whenever that one panel happens
    to have zero points of that kind (e.g. zero sig hits)."""
    handles, labels = [], []
    for ax in axes.flat:
        for h, l in zip(*ax.get_legend_handles_labels()):
            if l not in labels:
                handles.append(h)
                labels.append(l)
    if handles:
        fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.99, 0.965),
                   frameon=True, fontsize=7.5, markerscale=1.3)


def make_figure(feats, abund_od, lg_od, bio_od, fclass, fraction, treatment):
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 8.4), sharex=True, sharey=True)
    any_panel = False
    for r, clone in enumerate(CLONES):
        a_idx = cols_for(bio_od, clone, fraction, treatment)
        for c, (group_label, by_fraction) in enumerate(CONTROL_GROUPS.items()):
            ax = axes[r, c]
            ctrl_strain = by_fraction[fraction]
            b_idx = cols_for(bio_od, ctrl_strain, fraction, treatment)
            if len(a_idx) < 2 or len(b_idx) < 2:
                ax.text(0.5, 0.5, "insufficient replicates", ha="center", va="center",
                        transform=ax.transAxes, fontsize=8, color="#999")
                ax.set_axis_off()
                continue
            df = contrast_median(feats, abund_od, lg_od, a_idx, b_idx, fc_col="log2fc_clone_vs_ctrl")
            df["final_class"] = fclass.reindex(df["feature_id"]).values
            draw_panel(ax, df, clone, group_label)
            any_panel = True
            if r == 1:
                ax.set_xlabel("median log2FC (clone / control)")
            if c == 0:
                ax.set_ylabel(f"{clone}\n-log10 p")
            if r == 0:
                ax.set_title(group_label, fontsize=9.5)
    strip_inner_axes(axes)
    add_legend(fig, axes)
    fig.suptitle(
        f"Per-feature clone-vs-control volcano — {FRACTION_TITLE[fraction]}, "
        f"{TREATMENT_TITLE[treatment]} (OD-normalized, {PRIMARY_OD})",
        fontsize=10.5, y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig, any_panel


def main():
    feats, abund_raw, bio = load_bio(source="metaboscape", polarity="merged")
    fclass = final_class(feats)

    od = od_map(PRIMARY_OD)
    abund_od = od_normalize(abund_raw, PRIMARY_OD)
    bio_od = bio.loc[abund_od.columns]
    lg_od = log2(abund_od)

    combos = [
        ("P", "ctrl", "01_pellet_control"),
        ("P", "tol", "02_pellet_toluene"),
        ("S", "ctrl", "03_supernatant_control"),
        ("S", "tol", "04_supernatant_toluene"),
    ]
    for fraction, treatment, stem in combos:
        fig, any_panel = make_figure(feats, abund_od, lg_od, bio_od, fclass, fraction, treatment)
        if not any_panel:
            print(f"[skip] {stem}: no eligible comparisons")
            plt.close(fig)
            continue
        for ext in ("png", "svg"):
            fig.savefig(PUB / f"{stem}.{ext}", dpi=170, bbox_inches="tight")
        plt.close(fig)
        print(f"[publish] wrote {PUB / stem}.png (+ .svg)")


if __name__ == "__main__":
    main()

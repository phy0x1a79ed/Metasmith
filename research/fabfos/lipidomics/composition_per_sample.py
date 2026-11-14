"""Per-SAMPLE relative lipid composition (all 48 bio samples).

For each sample, break the mapped-lipid signal down by lipid-class family as a
fraction of that sample's total mapped signal. Relative composition is a
WITHIN-SAMPLE ratio, so it is invariant to any per-sample scalar normalization
(median-norm or OD-norm both cancel) -- we compute it straight from raw areas.

Outputs (under processed/metaboscape/composition/):
  - per_sample_composition.csv        48 samples x class-family fractions (+ mapped_total)
  - per_sample_family_long.csv        long form (sample, family, frac) for plotting
  - group_composition_mean.csv        per (fraction,strain,treatment) mean +/- sd of each family
  - composition_shift_stats.csv       tol-vs-ctrl and clone-vs-parent per-family tests
and data/fabfos/runs/scadc_lipidomics_figures/composition_per_sample_metaboscape.png (stacked bars, P & S panels).

CAVEATS (annotation ceiling): only 150/2180 features carry a final_class; ~87 are
chain-resolved. No cardiolipin in the table; PC calls are low-confidence (E. coli
makes little PC). Fractions are of the MAPPED signal only, not the whole lipidome.

Env: p312. Run from the project dir:
  mamba run -n p312 python research/fabfos/lipidomics/composition_per_sample.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipidio import load_bio  # noqa: E402

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
OUT = M / "composition"
FIG = Path("data/fabfos/runs/scadc_lipidomics_figures/composition_per_sample_metaboscape.png")
PARENT = {"P": "Epi300", "S": "ESi300"}
CLONES = ("Clone1", "Clone2")

# final_class -> display family. Order controls stack order + legend.
FAMILY = {
    "PE": "PE", "O-PE": "PE", "PE-P": "PE", "PE-NMe": "PE",
    "PG": "PG", "O-PG": "PG",
    "PC": "PC", "O-PC": "PC", "PC-P": "PC",
    "PS": "PS", "O-PS": "PS",
    "PA": "PA", "O-PA": "PA",
    "LPE": "Lyso", "LPC": "Lyso", "LPG": "Lyso", "LPA": "Lyso", "MAG": "Lyso",
    "HBMP": "HBMP",
    "TAG": "Neutral", "DAG": "Neutral", "O-DG": "Neutral",
    "Ubiquinones": "Redox/prenol", "Vitamin K": "Redox/prenol", "Vitamin E": "Redox/prenol",
}
FAM_ORDER = ["PE", "PG", "PC", "PS", "PA", "HBMP", "Lyso", "Neutral", "Redox/prenol", "Other"]
FAM_COLOR = {
    "PE": "#2a6f7f", "PG": "#3d9aab", "PC": "#e0a458", "PS": "#8c5a9e",
    "PA": "#c05746", "HBMP": "#6a8d3f", "Lyso": "#d94f4f", "Neutral": "#9a9a55",
    "Redox/prenol": "#4a7ab5", "Other": "#b8b8b8",
}
# anionic families (PG, PA, PS, HBMP) -- the E. coli solvent-tolerance lever.
ANIONIC_FAM = {"PG", "PA", "PS", "HBMP"}


def sample_order(bio):
    """Deterministic P-then-S, strain, ctrl-then-tol, rep ordering."""
    strain_rank = {"Epi300": 0, "EpCC1": 1, "Clone1": 2, "Clone2": 3,
                   "ESi300": 0, "ESCC1": 1}
    tr_rank = {"ctrl": 0, "tol": 1}
    keys = []
    for s in bio.index:
        r = bio.loc[s]
        keys.append((0 if r.fraction == "P" else 1, strain_rank[r.strain],
                     tr_rank[r.treatment], int(r.replicate), s))
    return [k[-1] for k in sorted(keys)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    feats, abund, bio = load_bio(source="metaboscape", polarity="merged")
    fm = pd.read_csv(M / "features_mapped.csv", index_col="feature_id")

    cls = fm["final_class"].reindex(abund.index)
    fam = cls.map(FAMILY).where(cls.isna() | cls.map(FAMILY).notna(), "Other")
    fam = cls.map(lambda c: FAMILY.get(c, "Other") if pd.notna(c) else np.nan)
    mapped = cls.notna()
    print(f"[comp] {int(mapped.sum())} mapped features across {len(FAM_ORDER)} families; "
          f"{abund.shape[1]} samples")

    # --- per-sample family fractions (raw areas; within-sample ratio) ----------
    A = abund[mapped]                      # mapped features only
    famv = fam[mapped]
    per_fam = A.groupby(famv).sum()        # family x sample  (raw summed area)
    tot = per_fam.sum(axis=0)              # per-sample mapped total
    frac = per_fam.divide(tot, axis=1)     # within-sample fractions
    frac = frac.reindex(FAM_ORDER).fillna(0.0)
    frac.index.name = "family"

    order = sample_order(bio)
    frac = frac[order]
    comp = frac.T.copy()                   # sample x family
    comp["mapped_total_area"] = tot.reindex(order).values
    comp["anionic_frac"] = frac.reindex(list(ANIONIC_FAM)).sum().reindex(order).values
    for c in ("strain", "treatment", "fraction", "replicate"):
        comp[c] = bio.loc[order, c].values
    comp.index.name = "sample"
    comp.to_csv(OUT / "per_sample_composition.csv")

    longf = frac.reset_index().melt(id_vars="family", var_name="sample", value_name="frac")
    longf.to_csv(OUT / "per_sample_family_long.csv", index=False)

    # --- group means +/- sd ----------------------------------------------------
    grp_rows = []
    g = comp.groupby(["fraction", "strain", "treatment"])
    for fam_name in FAM_ORDER + ["anionic_frac"]:
        col = fam_name
        for (fr, st, tr), sub in g:
            grp_rows.append(dict(fraction=fr, strain=st, treatment=tr, family=fam_name,
                                 mean=float(sub[col].mean()), sd=float(sub[col].std(ddof=1)),
                                 n=len(sub)))
    grp = pd.DataFrame(grp_rows)
    grp.to_csv(OUT / "group_composition_mean.csv", index=False)

    # --- shift stats: tol vs ctrl (within strain) & clone vs parent (within tr) --
    from scipy import stats as ss
    stat_rows = []

    def frac_vec(st, tr, fr, fam_name):
        idx = comp[(comp.strain == st) & (comp.treatment == tr) &
                   (comp.fraction == fr)].index
        return comp.loc[idx, fam_name].to_numpy()

    fam_cols = FAM_ORDER + ["anionic_frac"]
    for fr in ("P", "S"):
        strains = [PARENT[fr], ("EpCC1" if fr == "P" else "ESCC1")] + list(CLONES)
        # toluene effect within each strain
        for st in strains:
            for fam_name in fam_cols:
                a, b = frac_vec(st, "tol", fr, fam_name), frac_vec(st, "ctrl", fr, fam_name)
                if len(a) < 2 or len(b) < 2:
                    continue
                t, p = ss.ttest_ind(a, b, equal_var=False)
                stat_rows.append(dict(test="tol_vs_ctrl", fraction=fr, strain=st,
                                      family=fam_name, mean_a=a.mean(), mean_b=b.mean(),
                                      delta=a.mean() - b.mean(), pvalue=float(p)))
        # clone vs parent within each treatment
        par = PARENT[fr]
        for cl in CLONES:
            for tr in ("ctrl", "tol"):
                for fam_name in fam_cols:
                    a, b = frac_vec(cl, tr, fr, fam_name), frac_vec(par, tr, fr, fam_name)
                    if len(a) < 2 or len(b) < 2:
                        continue
                    t, p = ss.ttest_ind(a, b, equal_var=False)
                    stat_rows.append(dict(test=f"{cl}_vs_parent", fraction=fr, strain=cl,
                                          treatment=tr, family=fam_name,
                                          mean_a=a.mean(), mean_b=b.mean(),
                                          delta=a.mean() - b.mean(), pvalue=float(p)))
    st_df = pd.DataFrame(stat_rows)
    from statsmodels.stats.multitest import multipletests
    st_df["qvalue"] = np.nan
    for _, gi in st_df.groupby("test"):
        st_df.loc[gi.index, "qvalue"] = multipletests(
            gi.pvalue.fillna(1.0), method="fdr_bh")[1]
    st_df.to_csv(OUT / "composition_shift_stats.csv", index=False)

    # --- acyl-chain axis: within-sample weighted mean unsaturation + chain length --
    # (weights are within-sample ratios -> also normalization-invariant). This is the
    # classic solvent-tolerance readout the headgroup/class view collapses.
    chain = _chain_axis(abund, fm, bio, OUT)

    # --- compositional distance: total-variation between mean vectors ----------
    def mean_vec(st, tr, fr):
        return frac[[c for c in order if c in
                     comp[(comp.strain == st) & (comp.treatment == tr) &
                          (comp.fraction == fr)].index]].mean(axis=1)
    tv_rows = []
    for fr in ("P", "S"):
        par = PARENT[fr]
        for tr in ("ctrl", "tol"):
            base = mean_vec(par, tr, fr)
            for st in [("EpCC1" if fr == "P" else "ESCC1")] + list(CLONES):
                v = mean_vec(st, tr, fr)
                tv_rows.append(dict(fraction=fr, treatment=tr, strain=st,
                                    tv_vs_parent=0.5 * float((v - base).abs().sum())))
        # toluene shift (tol vs ctrl) within each strain
        for st in [par, ("EpCC1" if fr == "P" else "ESCC1")] + list(CLONES):
            v_t, v_c = mean_vec(st, "tol", fr), mean_vec(st, "ctrl", fr)
            tv_rows.append(dict(fraction=fr, treatment="tol_vs_ctrl", strain=st,
                                tv_vs_parent=0.5 * float((v_t - v_c).abs().sum())))
    tv = pd.DataFrame(tv_rows)
    tv.to_csv(OUT / "composition_tv_distance.csv", index=False)

    _figure(frac, comp, order, bio)
    _report(comp, grp, st_df, tv, chain)


def _chain_axis(abund, fm, bio, out):
    """Per-sample abundance-weighted mean double-bond count and chain length over
    the chain-resolved features, + tol-vs-ctrl and clone-vs-parent tests (FDR).
    Weights are within-sample fractions, so both metrics are scalar-invariant."""
    from scipy import stats as ss
    from statsmodels.stats.multitest import multipletests
    db = fm["total_db"].reindex(abund.index)
    cc = fm["total_carbon"].reindex(abund.index)
    mask = db.notna() & cc.notna()
    A = abund[mask]
    w = A.divide(A.sum(axis=0), axis=1)             # per-sample weights sum to 1
    d = bio.copy()
    d["wmean_db"] = (w.mul(db[mask], axis=0)).sum(axis=0).reindex(d.index)
    d["wmean_C"] = (w.mul(cc[mask], axis=0)).sum(axis=0).reindex(d.index)
    d[["strain", "treatment", "fraction", "replicate", "wmean_db", "wmean_C"]].to_csv(
        out / "chain_axis_per_sample.csv")

    rows = []
    for metric in ("wmean_db", "wmean_C"):
        for fr in ("P", "S"):
            par = PARENT[fr]
            strains = [par, ("EpCC1" if fr == "P" else "ESCC1")] + list(CLONES)
            for st in strains:                       # tol vs ctrl
                a = d[(d.strain == st) & (d.fraction == fr) & (d.treatment == "tol")][metric]
                b = d[(d.strain == st) & (d.fraction == fr) & (d.treatment == "ctrl")][metric]
                if len(a) > 1 and len(b) > 1:
                    rows.append(dict(metric=metric, test="tol_vs_ctrl", fraction=fr, strain=st,
                                     treatment=None, mean_a=a.mean(), mean_b=b.mean(),
                                     delta=a.mean() - b.mean(), pvalue=float(ss.ttest_ind(a, b, equal_var=False)[1])))
            for cl in CLONES:                        # clone vs parent, per treatment
                for tr in ("ctrl", "tol"):
                    a = d[(d.strain == cl) & (d.fraction == fr) & (d.treatment == tr)][metric]
                    b = d[(d.strain == par) & (d.fraction == fr) & (d.treatment == tr)][metric]
                    if len(a) > 1 and len(b) > 1:
                        rows.append(dict(metric=metric, test=f"{cl}_vs_parent", fraction=fr, strain=cl,
                                         treatment=tr, mean_a=a.mean(), mean_b=b.mean(),
                                         delta=a.mean() - b.mean(), pvalue=float(ss.ttest_ind(a, b, equal_var=False)[1])))
    cs = pd.DataFrame(rows)
    cs["qvalue"] = np.nan
    for _, gi in cs.groupby("metric"):
        cs.loc[gi.index, "qvalue"] = multipletests(gi.pvalue.fillna(1.0), method="fdr_bh")[1]
    cs.to_csv(out / "chain_axis_stats.csv", index=False)
    _chain_figure(d)
    return dict(per_sample=d, stats=cs)


def _chain_figure(d):
    """Chain length vs unsaturation scatter of the group means -- shows the two
    clones diverging on membrane order in opposite directions."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"wspace": 0.22})
    col = {"Epi300": "#333333", "ESi300": "#333333", "EpCC1": "#888888",
           "ESCC1": "#888888", "Clone1": "#c05746", "Clone2": "#2a6f7f"}
    g = d.groupby(["fraction", "strain", "treatment"]).agg(
        db=("wmean_db", "mean"), C=("wmean_C", "mean")).reset_index()
    for ax, fr in zip(axes, ("P", "S")):
        sub = g[g.fraction == fr]
        for _, r in sub.iterrows():
            m = "o" if r.treatment == "ctrl" else "^"
            ax.scatter(r.C, r.db, c=col[r.strain], marker=m, s=90,
                       edgecolor="white", linewidth=0.6, zorder=3)
        # connect ctrl->tol within strain
        for st in sub.strain.unique():
            s2 = sub[sub.strain == st].set_index("treatment")
            if {"ctrl", "tol"} <= set(s2.index):
                ax.plot([s2.loc["ctrl", "C"], s2.loc["tol", "C"]],
                        [s2.loc["ctrl", "db"], s2.loc["tol", "db"]],
                        c=col[st], lw=1.0, alpha=0.5, zorder=2)
            lab = st
            rr = s2.iloc[0]
            ax.annotate(lab, (rr.C, rr.db), fontsize=8, xytext=(4, 4),
                        textcoords="offset points", color=col[st])
        ax.set_xlabel("mean chain length (C)")
        ax.set_ylabel("mean unsaturation (C=C per lipid)" if fr == "P" else "")
        ax.set_title(f"{'Pellet (cell)' if fr=='P' else 'Supernatant'} fraction", fontsize=11)
        ax.grid(True, lw=0.3, alpha=0.4)
    fig.suptitle("Acyl-chain architecture: clones diverge on membrane order "
                 "(o = control, ^ = toluene)", fontsize=12, y=0.99)
    p = Path("data/fabfos/runs/scadc_lipidomics_figures/composition_chain_axis_metaboscape.png")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] wrote {p}")


def _figure(frac, comp, order, bio):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"wspace": 0.12})
    for ax, fr in zip(axes, ("P", "S")):
        cols = [s for s in order if comp.loc[s, "fraction"] == fr]
        x = np.arange(len(cols))
        bottom = np.zeros(len(cols))
        for fam_name in FAM_ORDER:
            vals = frac.loc[fam_name, cols].to_numpy()
            ax.bar(x, vals, bottom=bottom, width=0.8, color=FAM_COLOR[fam_name],
                   edgecolor="white", linewidth=0.3, label=fam_name)
            bottom += vals
        labels = [f"{comp.loc[s,'strain']} {comp.loc[s,'treatment']} r{comp.loc[s,'replicate']}"
                  for s in cols]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=90, fontsize=7)
        ax.set_ylim(0, 1)
        ax.set_title(f"{'Pellet (cell)' if fr=='P' else 'Supernatant'} fraction", fontsize=11)
        ax.set_ylabel("fraction of mapped lipid signal" if fr == "P" else "")
        # separate strains with light vlines
        prev = None
        for i, s in enumerate(cols):
            stn = comp.loc[s, "strain"]
            if prev is not None and stn != prev:
                ax.axvline(i - 0.5, color="0.6", lw=0.6)
            prev = stn
    handles = [Patch(facecolor=FAM_COLOR[f], label=f) for f in FAM_ORDER]
    axes[1].legend(handles=handles, bbox_to_anchor=(1.01, 1), loc="upper left",
                   fontsize=8, frameon=False, title="class family")
    fig.suptitle("Per-sample relative lipid composition (mapped features only; "
                 "normalization-invariant)", fontsize=12, y=0.99)
    fig.savefig(FIG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] wrote {FIG}")


def _report(comp, grp, st_df, tv, chain):
    pd.set_option("display.width", 190, "display.max_columns", 30)
    print("\n=== per-sample mapped total area (within-sample ratio is scalar-invariant) ===")
    print("  (fractions below are unaffected by OD/median normalization)")

    print("\n=== group-mean composition (fraction of mapped signal) ===")
    piv = grp[grp.family.isin(FAM_ORDER)].pivot_table(
        index=["fraction", "strain", "treatment"], columns="family", values="mean")
    piv = piv[[c for c in FAM_ORDER if c in piv.columns]]
    print((100 * piv).round(1).to_string())

    print("\n=== anionic (PG+PA+PS+HBMP) fraction, mean by group ===")
    an = grp[grp.family == "anionic_frac"].pivot_table(
        index=["fraction", "strain"], columns="treatment", values="mean")
    print((100 * an).round(1).to_string())

    print("\n=== toluene shift (tol-vs-ctrl) per family, |delta|>0.02 & p<0.10 ===")
    tv1 = st_df[(st_df.test == "tol_vs_ctrl") & (st_df.delta.abs() > 0.02) & (st_df.pvalue < 0.10)]
    if len(tv1):
        print(tv1[["fraction", "strain", "family", "mean_b", "mean_a", "delta", "pvalue"]]
              .round(4).to_string(index=False))
    else:
        print("  (none)")

    print("\n=== clone-vs-parent (CTRL) per family, |delta|>0.02 & p<0.10 ===")
    cv = st_df[(st_df.test.str.contains("_vs_parent")) & (st_df.get("treatment") == "ctrl")
               & (st_df.delta.abs() > 0.02) & (st_df.pvalue < 0.10)]
    if len(cv):
        print(cv[["fraction", "strain", "family", "mean_b", "mean_a", "delta", "pvalue"]]
              .round(4).to_string(index=False))
    else:
        print("  (none)")

    print("\n=== family shifts surviving FDR q<0.10 (the only real headgroup patterns) ===")
    sig = st_df[st_df.qvalue < 0.10].sort_values("qvalue")
    if len(sig):
        print(sig[["test", "fraction", "strain", "treatment", "family",
                   "mean_b", "mean_a", "delta", "pvalue", "qvalue"]].round(4).to_string(index=False))
    else:
        print("  (none survive FDR)")

    print("\n=== ACYL-CHAIN axis (weighted mean, scalar-invariant) group means ===")
    d = chain["per_sample"]
    for metric, lab in [("wmean_db", "unsaturation (mean # C=C)"), ("wmean_C", "chain length (mean C)")]:
        piv = d.groupby(["fraction", "strain", "treatment"])[metric].mean().unstack("treatment")
        print(f"  -- {lab} --")
        print(piv.round(3).to_string())
    print("\n=== chain-axis tests, nominal p<0.05 (q shown) ===")
    cs = chain["stats"]
    sg = cs[cs.pvalue < 0.05].sort_values(["metric", "pvalue"])
    print(sg[["metric", "test", "fraction", "strain", "treatment",
              "mean_b", "mean_a", "delta", "pvalue", "qvalue"]].round(4).to_string(index=False)
          if len(sg) else "  (none)")

    print("\n=== compositional distance (total variation, 0..1) ===")
    print("  clone/EV vs parent, and toluene shift within each strain:")
    print(tv.round(3).to_string(index=False))
    print(f"\n[comp] wrote -> {OUT}/  (per_sample_composition, group_composition_mean, "
          f"composition_shift_stats, composition_tv_distance, chain_axis_per_sample, chain_axis_stats)")


if __name__ == "__main__":
    main()

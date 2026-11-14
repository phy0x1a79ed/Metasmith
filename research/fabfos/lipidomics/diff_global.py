"""Global multi-group screen — does a feature vary anywhere in the condition matrix?

Within each fraction (P, S separately — different matrices), runs a one-way ANOVA
(F-test) per feature across all condition groups (strain x treatment) on the log2
matrix, BH-corrects across the feature set. This is the "full matrix" omnibus: it
flags features that differ across *any* condition, independent of the pairwise
contrasts. A non-parametric Kruskal-Wallis is also computed for reference — it is
heavily de-powered here by rank ties from the gap-filled zeros, so ANOVA is the
primary screen and Kruskal the conservative cross-check.

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/diff_global.py metaboscape
"""
from __future__ import annotations
import sys

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from lipidio import load_bio, median_normalize, log2, resolve_source

FAMILY = "diff_global"


def run(arg: str) -> None:
    source, polarity, out_base, tag = resolve_source(arg)
    feats, abund, bio = load_bio(source=source, polarity=polarity)
    lg = log2(median_normalize(abund))

    rows = []
    for fraction, fbio in bio.groupby("fraction"):
        groups = [g.index.tolist() for _, g in fbio.groupby(["strain", "treatment"])]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            continue
        mats = [lg[g].to_numpy() for g in groups]
        # primary: vectorized one-way ANOVA across groups (axis=1 = per feature)
        fstat, pvals = stats.f_oneway(*mats, axis=1)
        pvals = np.nan_to_num(np.asarray(pvals, dtype=float), nan=1.0)
        _, q, _, _ = multipletests(pvals, method="fdr_bh")
        # reference: Kruskal-Wallis (rank-tie de-powered) — loop, with guard
        kp = np.ones(lg.shape[0])
        for i in range(lg.shape[0]):
            try:
                _, kp[i] = stats.kruskal(*[m[i, :] for m in mats])
            except ValueError:
                kp[i] = 1.0
        _, kq, _, _ = multipletests(np.nan_to_num(kp, nan=1.0), method="fdr_bh")
        rows.append(pd.DataFrame({
            "feature_id": lg.index,
            "lipid_name": feats["lipid_name"].reindex(lg.index).values,
            "lipid_class": feats["lipid_class"].reindex(lg.index).values,
            "mz": feats["mz"].reindex(lg.index).values,
            "rt": feats["rt"].reindex(lg.index).values,
            "fraction": fraction,
            "n_groups": len(groups),
            "anova_F": np.asarray(fstat, dtype=float),
            "pvalue": pvals,
            "qvalue": q,
            "kruskal_p": kp,
            "kruskal_q": kq,
        }))

    if not rows:
        print("no fraction with >=2 groups", file=sys.stderr)
        return
    full = pd.concat(rows, ignore_index=True)
    full["contrast_family"] = FAMILY
    csv = out_base / f"{FAMILY}_{tag}.csv"
    full.to_csv(csv, index=False)
    print(f"wrote {csv} ({len(full)} rows)")
    summ = full.groupby("fraction").apply(
        lambda d: pd.Series({"anova_q<0.05": int((d.qvalue < 0.05).sum()),
                             "kruskal_q<0.05": int((d.kruskal_q < 0.05).sum())}),
        include_groups=False)
    print("features significant per fraction:\n", summ.to_string())


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "metaboscape")

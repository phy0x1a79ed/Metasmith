"""Strain x toluene interaction: does toluene ERASE the clone phenotype, or just
DE-POWER the test?

The ctrl-only clone-vs-parent signal vanishes under toluene (diff_strain: 0 sig at
tol in the pellet). Two explanations, which a one-factor test can't separate:
  (a) true interaction — toluene genuinely removes the clone effect, OR
  (b) variance inflation — the toluene replicates are noisier (n=3), so EVERY test
      loses power (recall diff_toluene gave 0 sig for ALL strains incl. the parent).

For each feature and each engineered strain (vs its fraction-matched parent), fit a
2x2 OLS on log2 abundance:  y ~ strain + treatment + strain:treatment  (12 obs).
Report the interaction term's p (BH-corrected per fraction x strain) AND the ratio
of toluene-arm to control-arm residual spread, so "no fold-change survived" can be
attributed to (a) vs (b).

Verdict logic: if few/no interactions are BH-significant AND tol-arm variance is
systematically larger than ctrl-arm, the disappearance is de-powering, not erasure.

Env: p312. Run: mamba run -n p312 python research/fabfos/lipidomics/diff_interaction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipidio import median_normalize, log2  # noqa: E402

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
PARENT = {"P": "Epi300", "S": "ESi300"}
CLONES = ["Clone1", "Clone2"]
SAMPLE_RE = r"^(Epi300|EpCC1|ESi300|ESCC1|Clone1|Clone2)_(ctrl|tol)_(P|S)_\d$"


def bh(p):
    p = np.asarray(p, float)
    ok = np.isfinite(p)
    q = np.full_like(p, np.nan)
    pv = p[ok]
    if len(pv) == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * len(pv) / (np.arange(len(pv)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    qq = np.empty_like(ranked)
    qq[order] = np.clip(ranked, 0, 1)
    q[ok] = qq
    return q


def main():
    df = pd.read_csv(M / "features_mapped.csv")
    sample_cols = [c for c in df.columns if pd.Series([c]).str.match(SAMPLE_RE)[0]]
    lg = log2(median_normalize(df[sample_cols].fillna(0.0)))

    import statsmodels.formula.api as smf

    recs = []
    var_ratios = []
    for frac in ("P", "S"):
        parent = PARENT[frac]
        for clone in CLONES:
            cols = {}
            for st in (parent, clone):
                for tr in ("ctrl", "tol"):
                    cs = [f"{st}_{tr}_{frac}_{r}" for r in (1, 2, 3)
                          if f"{st}_{tr}_{frac}_{r}" in lg.columns]
                    cols[(st, tr)] = cs
            # tol vs ctrl residual-spread ratio (pooled across both strains)
            for fid, row in lg.iterrows():
                data = []
                for (st, tr), cs in cols.items():
                    for c in cs:
                        data.append((row[c], 0 if st == parent else 1,
                                     0 if tr == "ctrl" else 1))
                d = pd.DataFrame(data, columns=["y", "strain", "treat"])
                if d["y"].nunique() < 2 or len(d) < 8:
                    continue
                try:
                    fit = smf.ols("y ~ strain * treat", data=d).fit()
                    pi = fit.pvalues.get("strain:treat", np.nan)
                except Exception:
                    pi = np.nan
                recs.append(dict(fraction=frac, clone=clone, feature_id=fid,
                                 final_class=df.loc[fid, "final_class"],
                                 p_interaction=pi))
            # variance: tol-arm vs ctrl-arm SD across all features (both strains)
            ctrl_cols = cols[(parent, "ctrl")] + cols[(clone, "ctrl")]
            tol_cols = cols[(parent, "tol")] + cols[(clone, "tol")]
            sd_ctrl = lg[ctrl_cols].std(axis=1).median()
            sd_tol = lg[tol_cols].std(axis=1).median()
            var_ratios.append(dict(fraction=frac, clone=clone,
                                   median_sd_ctrl=round(sd_ctrl, 3),
                                   median_sd_tol=round(sd_tol, 3),
                                   tol_over_ctrl=round(sd_tol / sd_ctrl, 2)))

    res = pd.DataFrame(recs)
    res["q_interaction"] = np.nan
    for (fr, cl), g in res.groupby(["fraction", "clone"]):
        res.loc[g.index, "q_interaction"] = bh(g["p_interaction"].values)
    res.to_csv(M / "diff_interaction_metaboscape.csv", index=False)

    print("=== interaction (strain x treatment) significant features per cell ===")
    for (fr, cl), g in res.groupby(["fraction", "clone"]):
        nsig = int((g["q_interaction"] < 0.05).sum())
        ntest = int(g["p_interaction"].notna().sum())
        print(f"  {cl} vs {PARENT[fr]} [{fr}]: {nsig} interaction-sig / {ntest} tested")
    print("\n=== toluene-arm vs control-arm replicate spread (median per-feature SD) ===")
    print(pd.DataFrame(var_ratios).to_string(index=False))
    print(f"\n[interaction] wrote diff_interaction_metaboscape.csv -> {M}")


if __name__ == "__main__":
    main()

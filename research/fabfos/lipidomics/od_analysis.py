"""OD-normalized lipidomics: how the toluene effect differs in Clone1/Clone2 vs EPI300.

Andras Szeitz's recipe (email 2026-07-08): divide the peak-area counts by each sample's
OD600, i.e. lipid signal per unit biomass. This matters here because 0.1% toluene collapses
the biomass of the EPI300 parent and the empty-vector control (~3-5x lower OD) but NOT the
clones (see od_values.csv / method doc). Raw peak areas therefore confound biomass with
per-cell composition; median-normalization hides it by forcing equal totals. OD-normalization
uses the measured biomass instead, so a per-cell toluene effect is separated from the growth
effect.

Outputs (processed/metaboscape/od/):
  - od_total_lipid.csv          total lipid signal per OD, per strain x treatment x fraction
  - od_toluene_metaboscape.csv  tol/ctrl per (strain, fraction), OD-normalized, Welch + BH
  - od_interaction_metaboscape.csv  strain x treatment interaction (engineered vs parent)
  - od_norm_comparison.csv      robustness: #sig + total-lipid ratio under
                                raw / median / OD-per-rep / OD-geomean
  - volcano/*.png

Env: p312. Run from project dir:
  mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/od_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipidio import (  # noqa: E402
    load_bio, load_od, od_map, od_normalize, median_normalize, log2,
    contrast, volcano, METABOSCAPE_DIR,
)

OUT = METABOSCAPE_DIR / "od"
PARENT = {"P": "Epi300", "S": "ESi300"}          # fraction -> parent strain
ENGINEERED = {"P": ["EpCC1", "Clone1", "Clone2"],
              "S": ["ESCC1", "Clone1", "Clone2"]}
SIG = lambda df, fc: (df["qvalue"] < 0.05) & (df[fc].abs() > 1)


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


def _final_class(feats: pd.DataFrame) -> pd.Series:
    """Prefer the RefMet/Goslin final_class (features_mapped.csv) over the raw shorthand."""
    mapped = METABOSCAPE_DIR / "features_mapped.csv"
    if mapped.exists():
        m = pd.read_csv(mapped, index_col="feature_id")
        if "final_class" in m.columns:
            return m["final_class"].reindex(feats.index)
    return feats.get("lipid_class", pd.Series(index=feats.index, dtype=object))


def cols_for(bio, strain, fraction, treatment):
    c = bio[(bio.strain == strain) & (bio.fraction == fraction) &
            (bio.treatment == treatment)]
    return c.index.tolist()


def total_lipid_per_od(abund_raw, bio, od) -> pd.DataFrame:
    """Sum of raw peak areas per sample / its OD, summarized per group, plus tol/ctrl ratio."""
    tot = abund_raw.sum(axis=0)                       # total signal per sample
    rows = []
    for frac in ("P", "S"):
        for strain in [PARENT[frac]] + ENGINEERED[frac]:
            rec = {"fraction": frac, "strain": strain}
            per = {}
            for tr in ("ctrl", "tol"):
                cs = cols_for(bio, strain, frac, tr)
                raw = tot[cs].mean()
                per_od = (tot[cs] / od[cs]).mean()
                per[tr] = per_od
                rec[f"total_raw_{tr}"] = raw
                rec[f"total_per_od_{tr}"] = per_od
            rec["per_od_tol_over_ctrl"] = per["tol"] / per["ctrl"] if per["ctrl"] else np.nan
            rec["log2_per_od_tol_over_ctrl"] = np.log2(rec["per_od_tol_over_ctrl"])
            rows.append(rec)
    return pd.DataFrame(rows)


def toluene_contrasts(feats, abund_od, lg_od, bio, fclass) -> pd.DataFrame:
    """tol vs ctrl per (strain, fraction) on the OD-normalized matrix."""
    OUT.joinpath("volcano").mkdir(parents=True, exist_ok=True)
    rows = []
    for frac in ("P", "S"):
        for strain in [PARENT[frac]] + ENGINEERED[frac]:
            tol = cols_for(bio, strain, frac, "tol")
            ctl = cols_for(bio, strain, frac, "ctrl")
            if len(tol) < 2 or len(ctl) < 2:
                continue
            df = contrast(feats, abund_od, lg_od, tol, ctl, fc_col="log2fc_tol_vs_ctrl")
            df.insert(1, "strain", strain)
            df.insert(2, "fraction", frac)
            df["final_class"] = fclass.reindex(df["feature_id"]).values
            rows.append(df)
            volcano(df, "log2fc_tol_vs_ctrl",
                    f"OD-norm {strain} [{frac}] tol/ctrl",
                    OUT / "volcano" / f"tol_{strain}_{frac}.png")
    return pd.concat(rows, ignore_index=True)


def interaction(lg_od, bio, fclass) -> pd.DataFrame:
    """2x2 OLS (strain*treatment) per feature: engineered strain vs its fraction parent.

    The strain:treatment term is exactly log2FC_engineered(tol/ctrl) - log2FC_parent(tol/ctrl)
    — i.e. how much toluene's per-cell lipid effect differs in the clone vs the background.
    """
    import statsmodels.formula.api as smf
    recs = []
    for frac in ("P", "S"):
        parent = PARENT[frac]
        for strain in ENGINEERED[frac]:
            colmap = {}
            for st in (parent, strain):
                for tr in ("ctrl", "tol"):
                    colmap[(st, tr)] = cols_for(bio, st, frac, tr)
            for fid, row in lg_od.iterrows():
                data = []
                for (st, tr), cs in colmap.items():
                    for c in cs:
                        data.append((row[c], 0 if st == parent else 1,
                                     0 if tr == "ctrl" else 1))
                d = pd.DataFrame(data, columns=["y", "strain", "treat"])
                if d["y"].nunique() < 2 or len(d) < 8:
                    continue
                try:
                    fit = smf.ols("y ~ strain * treat", data=d).fit()
                    pi = fit.pvalues.get("strain:treat", np.nan)
                    bi = fit.params.get("strain:treat", np.nan)
                except Exception:
                    pi, bi = np.nan, np.nan
                recs.append(dict(fraction=frac, strain=strain, parent=parent,
                                 feature_id=fid, final_class=fclass.get(fid),
                                 interaction_log2=bi, p_interaction=pi))
    res = pd.DataFrame(recs)
    res["q_interaction"] = np.nan
    for (fr, st), g in res.groupby(["fraction", "strain"]):
        res.loc[g.index, "q_interaction"] = bh(g["p_interaction"].values)
    return res


def norm_comparison(feats, abund_raw, bio, od_perrep, od_geo) -> pd.DataFrame:
    """How the tol/ctrl signal changes under 4 normalizations, at the summary level:
    #sig features and the total-lipid tol/ctrl ratio, per (strain, fraction)."""
    schemes = {
        "raw":        abund_raw,
        "median":     median_normalize(abund_raw),
        "od_perrep":  od_normalize(abund_raw, "per_rep"),
        "od_geomean": od_normalize(abund_raw, "group_geomean"),
    }
    rows = []
    for frac in ("P", "S"):
        for strain in [PARENT[frac]] + ENGINEERED[frac]:
            tol = cols_for(bio, strain, frac, "tol")
            ctl = cols_for(bio, strain, frac, "ctrl")
            if len(tol) < 2 or len(ctl) < 2:
                continue
            rec = {"fraction": frac, "strain": strain}
            for name, mat in schemes.items():
                cols = [c for c in mat.columns]
                t = [c for c in tol if c in cols]
                c = [c for c in ctl if c in cols]
                lg = log2(mat[t + c])
                df = contrast(feats, mat[t + c], lg, t, c, fc_col="lfc")
                rec[f"nsig_{name}"] = int(SIG(df, "lfc").sum())
                tot = mat[t + c].sum(axis=0)
                rec[f"totlfc_{name}"] = float(np.log2(tot[t].mean() / tot[c].mean()))
            rows.append(rec)
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    feats, abund_raw, bio = load_bio(source="metaboscape", polarity="merged")
    fclass = _final_class(feats)

    # Primary normalization = group geometric-mean OD. It is assumption-free (does NOT
    # require the OD-rep index to match the lipidomics-rep index — it cancels the pairing)
    # and, for the high-OD-variance toluene parent, far more powerful than per-rep, while
    # giving the same central tol/ctrl fold-change. Per-rep (Andras's literal "individual
    # sample" recipe) is reported alongside in od_norm_comparison.csv.
    PRIMARY = "group_geomean"
    od = od_map(PRIMARY)
    abund_od = od_normalize(abund_raw, PRIMARY)
    bio_od = bio.loc[abund_od.columns]
    lg_od = log2(abund_od)

    tot = total_lipid_per_od(abund_raw, bio, od)
    tot.to_csv(OUT / "od_total_lipid.csv", index=False)

    tol = toluene_contrasts(feats, abund_od, lg_od, bio_od, fclass)
    tol.to_csv(METABOSCAPE_DIR / "od_toluene_metaboscape.csv", index=False)

    inter = interaction(lg_od, bio_od, fclass)
    inter.to_csv(METABOSCAPE_DIR / "od_interaction_metaboscape.csv", index=False)

    cmp = norm_comparison(feats, abund_raw, bio,
                          od_map("per_rep"), od_map("group_geomean"))
    cmp.to_csv(OUT / "od_norm_comparison.csv", index=False)

    # ---- console summary --------------------------------------------------------
    pd.set_option("display.width", 160, "display.max_columns", 30)
    print("\n================ OD600 growth (culture means) ================")
    g = load_od().groupby(["culture", "treatment"])["od600"].mean().unstack()
    g["pct_retained"] = (100 * g["tol"] / g["ctrl"]).round(1)
    print(g.round(3).to_string())

    print("\n================ total lipid signal per OD (mean over reps) ================")
    show = tot[["fraction", "strain", "total_per_od_ctrl", "total_per_od_tol",
                "per_od_tol_over_ctrl", "log2_per_od_tol_over_ctrl"]].copy()
    for c in show.columns[2:]:
        show[c] = show[c].astype(float).round(3)
    print(show.to_string(index=False))

    print("\n================ toluene effect per strain (OD-normalized, q<0.05 & |lfc|>1) ================")
    for (frac, strain), gdf in tol.groupby(["fraction", "strain"]):
        s = SIG(gdf, "log2fc_tol_vs_ctrl")
        up = int((s & (gdf.log2fc_tol_vs_ctrl > 0)).sum())
        dn = int((s & (gdf.log2fc_tol_vs_ctrl < 0)).sum())
        pa = int(gdf.present_absent.sum())
        print(f"  [{frac}] {strain:7s}: {int(s.sum()):3d} sig ({up} up / {dn} dn), {pa} present/absent")

    print("\n================ strain x treatment interaction vs parent (q<0.05) ================")
    for (frac, strain), gdf in inter.groupby(["fraction", "strain"]):
        nsig = int((gdf.q_interaction < 0.05).sum())
        ntest = int(gdf.p_interaction.notna().sum())
        print(f"  [{frac}] {strain:7s} vs {PARENT[frac]:7s}: {nsig:3d} interaction-sig / {ntest} tested")

    print("\n================ robustness: #sig & total-lipid log2(tol/ctrl) by normalization ================")
    print(cmp.round(2).to_string(index=False))

    print(f"\n[od_analysis] wrote outputs -> {OUT} and {METABOSCAPE_DIR}/od_*.csv")


if __name__ == "__main__":
    main()

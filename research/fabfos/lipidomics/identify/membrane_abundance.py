"""Does Clone2 carry a different membrane from the empty-vector control?

The enrichment lane asked a compositional question of seven features and could not
answer it -- n=7 has no power. This asks the same biology a different way: aggregate
the peak area over the membrane-lipid set per SAMPLE, and compare samples. The power
then comes from the three biological replicates per group, not from the feature count,
which is why this does not need the classifier to be perfect and why it is run twice --
once on the fragment-confirmed set alone, once on the >=95%-coverage classifier set.

FOUR CONDITIONS. Clone2 (n=3) against the pCC1 empty-vector control (n=3), separately
in pellet and supernatant and separately with and without toluene. pCC1 is EpCC1 in
the pellet and ESCC1 in the supernatant -- the same construct through the two
fractions, named differently upstream.

FOUR READOUTS, because proportion and amount are different questions and the OD
normalisation only touches one of them:

  A-proportion   membrane signal / total signal      is the MAKE-UP different
  A-amount       membrane signal / OD600             is there more membrane PER CELL
  B-proportion   curvature-forcing / membrane        the bilayer/non-bilayer balance
  B-amount       curvature-forcing / OD600

The two proportions are OD-INVARIANT BY CONSTRUCTION: the per-sample OD divides out
of numerator and denominator, so they are numerically identical normalised or not.
They are reported as proportions and never as "OD-normalised", because that phrasing
would tell a reader the biomass correction is doing work where it cancels exactly.
The amounts are where OD earns its place, and it is not a formality here: toluene puts
EpCC1 at OD 0.10 against Clone2's 0.41, so a raw peak-area comparison between them is
mostly a comparison of how many cells were extracted.

WHY WELCH AND NOT A PERMUTATION TEST. At 3 against 3 there are C(6,3) = 20 label
assignments, so the smallest attainable two-sided permutation p is 0.10. A permutation
test cannot return significance here no matter how large the effect. Welch's t is used
instead, and the effect size and interval lead -- at n=3 the p-value is the least
informative number on the row.

THE INTERACTION ARM. A difference under toluene and none at baseline does not
establish that toluene caused it. The contrast that does is
(Clone2 tol - Clone2 ctrl) - (pCC1 tol - pCC1 ctrl), fitted as the interaction term of
a 2x2. And Clone1 goes through the identical grid, because at n=3 an independent second
clone is worth more than any refinement of the test statistic.

Run:  mamba run -n p312 python -m identify.membrane_abundance   (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lipidio  # noqa: E402
from identify import common  # noqa: E402

PUBLISH = common.PUBLISH_DIR.parent / "07_lipid_class_enrichment"

# pCC1 is one construct that the upstream naming splits by fraction.
PCC1 = {"P": "EpCC1", "S": "ESCC1"}
FRACTION_NAME = {"P": "pellet", "S": "supernatant"}

# THE FOUR CONDITIONS. These are the scope's canonical contrast grid -- the same
# four that are the subplot columns of 05_clone_response/clone_response_storey, laid
# out in od_clone_response_volcano.make_figure. Fraction crossed with CONTRAST TYPE,
# not fraction crossed with treatment:
#   "Clone vs pCC1 (-Tol.)"  the construct effect, measured at baseline
#   "+Tol. vs -Tol"          the clone's OWN toluene response, no comparison strain
# Reusing the established grid matters because every other figure in this section is
# read against it; a private grid would put the same words on different numbers.
VS_PCC1 = "Clone vs pCC1 (-Tol.)"
VS_TOL = "+Tol. vs -Tol"
CONDITIONS = [(f, k) for f in ("P", "S") for k in (VS_PCC1, VS_TOL)]


def groups_for(clone: str, frac: str, kind: str) -> tuple[tuple, tuple]:
    """(strain, treatment) for each side of one contrast."""
    if kind == VS_PCC1:
        return (clone, "ctrl"), (PCC1[frac], "ctrl")
    return (clone, "tol"), (clone, "ctrl")


# --------------------------------------------------------------- per-sample readouts
def weights(calls: pd.DataFrame, label_set: str, weighting: str) -> pd.DataFrame:
    """Per-feature membrane and curvature-forcing weights, in [0, 1].

    `label_set`:
      tier1  -- only what MS/MS fragment evidence confirmed. No model anywhere.
      full   -- the >=95%-coverage tiered call.
    `weighting`:
      hard   -- 1/0 on the call.
      prob   -- the calibrated probability, so a feature the model is unsure about
                contributes proportionally rather than all-or-nothing.
    """
    c = calls
    if label_set == "tier1":
        mem = (c.membrane_tier == "1_massbalance") & (c.membrane == "yes")
        w_mem = mem.astype(float)
        forcing = mem & (c.curvature_tier == "1_massbalance") & \
            (c.curvature_prior == "curvature-forcing")
        w_for = forcing.astype(float)
        # Under `tier1` the denominator of B is the tier-1 membrane set whose
        # curvature was ALSO settled by fragment evidence -- otherwise the ratio
        # would divide a measured numerator by a partly unmeasured denominator.
        w_bden = (mem & (c.curvature_tier == "1_massbalance") &
                  (c.curvature_prior != "indeterminate")).astype(float)
        return pd.DataFrame({"mem": w_mem, "forcing": w_for, "b_den": w_bden},
                            index=c.index)

    p_mem = c.membrane_p.fillna(c.model_p).clip(0, 1)
    hard_mem = (c.membrane == "yes").astype(float)
    w_mem = hard_mem if weighting == "hard" else p_mem

    model_tier = c.curvature_tier == "3_model"
    p_for = np.where(model_tier, c.curv_p,
                     (c.curvature_prior == "curvature-forcing").astype(float))
    p_for = np.where(c.curvature_prior == "positive-curvature", 0.0, p_for)
    p_for = np.where(c.curvature_prior == "indeterminate", np.nan, p_for)
    hard_for = (c.curvature_prior == "curvature-forcing").astype(float)
    w_for = hard_for if weighting == "hard" else pd.Series(p_for, index=c.index).fillna(0.0)
    w_bden = (c.curvature_prior != "indeterminate").astype(float)
    return pd.DataFrame({"mem": w_mem, "forcing": w_for * w_mem,
                         "b_den": w_bden * w_mem}, index=c.index)


def per_sample(calls: pd.DataFrame, abund: pd.DataFrame, od: pd.Series,
               label_set: str, weighting: str) -> pd.DataFrame:
    """The four readouts, one row per sample."""
    w = weights(calls, label_set, weighting)
    a = abund.loc[calls.index]
    total = a.sum(axis=0)
    mem = a.mul(w["mem"], axis=0).sum(axis=0)
    forcing = a.mul(w["forcing"], axis=0).sum(axis=0)
    b_den = a.mul(w["b_den"], axis=0).sum(axis=0)
    o = od.reindex(mem.index)
    return pd.DataFrame({
        "A_proportion": mem / total,
        "A_amount": mem / o,
        "B_proportion": forcing / b_den,
        "B_amount": forcing / o,
        "membrane_signal": mem, "total_signal": total, "od600": o,
    })


READOUTS = ["A_proportion", "A_amount", "B_proportion", "B_amount"]
# The amounts are intensities: multiplicative, so tested on log2 and reported as a
# fold change. The proportions are bounded fractions and are tested as they are.
LOG_SCALE = {"A_amount", "B_amount"}


# ------------------------------------------------------------------------ statistics
def hedges_g(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if sp == 0:
        return np.nan
    j = 1 - 3 / (4 * (na + nb) - 9)
    return j * (a.mean() - b.mean()) / sp


def welch(a: np.ndarray, b: np.ndarray) -> dict:
    """Welch's t with the difference and its 95% interval. Effect leads, p follows."""
    from scipy import stats

    na, nb = len(a), len(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    diff = a.mean() - b.mean()
    if se == 0 or not np.isfinite(se):
        return {"diff": diff, "ci_lo": np.nan, "ci_hi": np.nan, "t": np.nan,
                "df": np.nan, "p": np.nan, "g": np.nan}
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    t = diff / se
    crit = stats.t.ppf(0.975, df)
    return {"diff": diff, "ci_lo": diff - crit * se, "ci_hi": diff + crit * se,
            "t": t, "df": df, "p": 2 * stats.t.sf(abs(t), df), "g": hedges_g(a, b)}


def holm(p: list[float]) -> list[float]:
    order = sorted(range(len(p)), key=lambda i: (np.inf if np.isnan(p[i]) else p[i]))
    out = [np.nan] * len(p)
    prev, m = 0.0, sum(np.isfinite(p))
    for rank, i in enumerate(order):
        if not np.isfinite(p[i]):
            continue
        prev = min(1.0, max(prev, (m - rank) * p[i]))
        out[i] = prev
    return out


def cols_for(strain: str, treat: str, frac: str, available) -> list[str]:
    return [c for c in available
            if c.startswith(f"{strain}_{treat}_{frac}_")]


def contrasts(ps: pd.DataFrame, clone: str, label_set: str, weighting: str) -> pd.DataFrame:
    """The 4 canonical conditions x 4 readouts for one clone."""
    rows = []
    for frac, kind in CONDITIONS:
        (sa, ta), (sb, tb) = groups_for(clone, frac, kind)
        ia = cols_for(sa, ta, frac, ps.index)
        ib = cols_for(sb, tb, frac, ps.index)
        for r in READOUTS:
            a = ps.loc[ia, r].to_numpy(float)
            b = ps.loc[ib, r].to_numpy(float)
            use_log = r in LOG_SCALE
            av, bv = (np.log2(a), np.log2(b)) if use_log else (a, b)
            st = welch(av, bv)
            rows.append({
                "clone": clone, "label_set": label_set, "weighting": weighting,
                "fraction": FRACTION_NAME[frac], "contrast": kind,
                "group_a": f"{sa} {ta}", "group_b": f"{sb} {tb}",
                "readout": r, "scale": "log2" if use_log else "linear",
                "n_a": len(a), "n_b": len(b),
                "mean_a": a.mean(), "mean_b": b.mean(),
                "sd_a": a.std(ddof=1), "sd_b": b.std(ddof=1),
                "fold_change": (2 ** st["diff"]) if use_log else np.nan,
                **{k: st[k] for k in ("diff", "ci_lo", "ci_hi", "t", "df", "p", "g")},
            })
    out = pd.DataFrame(rows)
    # Holm within each readout family: the four conditions are the family, because
    # they are four asks of one question, and the four readouts are different
    # questions that should not dilute each other.
    out["p_holm"] = np.nan
    for r, g in out.groupby("readout"):
        out.loc[g.index, "p_holm"] = holm(g.p.tolist())
    return out


def interactions(ps: pd.DataFrame, clone: str, label_set: str,
                 weighting: str) -> pd.DataFrame:
    """(clone tol - clone ctrl) - (pCC1 tol - pCC1 ctrl), as a 2x2 interaction term."""
    import statsmodels.formula.api as smf

    rows = []
    for frac in ("P", "S"):
        ctrl_strain = PCC1[frac]
        for r in READOUTS:
            recs = []
            for strain in (clone, ctrl_strain):
                for treat in ("ctrl", "tol"):
                    for c in cols_for(strain, treat, frac, ps.index):
                        v = ps.at[c, r]
                        recs.append({"y": np.log2(v) if r in LOG_SCALE else v,
                                     "strain": "clone" if strain == clone else "pcc1",
                                     "treat": treat})
            df = pd.DataFrame(recs).dropna()
            if df.strain.nunique() < 2 or df.treat.nunique() < 2:
                continue
            m = smf.ols("y ~ C(strain, Treatment('pcc1')) * C(treat, Treatment('ctrl'))",
                        data=df).fit()
            term = [t for t in m.params.index if ":" in t]
            if not term:
                continue
            t0 = term[0]
            ci = m.conf_int().loc[t0]
            rows.append({
                "clone": clone, "label_set": label_set, "weighting": weighting,
                "fraction": FRACTION_NAME[frac], "readout": r,
                "scale": "log2" if r in LOG_SCALE else "linear",
                "interaction": m.params[t0], "ci_lo": ci[0], "ci_hi": ci[1],
                "p": m.pvalues[t0], "n": len(df),
            })
    out = pd.DataFrame(rows)
    if len(out):
        out["p_holm"] = np.nan
        for r, g in out.groupby("readout"):
            out.loc[g.index, "p_holm"] = holm(g.p.tolist())
    return out


# ---------------------------------------------------------------------------- driver
def run() -> pd.DataFrame:
    calls = pd.read_csv(common.IDENT_DIR / "membrane_calls.csv").set_index("feature_id")
    feats, abund, bio = lipidio.load_bio(source="metaboscape", polarity="merged")
    abund = abund.loc[[i for i in calls.index if i in abund.index]]
    calls = calls.loc[abund.index]
    od = lipidio.od_map("per_rep")

    print("=" * 78)
    print("MEMBRANE LIPID PER CELL -- Clone2 vs the pCC1 empty vector")
    print("=" * 78)
    print(f"   {len(calls)} negative-mode features, {abund.shape[1]} biological samples")
    print("   Denominator for A-proportion is the total signal over exactly these")
    print("   features -- the classified universe, not the whole 2180-feature table.")
    print("\n== OD600 by group (this is why the amount readouts need normalising)")
    o = pd.DataFrame({"od": od})
    o["strain"] = [i.rsplit("_", 3)[0] for i in o.index]
    o["treat"] = [i.split("_")[-3] for i in o.index]
    print(o.groupby(["strain", "treat"]).od.mean().round(3).to_string())

    per_sample_tables, all_tests, all_inter = {}, [], []
    settings = [("tier1", "hard"), ("full", "hard"), ("full", "prob")]
    for label_set, weighting in settings:
        ps = per_sample(calls, abund, od, label_set, weighting)
        per_sample_tables[(label_set, weighting)] = ps
        for clone in ("Clone2", "Clone1"):
            all_tests.append(contrasts(ps, clone, label_set, weighting))
            all_inter.append(interactions(ps, clone, label_set, weighting))

    tests = pd.concat(all_tests, ignore_index=True)
    inter = pd.concat([t for t in all_inter if len(t)], ignore_index=True)

    # ------------------------------------------------------------------- reporting
    print("\n== how many features each label set puts in the numerator")
    for (ls, wt), ps in per_sample_tables.items():
        w = weights(calls, ls, wt)
        print(f"   {ls:6s} / {wt:4s}   membrane weight sum {w['mem'].sum():7.1f}"
              f"   curvature-forcing {w['forcing'].sum():7.1f}"
              f"   B denominator {w['b_den'].sum():7.1f}")

    for ls, wt in settings:
        print("\n" + "=" * 78)
        print(f"CLONE2, the four canonical conditions -- '{ls}' / '{wt}'")
        print("=" * 78)
        t = tests[(tests.clone == "Clone2") & (tests.label_set == ls)
                  & (tests.weighting == wt)]
        for r in READOUTS:
            sub = t[t.readout == r]
            unit = "log2 fold" if r in LOG_SCALE else "difference"
            print(f"\n  {r}   ({unit}, a minus b)")
            for _, x in sub.iterrows():
                star = "  *" if x.p_holm < 0.05 else ("  ." if x.p < 0.05 else "")
                extra = f"  FC {x.fold_change:5.2f}x" if r in LOG_SCALE else ""
                print(f"    {x.fraction:12s} {x.contrast:22s}  "
                      f"{x.group_a:13s} {x.mean_a:11.4g} +/- {x.sd_a:9.3g}   "
                      f"{x.group_b:13s} {x.mean_b:11.4g} +/- {x.sd_b:9.3g}   "
                      f"d {x['diff']:+7.3f} [{x.ci_lo:+7.3f},{x.ci_hi:+7.3f}]"
                      f"{extra}  g {x.g:+6.2f}  p {x.p:.4f}  Holm {x.p_holm:.4f}{star}")

    # ---------------------------------------- the control strain's own toluene arm
    # The grid gives the clone's toluene response but not the control's, and the
    # control's is what explains the whole result. It is reported here rather than
    # added to the grid, because the grid is the scope's and is not mine to extend.
    print("\n" + "=" * 78)
    print("REFERENCE -- the pCC1 empty vector's OWN toluene response")
    print("=" * 78)
    ref = []
    for ls, wt in settings:
        ps_ = per_sample_tables[(ls, wt)]
        for frac in ("P", "S"):
            for r in READOUTS:
                s = PCC1[frac]
                a = ps_.loc[cols_for(s, "tol", frac, ps_.index), r].to_numpy(float)
                b = ps_.loc[cols_for(s, "ctrl", frac, ps_.index), r].to_numpy(float)
                if r in LOG_SCALE:
                    a, b = np.log2(a), np.log2(b)
                st = welch(a, b)
                ref.append({"strain": s, "label_set": ls, "weighting": wt,
                            "fraction": FRACTION_NAME[frac], "readout": r,
                            "scale": "log2" if r in LOG_SCALE else "linear", **st})
    ref = pd.DataFrame(ref)
    for ls, wt in settings[:2]:
        s = ref[(ref.label_set == ls) & (ref.weighting == wt)]
        print(f"\n  label set '{ls}'")
        for _, x in s.iterrows():
            print(f"    {x.strain:6s} {x.fraction:12s} {x.readout:14s} "
                  f"{x['diff']:+7.3f} [{x.ci_lo:+7.3f},{x.ci_hi:+7.3f}]  p {x.p:.4f}")
    print("\n   Set this against the clone's own '+Tol. vs -Tol' rows above. If the")
    print("   clone holds still and the control moves, the strain difference under")
    print("   toluene is the CONTROL's excursion, not an engineered response.")

    print("\n" + "=" * 78)
    print("INTERACTION -- (Clone2 tol - Clone2 ctrl) - (pCC1 tol - pCC1 ctrl)")
    print("=" * 78)
    print("   This is the contrast that licenses a causal reading of the toluene arm.")
    for ls, wt in settings:
        s = inter[(inter.clone == "Clone2") & (inter.label_set == ls)
                  & (inter.weighting == wt)]
        print(f"\n  label set '{ls}', weighting '{wt}'")
        for _, x in s.iterrows():
            star = "  *" if x.p_holm < 0.05 else ("  ." if x.p < 0.05 else "")
            print(f"    {x.fraction:12s} {x.readout:14s} "
                  f"{x.interaction:+8.4f} [{x.ci_lo:+8.4f},{x.ci_hi:+8.4f}]"
                  f"  p {x.p:.4f}  Holm {x.p_holm:.4f}{star}")

    print("\n" + "=" * 78)
    print("CLONE1 -- the same grid, as an independent second clone")
    print("=" * 78)
    c1 = tests[(tests.clone == "Clone1") & (tests.label_set == "full")
               & (tests.weighting == "hard")]
    for r in READOUTS:
        sub = c1[c1.readout == r]
        print(f"\n  {r}")
        for _, x in sub.iterrows():
            star = "  *" if x.p_holm < 0.05 else ("  ." if x.p < 0.05 else "")
            print(f"    {x.fraction:12s} {x.contrast:22s}  d {x['diff']:+7.3f} "
                  f"[{x.ci_lo:+7.3f},{x.ci_hi:+7.3f}]  g {x.g:+6.2f}  "
                  f"p {x.p:.4f}  Holm {x.p_holm:.4f}{star}")

    # ---------------------------------------------------------------- concordance
    print("\n" + "=" * 78)
    print("CONCORDANCE -- does the answer depend on the classifier?")
    print("=" * 78)
    key = ["clone", "fraction", "contrast", "readout"]
    a = tests[(tests.label_set == "tier1")].set_index(key)
    b = tests[(tests.label_set == "full") & (tests.weighting == "hard")].set_index(key)
    j = a[["diff", "p"]].join(b[["diff", "p"]], lsuffix="_t1", rsuffix="_full")
    j["same_sign"] = np.sign(j["diff_t1"]) == np.sign(j["diff_full"])
    j["both_p05"] = (j.p_t1 < 0.05) == (j.p_full < 0.05)
    print(f"   direction agrees on {int(j.same_sign.sum())}/{len(j)} contrasts")
    print(f"   p<0.05 status agrees on {int(j.both_p05.sum())}/{len(j)} contrasts")
    bad = j[~j.same_sign | ~j.both_p05]
    if len(bad):
        print("\n   where they disagree -- this is a finding, not a rounding error:")
        print(bad.round(4).to_string())

    # ------------------------------------------------------- what the OD is doing
    # Every amount readout is a ratio of two things that both moved. Toluene puts
    # pCC1 at OD 0.10 against Clone2's 0.41, so a four-fold per-cell difference can
    # be produced by the denominator alone. Splitting the log2 effect into its two
    # halves is the only way a reader can tell which one is carrying it.
    print("\n" + "=" * 78)
    print("WHAT IS CARRYING THE AMOUNT EFFECT -- lipid, or biomass?")
    print("=" * 78)
    ps = per_sample_tables[("full", "hard")]
    rows = []
    for frac, kind in CONDITIONS:
        (sa, ta), (sb, tb) = groups_for("Clone2", frac, kind)
        ia = cols_for(sa, ta, frac, ps.index)
        ib = cols_for(sb, tb, frac, ps.index)
        sig = np.log2(ps.loc[ia, "membrane_signal"].mean()
                      / ps.loc[ib, "membrane_signal"].mean())
        odr = np.log2(ps.loc[ia, "od600"].mean() / ps.loc[ib, "od600"].mean())
        rows.append({"fraction": FRACTION_NAME[frac], "contrast": kind,
                     "log2_raw_signal": sig, "log2_od": odr,
                     "log2_per_cell": sig - odr})
        print(f"   {FRACTION_NAME[frac]:12s} {kind:22s}  raw membrane signal "
              f"{sig:+6.2f}   minus OD {odr:+6.2f}   = per cell {sig - odr:+6.2f}"
              f"   ({2 ** (sig - odr):.2f}x)")
    dec = pd.DataFrame(rows)
    print("   Where the OD column is the large one, the per-cell result is a biomass")
    print("   result. It is a correct one -- that is what per cell means -- but the")
    print("   sentence to write names the growth difference, not a lipid change.")

    print("\n== does total signal track OD?  (it must, for a per-cell ratio to mean"
          " what it says)")
    frac_of = pd.Series([i.split("_")[-2] for i in ps.index], index=ps.index)
    for f in ("P", "S"):
        s = ps[frac_of == f]
        r = np.corrcoef(np.log2(s.total_signal.astype(float)),
                        np.log2(s.od600.astype(float)))[0, 1]
        print(f"   {FRACTION_NAME[f]:12s} Pearson r(log2 total signal, log2 OD600) "
              f"= {r:+.3f}   (n={len(s)})")
    print("   Pellet is positive, which is what an extraction from a fixed culture")
    print("   volume should give -- more cells, more lipid -- so dividing by OD there")
    print("   removes a real biomass term. Supernatant runs the OTHER way: the cultures")
    print("   with the least biomass shed the MOST lipid into the medium, which is what")
    print("   lysis looks like. Dividing supernatant signal by OD therefore multiplies")
    print("   two effects pointing the same direction rather than cancelling one, and")
    print("   the supernatant amount readouts are inflated by construction. That is the")
    print("   single most misreadable number in this table.")

    PUBLISH.mkdir(parents=True, exist_ok=True)
    dec.to_csv(PUBLISH / "membrane_abundance_od_decomposition.csv", index=False)
    ref.to_csv(PUBLISH / "membrane_abundance_pcc1_toluene.csv", index=False)
    tests.to_csv(PUBLISH / "membrane_abundance_tests.csv", index=False)
    inter.to_csv(PUBLISH / "membrane_abundance_interactions.csv", index=False)
    ps_out = pd.concat(
        [t.assign(label_set=k[0], weighting=k[1]) for k, t in per_sample_tables.items()]
    ).rename_axis("sample").reset_index()
    ps_out.to_csv(PUBLISH / "membrane_abundance_per_sample.csv", index=False)
    print(f"\nwrote {PUBLISH}/membrane_abundance_tests.csv")
    return tests


if __name__ == "__main__":
    run()

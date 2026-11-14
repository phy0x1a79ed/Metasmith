"""Are the Clone2 toluene-response lipids over-represented in any lipid class?

The question is the seven supernatant features that go UP in Clone2 under toluene.
Three axes carry formal tests -- phospholipid, curvature, and headgroup class --
against a null drawn from the whole feature table, classified by the identical rule.

Three things make this harder than a contingency table, and each is handled rather
than assumed away:

  INDETERMINATES ARE NOT DROPPED. A feature the classifier could not call is a
  third state, not a missing value. Every enrichment is therefore reported three
  times: as observed, then recomputed with every indeterminate forced positive, then
  with every indeterminate forced negative. The truth lies inside that interval
  whatever the indeterminates really are. An interval spanning both directions is
  the finding, not a failure to produce one.

  ABUNDANCE IS THE CONFOUNDER. Data-dependent acquisition fragments abundant
  precursors preferentially, and phospholipids are abundant, so MS/MS availability
  and phospholipid status both track intensity. The seven hits are specifically the
  low-abundance tail. The primary test is therefore run against an abundance-matched
  background as well as the whole table, and both are shown.

  n=7 CANNOT DETECT A SMALL EFFECT. The minimum detectable effect is computed and
  printed BEFORE each test, so a null result is read as "underpowered to see less
  than k of 7" rather than as evidence of absence.

The cardiolipin arm rides along here. CL is not detectable in this dataset (see
cl_bound.py), but ClsA makes CL from two PG, so PG consumption is the observable
shadow of a CL-mediated remodelling. It is reported as a directional readout, not a
claim about CL.

Run:  mamba run -n p312 python -m identify.headgroup_enrichment    (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lipidio  # noqa: E402
from identify import common  # noqa: E402
from lipidio import load_bio, od_normalize, log2  # noqa: E402
from od_strain_volcano import cols_for, contrast_median  # noqa: E402

# The seven positive-fold-change supernatant features from the Clone2 toluene
# contrast -- the hit set this whole lane exists to characterise.
HITS = ["F2799", "F2475", "F2873", "F0161", "F1683", "F0415", "F1515"]

N_ABUNDANCE_STRATA = 5
PUBLISH = common.PUBLISH_DIR.parent / "07_lipid_class_enrichment"


# --------------------------------------------------------------- fold changes
def fold_changes() -> pd.DataFrame:
    """Clone2 supernatant, +toluene vs -toluene, OD-normalised -- the contrast the
    seven hits were called on, recomputed here so the classifier table and the
    effect sizes come from one place."""
    feats, raw, bio = load_bio(source="metaboscape", polarity="merged")
    ab = od_normalize(raw, "group_geomean")
    b, lg = bio.loc[ab.columns], log2(ab)
    out = {}
    for label, (s, frac) in {"sup": ("Clone2", "S"), "pel": ("Clone2", "P")}.items():
        a = cols_for(b, s, frac, "tol")
        c = cols_for(b, s, frac, "ctrl")
        d = contrast_median(feats, ab, lg, a, c, fc_col="fc",
                            fdr="storey").set_index("feature_id")
        # contrast_median's `fc` is already a log2 difference -- median(log2 a)
        # minus median(log2 b) -- not a ratio. Taking a log of it would be wrong.
        out[f"log2fc_{label}"] = d.fc
        out[f"q_{label}"] = d.qvalue
    return pd.DataFrame(out)


# ------------------------------------------------------------------ statistics
def mde(n_hits: int, bg_pos: int, bg_n: int, alpha: float = 0.05) -> int | None:
    """Smallest number of the n hits that would reach significance, given the
    background rate. Printed before a test so a null can be read correctly."""
    for k in range(n_hits + 1):
        _, p = fisher_exact([[k, n_hits - k], [bg_pos, bg_n - bg_pos]],
                            alternative="greater")
        if p < alpha:
            return k
    return None


def fisher_row(name: str, hit_pos: int, hit_n: int,
               bg_pos: int, bg_n: int) -> dict:
    odds, p = fisher_exact([[hit_pos, hit_n - hit_pos],
                            [bg_pos, bg_n - bg_pos]], alternative="two-sided")
    return {"test": name, "hit": f"{hit_pos}/{hit_n}", "bg": f"{bg_pos}/{bg_n}",
            "hit_pct": 100 * hit_pos / hit_n if hit_n else np.nan,
            "bg_pct": 100 * bg_pos / bg_n if bg_n else np.nan,
            "odds_ratio": odds, "p_raw": p}


def bounded(name: str, d: pd.DataFrame, hits: set[str], axis: str,
            positive: set[str], indet: set[str]) -> list[dict]:
    """The same enrichment three ways: as called, and with the indeterminates
    forced each direction. The observed row is the estimate; the two forced rows
    are the bound it must lie inside."""
    rows = []
    for mode in ("observed", "indet->positive", "indet->negative"):
        def is_pos(v):
            if v in positive:
                return True
            if v in indet:
                return mode == "indet->positive"
            return False

        def in_scope(v):
            return mode != "observed" or v not in indet

        h = d[d.feature_id.isin(hits)]
        b = d[~d.feature_id.isin(hits)]
        h = h[h[axis].map(in_scope)]
        b = b[b[axis].map(in_scope)]
        if not len(h) or not len(b):
            continue
        rows.append({**fisher_row(name, int(h[axis].map(is_pos).sum()), len(h),
                                  int(b[axis].map(is_pos).sum()), len(b)),
                     "mode": mode})
    return rows


def holm(rows: list[dict]) -> list[dict]:
    """Holm-Bonferroni across the family of observed tests only -- correcting the
    forced-bound rows too would count each hypothesis three times."""
    fam = [r for r in rows if r.get("mode") == "observed"]
    order = sorted(range(len(fam)), key=lambda i: fam[i]["p_raw"])
    m = len(fam)
    prev = 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, max(prev, (m - rank) * fam[i]["p_raw"]))
        fam[i]["p_holm"] = adj
        prev = adj
    return rows


# ---------------------------------------------------------------------- driver
def run() -> pd.DataFrame:
    d = pd.read_csv(common.IDENT_DIR / "full_headgroup_validated.csv")
    fc = fold_changes()
    d = d.merge(fc, left_on="feature_id", right_index=True, how="left")
    hits = set(HITS)

    missing = hits - set(d.feature_id)
    if missing:
        raise KeyError(f"hit features absent from the classifier table: {missing}")

    print("=" * 72)
    print("THE SEVEN HITS, as classified")
    print("=" * 72)
    cols = ["feature_id", "polarity", "channel", "phospholipid", "headgroup_group",
            "n_acyl", "chains", "curvature_prior", "contains_N", "log2fc_sup",
            "lipid_class"]
    print(d[d.feature_id.isin(hits)][cols].to_string(index=False))

    # ------------------------------------------------------- abundance matching
    d["ab_stratum"] = pd.qcut(d.mean_abundance.rank(method="first"),
                              N_ABUNDANCE_STRATA, labels=False)
    hs = d[d.feature_id.isin(hits)].ab_stratum.value_counts().sort_index()
    print("\n== abundance strata of the hits (0 = lowest)")
    print(f"   {dict(hs)}   <- the confounder: DDA fragments abundant precursors")
    matched = d[d.ab_stratum.isin(hs.index) | d.feature_id.isin(hits)]
    print(f"   abundance-matched background: {len(matched) - len(hits)} features "
          f"(vs {len(d) - len(hits)} unmatched)")

    # Curvature is tested on the PRIOR column. The strict column leaves PE/PC
    # indeterminate, which empties the cone class entirely -- it is reported by
    # headgroup_validate but carries no test, because there is nothing in it.
    IND = {"indeterminate", "ambiguous"}
    axes = [
        ("phospholipid", {"yes"}, IND, "phospholipid"),
        ("curvature_prior", {"cone"}, IND, "cone-shaped"),
        ("curvature_prior", {"inverted-cone"}, IND, "inverted-cone (lyso)"),
        ("curvature_prior", {"cylinder"}, IND, "cylinder"),
        ("headgroup_group", {"PE/PC"}, IND, "headgroup PE/PC"),
        ("headgroup_group", {"PG"}, IND, "headgroup PG"),
        ("headgroup_group", {"PS"}, IND, "headgroup PS"),
        ("contains_N", {"yes"}, IND, "contains N (descriptive)"),
    ]

    all_rows: list[dict] = []
    for bg_name, table in (("whole table", d), ("abundance-matched", matched)):
        print("\n" + "=" * 72)
        print(f"CONFIRMATORY: seven hits vs {bg_name}")
        print("=" * 72)
        for axis, pos, ind, label in axes:
            b = table[~table.feature_id.isin(hits)]
            det = b[~b[axis].isin(ind)]
            k = mde(len(hits), int(det[axis].isin(pos).sum()), len(det))
            need = f"needs >={k}/7" if k is not None else "UNDETECTABLE at any k"
            print(f"\n  {label}  (background {100 * det[axis].isin(pos).mean():.1f}% "
                  f"of {len(det)} determinate)   MDE: {need}")
            for r in bounded(f"{label} [{bg_name}]", table, hits, axis, pos, ind):
                r["background"] = bg_name
                all_rows.append(r)
                print(f"     {r['mode']:<16} hits {r['hit']:>6} = {r['hit_pct']:5.1f}%  "
                      f"bg {r['bg']:>10} = {r['bg_pct']:5.1f}%  "
                      f"OR {r['odds_ratio']:6.2f}  p {r['p_raw']:.4f}")

    # ------------------------------------------------ primary: continuous test
    print("\n" + "=" * 72)
    print("PRIMARY: does each label shift the whole-table fold-change distribution?")
    print("=" * 72)
    print("  (all determinate features, not just the seven -- this is where the power is)")
    cont = []
    for axis, pos, ind, label in axes:
        s = d[d[axis].notna() & ~d[axis].isin(ind) & d.log2fc_sup.notna()]
        a = s[s[axis].isin(pos)].log2fc_sup
        b = s[~s[axis].isin(pos)].log2fc_sup
        if len(a) < 3 or len(b) < 3:
            print(f"  {label:<18} n={len(a)} vs {len(b)}  -- too few to test")
            continue
        u, p = mannwhitneyu(a, b, alternative="two-sided")
        cont.append({"test": f"{label} (continuous)", "n_pos": len(a), "n_neg": len(b),
                     "median_pos": a.median(), "median_neg": b.median(),
                     "p_raw": p, "mode": "observed", "background": "continuous"})
        print(f"  {label:<18} n={len(a):5d} vs {len(b):5d}   "
              f"median log2FC {a.median():+.3f} vs {b.median():+.3f}   p {p:.2e}")
    all_rows += cont

    all_rows = holm(all_rows)
    out = pd.DataFrame(all_rows)

    print("\n" + "=" * 72)
    print("FAMILY-CORRECTED (Holm over the observed tests)")
    print("=" * 72)
    obs = out[out["mode"] == "observed"].sort_values("p_raw")
    print(obs[["test", "background", "p_raw", "p_holm"]].to_string(index=False))

    # -------------------------------------------------------- cardiolipin arm
    print("\n" + "=" * 72)
    print("CARDIOLIPIN ARM: PG is CL's precursor, and PG we can see")
    print("=" * 72)
    for frac, col in (("supernatant", "log2fc_sup"), ("pellet", "log2fc_pel")):
        s = d[d[col].notna()]
        pg = s[s.headgroup_group == "PG"][col]
        other = s[s.headgroup_group.isin(["PE/PC", "PS"])][col]
        if len(pg) >= 3 and len(other) >= 3:
            u, p = mannwhitneyu(pg, other, alternative="two-sided")
            print(f"  {frac:<12} PG n={len(pg):3d} median {pg.median():+.3f}   "
                  f"other phospholipid n={len(other):3d} median {other.median():+.3f}   "
                  f"p {p:.4f}")
        else:
            print(f"  {frac:<12} PG n={len(pg)} -- too few to test")
    print("\n  A CL-mediated remodelling would show as PG depletion. This is a")
    print("  directional readout on the precursor, not a measurement of CL.")

    PUBLISH.mkdir(parents=True, exist_ok=True)
    out.to_csv(PUBLISH / "class_enrichment_tests.csv", index=False)
    d.to_csv(PUBLISH / "feature_class_calls.csv", index=False)
    print(f"\nwrote {PUBLISH}")
    return out


if __name__ == "__main__":
    run()

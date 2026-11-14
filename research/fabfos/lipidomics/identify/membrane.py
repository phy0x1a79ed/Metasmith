"""Put a membrane-lipid call on every negative-mode feature, not a fifth of them.

WHY THIS EXISTS. `headgroup.py` reads the backbone off the MS/MS by mass balance.
It is the strongest evidence available and it reaches 178 of 800 negative-mode
features, because it needs an acyl carboxylate anion and only 346 features have
one. Everything downstream -- enrichment, composition, the membrane-per-cell
question -- was therefore being asked of a fifth of the table, selected by
fragmentability, which tracks abundance.

WHAT WAS TRIED AND FAILED, so it is not tried again. Phosphorus has no cheap
handle in this dataset:
  - PO3- (78.96) and H2PO4- (96.97) sit below this method's MS2 acquisition floor
    of m/z 99.92 and were never written to disk.
  - The complementary neutral losses ARE in range and are absent: 1 of 144
    confirmed phospholipids shows an HPO3/H3PO4 loss.
  - Free CHNOPS enumeration at 5 ppm leaves 80% of negative features admitting
    both a P-containing and a P-free formula, and 31-P is mononuclidic so there is
    no isotope-pattern handle either.
  - Lowering the acyl-anion intensity floor from 10% to 0.5% moves the number of
    features with a chain from 341 to 346.

So coverage cannot come from more chemistry. It comes from channels that exist for
every feature -- m/z, retention time, CCS, mass defect, adduct -- and those channels
carry a model, not a measurement. The whole design of this module is about keeping
that distinction visible instead of laundering it.

THE TIERS. Each feature lands in exactly one, and the tier travels with the call:
  1  mass balance      -- MS/MS fragment evidence. Never overwritten.
  2  formula / facility -- an assigned molecular formula decides phosphorus outright;
                          the facility's super-class decides membrane status. Joins,
                          not models. Checked against tier 1 where both exist.
  3  model             -- calibrated probability from the full-coverage channels.
  4  abstain           -- too close to the decision boundary to call. Kept as a
                          state rather than forced, because a coin flip entering an
                          enrichment test is indistinguishable from a confident call.

THE BINDING CONSTRAINT is the negative class. This is a lipid extract, so nearly
everything confirmed is a phospholipid; the confirmed NON-phospholipids number in the
low tens. Every specificity figure printed here is therefore a bound with a wide
interval, and is printed next to its n so it cannot be read as more than that.

WHAT IS DELIBERATELY NOT A FEATURE. MS2 availability (has_msms, n_peaks, msms_score)
predicts the tier-1 label almost perfectly -- because it is what PRODUCES the tier-1
label. Feeding it to the model would recover the labelling process, not the chemistry.
Abundance is the same story one step removed, so the canonical model excludes it and
a sensitivity run reports what including it does.

CLASSIFICATION B rides on the same machinery. Curvature-forcing (PE) versus
bilayer-forming (PG/PS) is a binary within the membrane set, and its labels are
nearly balanced, so it is better posed than A -- with one hard limit: PE and PC are
mass-degenerate to 0.00 mDa, and that degeneracy sits exactly on the split. The strict
column leaves PE/PC uncalled; the prior column reads it as PE on the grounds that
E. coli has no phosphatidylcholine synthase. Both are emitted. Neither is chosen here.

Run:  mamba run -n p312 python -m identify.membrane        (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common, headgroup, refs  # noqa: E402

POLARITY = "neg"          # positive mode has no acyl anions and no usable label set
COVERAGE_TARGET = 0.95
ABSTAIN_MAX = 0.15        # widest half-band around p=0.5 we will ever abstain over
RANDOM_STATE = 0
N_REPEATS = 20
N_SPLITS = 5

PUBLISH = common.PUBLISH_DIR.parent / "07_lipid_class_enrichment"

# --------------------------------------------------------------- label vocabulary
# These five used to be hand-written dictionaries here. They are now views over the
# cited tables in `identify/refs/`, because the mapping from lipid class to "is it a
# membrane lipid" and "does it force curvature" is literature rather than a decision
# this lane gets to make, and it should be readable as literature -- with the
# citation attached to the row, not buried in a comment above the dict.
#
# The tables reproduce the old dictionaries exactly on every key they shared, and
# add three the old ones had simply missed: O-DG, O-PA and Ubiquinones. Ubiquinone
# is the one that matters -- it is genuinely present and abundant in this dataset,
# and leaving it out of the facility tier pushed every quinone feature down to the
# model instead of settling it from the facility's own class.
SUPER_CLASS_MEMBRANE = refs.membrane_by_super_class()
FINAL_CLASS_GROUP = refs.group_by_facility_class()
FINAL_CLASS_MEMBRANE = refs.membrane_by_facility_class()
FINAL_CLASS_LYSO = refs.lyso_facility_classes()

# Classification B, from the headgroup group -- a deliberately weaker claim than the
# per-subclass table, because mass balance cannot separate PE from PC or PA from PI.
# See refs/headgroup_group_curvature.tsv for why each cell reads as it does.
GROUP_CURVATURE_STRICT = refs.curvature_by_group(prior=False)
GROUP_CURVATURE_PRIOR = refs.curvature_by_group(prior=True)


# ------------------------------------------------------------------ label assembly
def has_phosphorus(formula: object) -> bool | None:
    """Does an assigned molecular formula contain P? None if no formula."""
    if not isinstance(formula, str) or not formula.strip():
        return None
    return bool(re.search(r"P(?![a-z])", formula))


def assemble(polarity: str = POLARITY) -> pd.DataFrame:
    """One row per feature of the chosen polarity, carrying every label source."""
    man = pd.read_csv(common.IDENT_DIR / "full_manifest.csv")
    hg = pd.read_csv(common.IDENT_DIR / "full_headgroup_validated.csv")
    tiers = pd.read_csv(common.METABOSCAPE_DIR / "annotation_tiers.csv")

    keep_hg = ["feature_id", "phospholipid", "headgroup_group", "channel", "n_acyl",
               "best_residue", "chains", "groups_closing", "residue_err_mda"]
    d = man.merge(hg[keep_hg], on="feature_id", how="left")
    d = d.merge(tiers[["feature_id", "final_class", "super_class", "tier"]],
                on="feature_id", how="left")
    d = d[d.polarity == polarity].reset_index(drop=True)

    # --- tier 1: MS/MS mass balance
    d["t1_membrane"] = d.phospholipid.where(d.channel == "mass-balance")
    d["t1_membrane"] = d.t1_membrane.where(d.t1_membrane.isin(["yes", "no"]))
    d["t1_group"] = d.headgroup_group.where(
        (d.channel == "mass-balance")
        & d.headgroup_group.isin(GROUP_CURVATURE_STRICT))
    d["t1_n_acyl"] = d.n_acyl.where(d.channel == "mass-balance")

    # --- tier 2a: assigned molecular formula
    p = d.formula.map(has_phosphorus)
    d["t2_formula_membrane"] = p.map({True: "yes", False: "no"})

    # --- tier 2b: the facility's own class assignment
    d["t2_facility_membrane"] = d.super_class.map(SUPER_CLASS_MEMBRANE)
    fine = d.final_class.map(FINAL_CLASS_MEMBRANE)
    d["t2_facility_membrane"] = d.t2_facility_membrane.fillna(fine)
    d["t2_facility_group"] = d.final_class.map(FINAL_CLASS_GROUP)
    d["t2_facility_lyso"] = d.final_class.isin(FINAL_CLASS_LYSO)
    return d


def label_conflicts(d: pd.DataFrame) -> pd.DataFrame:
    """Where two label sources disagree. A join is only free if it is consistent."""
    rows = []
    pairs = [("t1_membrane", "t2_formula_membrane"),
             ("t1_membrane", "t2_facility_membrane"),
             ("t2_formula_membrane", "t2_facility_membrane")]
    for a, b in pairs:
        s = d[d[a].notna() & d[b].notna()]
        bad = s[s[a] != s[b]]
        rows.append({"source_a": a, "source_b": b, "overlap": len(s),
                     "conflicts": len(bad),
                     "features": ",".join(bad.feature_id.head(10))})
    return pd.DataFrame(rows)


def resolved_labels(d: pd.DataFrame) -> pd.Series:
    """The determinate membrane label per feature: tier 1 first, then tier 2."""
    return (d.t1_membrane
            .fillna(d.t2_formula_membrane)
            .fillna(d.t2_facility_membrane))


# ------------------------------------------------------------- feature engineering
BASE_FEATURES = ["log_mz", "rt", "ccs", "ccs_resid", "rmd",
                 "ad_deprot", "ad_formate", "ad_chloride"]


def _ccs_powerlaw(mz: np.ndarray, ccs: np.ndarray) -> tuple[float, float]:
    ok = np.isfinite(mz) & np.isfinite(ccs) & (mz > 0) & (ccs > 0)
    b, a = np.polyfit(np.log(mz[ok]), np.log(ccs[ok]), 1)
    return float(np.exp(a)), float(b)


def design(d: pd.DataFrame, fit_rows: np.ndarray | None = None) -> pd.DataFrame:
    """Model matrix. The CCS trendline is fitted on `fit_rows` only, so that a
    cross-validation fold never sees its own test features in the trend."""
    mz = d.mz.to_numpy(float)
    ccs = d.ccs.to_numpy(float)
    rows = np.ones(len(d), bool) if fit_rows is None else fit_rows
    a, b = _ccs_powerlaw(mz[rows], ccs[rows])

    nm = d.neutral_mass.to_numpy(float)
    ad = d.adduct.fillna("").to_numpy()
    return pd.DataFrame({
        "log_mz": np.log10(mz),
        "rt": d.rt.to_numpy(float),
        "ccs": ccs,
        # How far the ion sits off the m/z-vs-CCS trendline: the shape term.
        "ccs_resid": ccs - a * mz ** b,
        # Relative mass defect. Phosphorus and oxygen are mass-defect-poor, so a
        # phospholipid sits below a hydrocarbon of the same nominal mass.
        "rmd": (nm % 1) / nm * 1e6,
        "ad_deprot": (ad == "[M-H]-").astype(float),
        "ad_formate": np.isin(ad, ["[M+CHOO]-", "[M+HCOO]-"]).astype(float),
        "ad_chloride": (ad == "[M+Cl]-").astype(float),
        "log_abundance": np.log10(d.mean_bio_abundance.to_numpy(float) + 1.0),
    }, index=d.index)


# ------------------------------------------------------------------- model + CV
def _model():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline([
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(penalty="l2", C=1.0, max_iter=2000,
                                  class_weight="balanced")),
    ])


def cross_validate(d: pd.DataFrame, y: pd.Series, cols: list[str],
                   shuffle_labels: bool = False, model=None) -> dict:
    """Repeated stratified CV. Returns pooled out-of-fold probabilities.

    The design matrix is rebuilt inside every fold from the training rows only, so
    the CCS trendline -- the one feature that is fitted rather than measured -- is
    never informed by the test features.
    """
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    idx = y.index.to_numpy()
    yy = y.to_numpy(int)
    oof = np.full((N_REPEATS, len(idx)), np.nan)
    aucs = []
    for rep in range(N_REPEATS):
        yr = yy
        if shuffle_labels:
            rng = np.random.default_rng(RANDOM_STATE + rep)
            yr = rng.permutation(yy)
        skf = StratifiedKFold(N_SPLITS, shuffle=True, random_state=RANDOM_STATE + rep)
        for tr, te in skf.split(idx, yr):
            fit_rows = np.zeros(len(d), bool)
            fit_rows[d.index.get_indexer(idx[tr])] = True
            X = design(d, fit_rows)
            m = (model or _model())
            from sklearn.base import clone
            m = clone(m)
            m.fit(X.loc[idx[tr], cols], yr[tr])
            oof[rep, te] = m.predict_proba(X.loc[idx[te], cols])[:, 1]
        aucs.append(roc_auc_score(yr, oof[rep]))
    return {"oof": oof.mean(axis=0), "index": idx, "y": yy,
            "auc_mean": float(np.mean(aucs)), "auc_sd": float(np.std(aucs)),
            "aucs": aucs}


def confusion(y: np.ndarray, p: np.ndarray, thr: float = 0.5) -> dict:
    yhat = (p >= thr).astype(int)
    tp = int(((y == 1) & (yhat == 1)).sum())
    fn = int(((y == 1) & (yhat == 0)).sum())
    fp = int(((y == 0) & (yhat == 1)).sum())
    tn = int(((y == 0) & (yhat == 0)).sum())
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "sens": tp / max(tp + fn, 1), "spec": tn / max(tn + fp, 1),
            "n_pos": tp + fn, "n_neg": tn + fp}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson interval. Printed next to every rate estimated on ~20 negatives,
    because the point estimate on its own reads as far firmer than it is."""
    if n == 0:
        return (np.nan, np.nan)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# ------------------------------------------------------- mass-only chain counting
def chain_counts(neutral_mass: float, group: str | None) -> list[int]:
    """Which chain counts can close this mass, given the headgroup group?

    Not a headgroup call -- the headgroup is an input here. With the backbone fixed,
    the only free integers are the total chain carbons and double bonds, and one
    fatty acid tops out near 396 Da, so the feasible chain counts are usually a
    single value. That is what distinguishes a lyso species from a diacyl one when
    no acyl anion was recorded.
    """
    if group is None or not np.isfinite(neutral_mass):
        return []
    residues = [r for r, g in headgroup.RESIDUE_GROUP.items() if g == group]
    out = set()
    for name in residues:
        res = headgroup.RESIDUE[name][0]
        for n in range(1, headgroup.MAX_CHAINS + 1):
            rem = neutral_mass - res + n * headgroup.H2O
            if headgroup._decompose(rem, n, headgroup.RESIDUE_TOL_DA):
                out.add(n)
    return sorted(out)


def lyso_call(row: pd.Series, group_hint: str | None) -> tuple[float | None, str]:
    """Chain count and where it came from. Single-chain is a separate curvature state."""
    if np.isfinite(row.get("t1_n_acyl", np.nan)):
        return float(row.t1_n_acyl), "mass-balance"
    if row.get("t2_facility_lyso", False):
        return 1.0, "facility-class"
    groups = ([group_hint] if group_hint in GROUP_CURVATURE_STRICT
              else ["PE/PC", "PG", "PS"])
    feasible = set()
    for g in groups:
        feasible.update(chain_counts(row.neutral_mass, g))
    if len(feasible) == 1:
        return float(next(iter(feasible))), "mass-only"
    return None, "none"


# ---------------------------------------------------------------------- driver
def _band_for_coverage(p: np.ndarray, n_total: int, n_already: int) -> float:
    """Half-band around 0.5 that leaves overall coverage at the target.

    Abstention is a budget, not a confidence threshold picked by taste: the target
    fixes how many features may go uncalled, and the least-confident ones spend it.
    """
    allowed = max(0, n_total - int(np.ceil(COVERAGE_TARGET * n_total)) - 0)
    allowed = max(0, allowed - (0))
    n_uncalled_elsewhere = n_total - n_already - len(p)
    budget = max(0, allowed - n_uncalled_elsewhere)
    if budget >= len(p):
        return ABSTAIN_MAX
    conf = np.sort(np.abs(p - 0.5))
    if budget == 0:
        return 0.0
    return float(min(ABSTAIN_MAX, conf[budget - 1] + 1e-12))


def run() -> pd.DataFrame:
    from sklearn.metrics import roc_auc_score

    d = assemble()
    n = len(d)
    print("=" * 78)
    print(f"MEMBRANE-LIPID CLASSIFICATION -- {POLARITY} mode, {n} features")
    print("=" * 78)

    print("\n== label sources")
    for col, name in [("t1_membrane", "tier 1  mass balance"),
                      ("t2_formula_membrane", "tier 2  molecular formula"),
                      ("t2_facility_membrane", "tier 2  facility class")]:
        v = d[col].value_counts()
        print(f"   {name:28s} yes {v.get('yes', 0):4d}   no {v.get('no', 0):3d}")

    conf = label_conflicts(d)
    print("\n== do the sources agree where they overlap?")
    print(conf.to_string(index=False))
    if conf.conflicts.sum():
        print("   ^ conflicts are NOT auto-resolved; tier 1 wins and they are listed above")

    lab = resolved_labels(d)
    d["label_membrane"] = lab
    y = (lab[lab.isin(["yes", "no"])] == "yes").astype(int)
    print(f"\n== combined label set: {int(y.sum())} membrane / {int((1 - y).sum())} "
          f"non-membrane  ({len(y)} of {n} features = {100 * len(y) / n:.1f}%)")
    print("   Every specificity figure below rests on that non-membrane count.")

    # ------------------------------------------------------------ model + controls
    print("\n" + "=" * 78)
    print("TIER 3 -- cross-validated on the full-coverage channels")
    print("=" * 78)
    print(f"   features: {', '.join(BASE_FEATURES)}")
    print("   MS2 availability and abundance are excluded: they predict the LABEL,")
    print("   not the chemistry, because they are what produces a tier-1 label.")

    runs = {
        "canonical": (BASE_FEATURES, False),
        "RT withheld": ([c for c in BASE_FEATURES if c != "rt"], False),
        "+ abundance": (BASE_FEATURES + ["log_abundance"], False),
        "shuffled labels (control)": (BASE_FEATURES, True),
    }
    cvs = {}
    print(f"\n   {N_REPEATS}x{N_SPLITS}-fold stratified CV, CCS trendline refit per fold")
    for name, (cols, shuf) in runs.items():
        cv = cross_validate(d, y, cols, shuffle_labels=shuf)
        cvs[name] = cv
        cm = confusion(cv["y"], cv["oof"])
        lo, hi = wilson(cm["tn"], cm["n_neg"])
        print(f"   {name:26s} AUC {cv['auc_mean']:.3f} +/- {cv['auc_sd']:.3f}"
              f"   sens {cm['sens']:.3f} (n={cm['n_pos']})"
              f"   spec {cm['spec']:.3f} [{lo:.2f}-{hi:.2f}] (n={cm['n_neg']})")

    cv = cvs["canonical"]
    cm = confusion(cv["y"], cv["oof"])
    print("\n   canonical confusion matrix, pooled out-of-fold at p=0.5")
    print(f"        {'':14s}{'pred non-mem':>14s}{'pred membrane':>15s}")
    print(f"        {'true non-mem':14s}{cm['tn']:>14d}{cm['fp']:>15d}")
    print(f"        {'true membrane':14s}{cm['fn']:>14d}{cm['tp']:>15d}")
    print(f"   The right-hand column of the top row is the number that matters and")
    print(f"   there are only {cm['n_neg']} rows to estimate it from.")

    # external check: train on fragment evidence, test on the facility's own calls
    ext_tr = d.index[d.t1_membrane.notna()]
    ext_te = d.index[d.t1_membrane.isna() & d.t2_facility_membrane.notna()]
    if len(ext_te) >= 10:
        fit_rows = np.zeros(n, bool)
        fit_rows[d.index.get_indexer(ext_tr)] = True
        X = design(d, fit_rows)
        m = _model().fit(X.loc[ext_tr, BASE_FEATURES],
                         (d.loc[ext_tr, "t1_membrane"] == "yes").astype(int))
        pe = m.predict_proba(X.loc[ext_te, BASE_FEATURES])[:, 1]
        ye = (d.loc[ext_te, "t2_facility_membrane"] == "yes").astype(int).to_numpy()
        cme = confusion(ye, pe)
        auc = roc_auc_score(ye, pe) if len(set(ye)) > 1 else np.nan
        print(f"\n   HELD-OUT: trained on tier-1 fragment evidence only, tested on the")
        print(f"   {len(ext_te)} features the facility labelled and tier 1 did not.")
        print(f"      AUC {auc:.3f}   sens {cme['sens']:.3f} (n={cme['n_pos']})   "
              f"spec {cme['spec']:.3f} (n={cme['n_neg']})")

    # ------------------------------------------------------------- final assignment
    X = design(d)
    model = _model().fit(X.loc[y.index, BASE_FEATURES], y)
    d["model_p"] = model.predict_proba(X[BASE_FEATURES])[:, 1]

    d["membrane"] = "indeterminate"
    d["membrane_tier"] = "4_abstain"
    d["membrane_p"] = np.nan
    for col, tier in [("t2_facility_membrane", "2_facility"),
                      ("t2_formula_membrane", "2_formula"),
                      ("t1_membrane", "1_massbalance")]:
        m = d[col].notna()
        d.loc[m, "membrane"] = d.loc[m, col]
        d.loc[m, "membrane_tier"] = tier
        d.loc[m, "membrane_p"] = (d.loc[m, col] == "yes").astype(float)

    unlab = d.index[d.membrane_tier == "4_abstain"]
    band = _band_for_coverage(d.loc[unlab, "model_p"].to_numpy(), n, n - len(unlab))
    called = unlab[(d.loc[unlab, "model_p"] - 0.5).abs() > band]
    d.loc[called, "membrane"] = np.where(d.loc[called, "model_p"] >= 0.5, "yes", "no")
    d.loc[called, "membrane_tier"] = "3_model"
    d.loc[called, "membrane_p"] = d.loc[called, "model_p"]

    print("\n== coverage by tier")
    for t, k in d.membrane_tier.value_counts().sort_index().items():
        print(f"   {t:16s} {k:5d}  {100 * k / n:5.1f}%")
    cov = 100 * (d.membrane != "indeterminate").mean()
    print(f"   {'CALLED':16s} {int((d.membrane != 'indeterminate').sum()):5d}  {cov:5.1f}%"
          f"   (target {100 * COVERAGE_TARGET:.0f}%; abstention band |p-0.5| <= {band:.4f})")
    print("\n== membrane call")
    print(d.membrane.value_counts().to_string())

    # ---------------------------------------------------------- CLASSIFICATION B
    print("\n" + "=" * 78)
    print("CLASSIFICATION B -- curvature-forcing vs bilayer-forming, within membrane")
    print("=" * 78)
    d["group_called"] = d.t1_group.fillna(d.t2_facility_group)
    d["group_source"] = np.where(d.t1_group.notna(), "1_massbalance",
                                 np.where(d.t2_facility_group.notna(),
                                          "2_facility", "none"))
    n_pc = int((d.final_class.isin(["PC", "LPC", "O-PC", "PC-P"])).sum())
    print(f"   the facility names {n_pc} of these features as a choline lipid; the")
    print("   prior column overrides that (E. coli has no PC synthase, and PE/PC is")
    print("   mass-degenerate to 0.00 mDa so the name cannot have come from mass).")

    yb = d.group_called.map({"PE/PC": 1, "PG": 0, "PS": 0}).dropna().astype(int)
    print(f"\n   labels: {int(yb.sum())} curvature-forcing (PE/PC) / "
          f"{int((1 - yb).sum())} bilayer-forming (PG, PS)")
    cvb = cross_validate(d, yb, BASE_FEATURES)
    cvb_null = cross_validate(d, yb, BASE_FEATURES, shuffle_labels=True)
    cmb = confusion(cvb["y"], cvb["oof"])
    print(f"   CV AUC {cvb['auc_mean']:.3f} +/- {cvb['auc_sd']:.3f}"
          f"   (shuffled control {cvb_null['auc_mean']:.3f})")
    print(f"   sens {cmb['sens']:.3f} (n={cmb['n_pos']})   "
          f"spec {cmb['spec']:.3f} (n={cmb['n_neg']})")

    mb = _model().fit(X.loc[yb.index, BASE_FEATURES], yb)
    d["curv_p"] = mb.predict_proba(X[BASE_FEATURES])[:, 1]

    # chain count -> the third curvature state
    # Chain counting needs a backbone to subtract. Where no group was called, the
    # model's own curvature side supplies one: a curvature-forcing prediction means
    # PE/PC, and a bilayer prediction leaves the residue set open (PG and PS differ),
    # which lyso_call handles by requiring every plausible backbone to agree.
    hint = d.group_called.astype(object).copy()
    hint[hint.isna() & (d.curv_p >= 0.5)] = "PE/PC"
    n_acyl, src = [], []
    for i, row in d.iterrows():
        a, s = lyso_call(row, hint.get(i))
        n_acyl.append(a)
        src.append(s)
    d["n_acyl_called"] = n_acyl
    d["n_acyl_source"] = src
    print("\n== chain count (single-chain is its own curvature state)")
    print(pd.crosstab(d.n_acyl_source, d.n_acyl_called, dropna=False).to_string())

    mem = d.membrane == "yes"
    d["curvature_prior"] = "indeterminate"
    d["curvature_strict"] = "indeterminate"
    d["curvature_tier"] = "4_abstain"

    known = mem & d.group_called.notna()
    d.loc[known, "curvature_prior"] = d.loc[known, "group_called"].map(GROUP_CURVATURE_PRIOR)
    d.loc[known, "curvature_strict"] = d.loc[known, "group_called"].map(GROUP_CURVATURE_STRICT)
    d.loc[known, "curvature_tier"] = d.loc[known, "group_source"]

    rest = d.index[mem & (d.curvature_prior == "indeterminate")]
    bandb = _band_for_coverage(d.loc[rest, "curv_p"].to_numpy(),
                               int(mem.sum()), int(mem.sum()) - len(rest))
    calledb = rest[(d.loc[rest, "curv_p"] - 0.5).abs() > bandb]
    d.loc[calledb, "curvature_prior"] = np.where(
        d.loc[calledb, "curv_p"] >= 0.5, "curvature-forcing", "bilayer-forming")
    d.loc[calledb, "curvature_tier"] = "3_model"

    lyso = mem & (d.n_acyl_called == 1)
    d.loc[lyso, "curvature_prior"] = "positive-curvature"
    d.loc[lyso & (d.curvature_strict != "indeterminate"), "curvature_strict"] = \
        "positive-curvature"

    print("\n== curvature, PE-prior column (the one that can reach coverage)")
    print(d.loc[mem, "curvature_prior"].value_counts().to_string())
    covb = 100 * (d.loc[mem, "curvature_prior"] != "indeterminate").mean()
    print(f"   coverage within the membrane set: {covb:.1f}% of {int(mem.sum())}")
    print("\n== curvature, STRICT column (PE/PC left uncalled)")
    print(d.loc[mem, "curvature_strict"].value_counts().to_string())
    covs = 100 * (d.loc[mem, "curvature_strict"] != "indeterminate").mean()
    print(f"   coverage within the membrane set: {covs:.1f}%")
    print("   The gap between the two columns IS the PE/PC degeneracy. It is not")
    print("   closable by mass, now or ever, so B's coverage is a claim about the")
    print("   prior as much as about the model.")

    # -------------------------------------------------------------- diagnostics
    # A model trained on the fragmentable features and applied to the rest is
    # extrapolating across a covariate shift, and the honest way to show how far it
    # is being trusted is to weight by signal: the tier-1 features carry most of the
    # intensity, so a downstream sum is dominated by measurement even where the
    # feature COUNT is dominated by model.
    print("\n" + "=" * 78)
    print("HOW MUCH IS THE MODEL ACTUALLY CARRYING?")
    print("=" * 78)
    ab = d.mean_bio_abundance.fillna(0.0)
    print("\n== share of negative-mode signal by tier")
    for t, g in ab.groupby(d.membrane_tier):
        print(f"   {t:16s} {len(g):5d} features   {100 * g.sum() / ab.sum():5.1f}% of signal")
    print("\n== share of MEMBRANE signal by tier")
    abm = ab[mem]
    for t, g in abm.groupby(d.loc[mem, "membrane_tier"]):
        print(f"   {t:16s} {len(g):5d} features   {100 * g.sum() / abm.sum():5.1f}% of signal")
    print("\n== share of membrane signal by curvature call and tier")
    piv = pd.crosstab(d.loc[mem, "curvature_tier"], d.loc[mem, "curvature_prior"],
                      values=abm, aggfunc="sum").fillna(0.0)
    print((100 * piv / abm.sum()).round(1).to_string())

    print("\n== covariate shift: labelled vs model-called features")
    for f in ("mz", "rt", "ccs", "mean_bio_abundance"):
        a1 = d.loc[d.membrane_tier.isin(["1_massbalance", "2_formula", "2_facility"]), f]
        a0 = d.loc[d.membrane_tier == "3_model", f]
        print(f"   {f:20s} median  labelled {a1.median():12.2f}   model-called {a0.median():12.2f}")
    print("   The model is called on features that are systematically smaller, earlier")
    print("   and fainter than anything it was trained on. That is the tier-3 risk, and")
    print("   it is why every downstream test is also run on the tier-1 set alone.")

    print("\n== sanity check against known E. coli composition")
    f1 = d.loc[mem & (d.curvature_tier != "3_model"), :]
    fa = d.loc[mem, :]
    for name, s in (("tier 1-2 only", f1), ("all tiers", fa)):
        w = s.mean_bio_abundance.fillna(0.0)
        cf = w[s.curvature_prior == "curvature-forcing"].sum()
        bf = w[s.curvature_prior == "bilayer-forming"].sum()
        cnt = s.curvature_prior.value_counts()
        print(f"   {name:14s} signal forcing:bilayer = {100 * cf / max(cf + bf, 1e-9):4.1f}%"
              f" : {100 * bf / max(cf + bf, 1e-9):4.1f}%"
              f"   (by feature count {cnt.get('curvature-forcing', 0)}"
              f":{cnt.get('bilayer-forming', 0)})")
    print("   E. coli membrane is ~70-80% PE by mass. A model tier that pushes the")
    print("   feature COUNT the other way is a covariate-shift artefact to report,")
    print("   not a composition to believe -- which is what the signal share is for.")

    out_cols = ["feature_id", "polarity", "mz", "rt", "ccs", "neutral_mass", "adduct",
                "mean_bio_abundance", "final_class", "super_class",
                "label_membrane", "membrane", "membrane_tier", "membrane_p", "model_p",
                "group_called", "group_source", "curv_p",
                "n_acyl_called", "n_acyl_source",
                "curvature_prior", "curvature_strict", "curvature_tier",
                "channel", "chains", "residue_err_mda"]
    out = d[out_cols].copy()
    PUBLISH.mkdir(parents=True, exist_ok=True)
    out.to_csv(common.IDENT_DIR / "membrane_calls.csv", index=False)
    out.to_csv(PUBLISH / "membrane_calls.csv", index=False)

    perf = pd.DataFrame([
        {"model": k, "auc_mean": v["auc_mean"], "auc_sd": v["auc_sd"],
         **confusion(v["y"], v["oof"])} for k, v in cvs.items()
    ] + [{"model": "B curvature (canonical)", "auc_mean": cvb["auc_mean"],
          "auc_sd": cvb["auc_sd"], **confusion(cvb["y"], cvb["oof"])},
         {"model": "B curvature (shuffled control)", "auc_mean": cvb_null["auc_mean"],
          "auc_sd": cvb_null["auc_sd"], **confusion(cvb_null["y"], cvb_null["oof"])}])
    perf.to_csv(PUBLISH / "membrane_classifier_performance.csv", index=False)
    conf.to_csv(PUBLISH / "membrane_label_conflicts.csv", index=False)
    print(f"\nwrote {PUBLISH}/membrane_calls.csv")
    return out


if __name__ == "__main__":
    run()

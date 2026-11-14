"""Does the headgroup classifier work? Measure it before believing it.

The facility named 86 of the 2180 features to a lipid class. Those names were not
used to build the classifier and are held out here as labels: running the classifier
blind over them gives a confusion matrix per axis, which is the only thing that says
what the indeterminate rate costs and whether a negative call carries information.

Sensitivity measured this way is an UPPER bound and is reported as one. The labelled
features are library matches -- they are the features with clean, intense, spectra,
which is exactly why a library could match them. The dark features the classifier
will mostly face are harder by construction.

Specificity rests on a small arm: the non-phospholipid labels number single digits.
A point estimate off nine features would be misleading, so a Wilson interval is
reported alongside.

Also measured here, and for the same reason the last attempt failed: the BASE RATE of
every axis on this feature table. An enrichment read against an assumed base rate is
how a modal outcome gets mistaken for a finding.

Run:  mamba run -n p312 python -m identify.headgroup_validate    (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lipidio  # noqa: E402
from identify import common  # noqa: E402

# Facility class -> ground truth on each axis. Only classes the facility actually
# used in this dataset are listed; anything else is left unlabelled rather than
# guessed at.
TRUTH = {
    #                 phospholipid, headgroup, curvature
    # Truth is stated at the RESOLUTION THE METHOD CAN REACH. PE and PC are exactly
    # degenerate by mass (3xCH2), so a PC labelled "PE/PC" is a correct call, not a
    # miss, and scoring it as a miss would measure the degeneracy rather than the
    # classifier. Curvature truth uses the prior column for the same reason.
    "PE":        ("yes", "PE/PC", "cone"),
    "PE-NMe":    ("yes", "PE/PC", "cone"),
    "PG":        ("yes", "PG", "cylinder"),
    "PC":        ("yes", "PE/PC", "cylinder"),
    "PS":        ("yes", "PS", "cylinder"),
    "PA":        ("yes", "PA/PI/neutral", "cone"),
    "LPE":       ("yes", "PE/PC", "inverted-cone"),
    "LysoPE":    ("yes", "PE/PC", "inverted-cone"),
    "LysoPC":    ("yes", "PE/PC", "inverted-cone"),
    "TG":        ("no", "PA/PI/neutral", None),
    "MG":        ("no", "PA/PI/neutral", None),
    "SPB":       ("no", None, None),
}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load() -> pd.DataFrame:
    calls = pd.read_csv(common.IDENT_DIR / "full_headgroup_calls.csv")
    clean = pd.read_csv(lipidio.MS_FEATURES_CLEAN,
                        usecols=["feature_id", "lipid_class", "lipid_name"])
    d = calls.merge(clean, on="feature_id", how="left")
    if len(d) != len(calls):
        raise AssertionError("join to features_clean duplicated rows")
    t = d.lipid_class.map(lambda c: TRUTH.get(str(c).strip()))
    d["true_pl"] = t.map(lambda x: x[0] if x else None)
    d["true_hg"] = t.map(lambda x: x[1] if x else None)
    d["true_curv"] = t.map(lambda x: x[2] if x else None)
    return d


def _matrix(d: pd.DataFrame, truth_col: str, call_col: str, title: str) -> None:
    sub = d[d[truth_col].notna()]
    print(f"\n== {title}   (n = {len(sub)} labelled)")
    if not len(sub):
        return
    ct = pd.crosstab(sub[truth_col], sub[call_col], margins=True)
    print(ct.to_string())


def report() -> pd.DataFrame:
    d = load()
    n = len(d)
    print(f"features: {n}   labelled by the facility: {int(d.true_pl.notna().sum())}")

    # ---------------------------------------------------------------- base rates
    print("\n" + "=" * 68)
    print("BASE RATES on this feature table -- measured, not assumed")
    print("=" * 68)
    for axis in ("phospholipid", "headgroup_group", "curvature", "curvature_prior", "contains_N"):
        print(f"\n  {axis}")
        vc = d[axis].value_counts(dropna=False)
        for k, v in vc.items():
            print(f"    {str(k):<16} {v:5d}  {100 * v / n:5.1f}%")
        # The rate among features that got any call at all -- the number an
        # enrichment should actually be read against.
        called = d[~d[axis].isin(["indeterminate"])]
        if len(called):
            print(f"    -> among the {len(called)} determinate features:")
            for k, v in called[axis].value_counts().items():
                print(f"       {str(k):<14} {100 * v / len(called):5.1f}%")

    # ------------------------------------------------------------- confusion
    print("\n" + "=" * 68)
    print("VALIDATION against the held-out facility class labels")
    print("=" * 68)
    _matrix(d, "true_pl", "phospholipid", "phospholipid: truth (rows) x call (cols)")
    _matrix(d, "true_hg", "headgroup_group", "headgroup group: truth x call")
    _matrix(d, "true_curv", "curvature", "curvature STRICT: truth x call")
    _matrix(d, "true_curv", "curvature_prior", "curvature under the E. coli prior (PE/PC read as PE)")

    lab = d[d.true_pl.notna()]
    pos, neg = lab[lab.true_pl == "yes"], lab[lab.true_pl == "no"]
    tp = int((pos.phospholipid == "yes").sum())
    fn = int((pos.phospholipid == "no").sum())
    ip = int((pos.phospholipid == "indeterminate").sum())
    tn = int((neg.phospholipid == "no").sum())
    fp = int((neg.phospholipid == "yes").sum())
    inn = int((neg.phospholipid == "indeterminate").sum())

    print("\n== phospholipid gate, headline numbers")
    print(f"  true phospholipids   n={len(pos)}   called yes {tp}, no {fn}, "
          f"indeterminate {ip}")
    print(f"  true non-phospho     n={len(neg)}   called no  {tn}, yes {fp}, "
          f"indeterminate {inn}")
    if tp + fn:
        lo, hi = wilson(tp, tp + fn)
        print(f"  sensitivity (of determinate) {tp}/{tp + fn} = "
              f"{100 * tp / (tp + fn):.1f}%   95% CI {100 * lo:.0f}-{100 * hi:.0f}%"
              "   <- UPPER BOUND: these are library-matched, i.e. easy")
    if tn + fp:
        lo, hi = wilson(tn, tn + fp)
        print(f"  specificity (of determinate) {tn}/{tn + fp} = "
              f"{100 * tn / (tn + fp):.1f}%   95% CI {100 * lo:.0f}-{100 * hi:.0f}%"
              f"   <- only {tn + fp} features; the interval is the honest reading")

    # ----------------------------------------------------------------- controls
    print("\n== the three positive controls, called blind")
    for fid, spec in sorted(common.CONTROL_FEATURES.items()):
        r = d[d.feature_id == fid]
        if not len(r):
            print(f"  {fid}  ABSENT from the analysed set")
            continue
        r = r.iloc[0]
        want = "PG" if spec["class"] == "HBMP" else spec["class"]
        got = r.headgroup_group
        ok = "PASS" if got == want else "MISS"
        print(f"  {fid}  expect {spec['name']} ({want} headgroup)  ->  "
              f"phospholipid={r.phospholipid}  headgroup={r.headgroup}  "
              f"n_acyl={r.n_acyl}  [{ok}]   chains: {r.chains}  err {r.residue_err_mda} mDa")

    # ------------------------------------------------- what the tier costs
    print("\n== call rate by evidence channel")
    print(pd.crosstab(d.channel, d.phospholipid, margins=True).to_string())
    print("\n== call rate by polarity")
    print(pd.crosstab(d.polarity.fillna("none"), d.phospholipid, margins=True).to_string())

    d.to_csv(common.IDENT_DIR / "full_headgroup_validated.csv", index=False)
    return d


if __name__ == "__main__":
    report()

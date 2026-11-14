"""Score MS2Lipid against every piece of evidence this dataset already holds.

Nothing downstream may depend on MS2Lipid until this runs and is read. The point
is not to reproduce the paper's 97% -- that was measured on curated spectra from
other instruments -- but to find out what it does on OUR Bruker timsTOF DDA-PASEF
consensus spectra, separately in each polarity, against evidence MS2Lipid never
sees.

Five yardsticks, all independent of the model:

  1. negative-mode MS/MS mass balance    (headgroup.py, acyl-carboxylate channel)
  2. positive-mode diagnostic ions       (headgroup neutral losses / phosphocholine)
  3. the facility's own class assignment (MetaboScape annotation tiers)
  4. three blind positive controls       (2 HBMP, 1 PS -- known answers, run blind)
  5. cross-polarity twin pairs           (same neutral mass + RT in both modes)

Plus a plausibility audit: what fraction of calls name a class E. coli cannot make.
MS2Lipid is closed-world over 97 subclasses, so it always returns one; the only way
to see that failure mode is to count it.

Env: p312.  Run:  mamba run -n p312 python research/fabfos/lipidomics/identify/ms2lipid_validate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

REFS = Path(__file__).resolve().parent / "refs"
PRED = common.IDENT_DIR / "ms2lipid_predictions.csv"
OUT = common.IDENT_DIR / "ms2lipid_validation.csv"

# The facility's RefMet/Goslin class names against MS2Lipid's MS-DIAL shorthand.
# O- is the ether variant, -P the plasmalogen, L- the lyso form. Only classes the
# facility actually emitted on this dataset are listed; anything else abstains
# from the comparison rather than being guessed at.
FACILITY_TO_MS2LIPID = {
    "PE": "PE", "PG": "PG", "PC": "PC", "PS": "PS", "PA": "PA",
    "LPE": "LPE", "LPC": "LPC", "HBMP": "HBMP",
    "O-PE": "EtherPE", "O-PC": "EtherPC", "O-PG": "EtherPG",
    "O-PS": "EtherPS", "O-PA": "PA",
    "PE-P": "EtherPE", "PC-P": "EtherPC",
    "TAG": "TG", "DAG": "DG", "MAG": "MG", "O-DG": "EtherDG",
    "Ubiquinones": "CoQ",
}
# Facility classes deliberately NOT crosswalked: EPC, PE-NMe, SPB, HOME,
# Vitamin E, Vitamin K, Porphyrins, N-acyl amines. Some are outside MS2Lipid's
# vocabulary entirely (porphyrins, vitamin K), so scoring them would measure the
# vocabulary gap, not the model.

TWIN_PPM = 10.0
TWIN_RT_MIN = 0.10


def load() -> pd.DataFrame:
    pred = pd.read_csv(PRED)
    ref = pd.read_csv(REFS / "lipid_class_reference.tsv", sep="\t", comment="#")
    hg = pd.read_csv(common.IDENT_DIR / "full_headgroup_validated.csv")
    man = pd.read_csv(common.IDENT_DIR / "full_manifest.csv")
    tiers = pd.read_csv(common.METABOSCAPE_DIR / "annotation_tiers.csv")

    d = pred.merge(ref.add_prefix("ref_"), left_on="ms2lipid_class",
                   right_on="ref_class", how="left")
    d = d.merge(hg[["feature_id", "channel", "headgroup_group", "n_acyl",
                    "phospholipid"]], on="feature_id", how="left")
    d = d.merge(tiers[["feature_id", "final_class", "super_class", "name"]],
                on="feature_id", how="left")
    d = d.merge(man[["feature_id", "neutral_mass"]], on="feature_id", how="left")
    d["facility_ms2lipid"] = d.final_class.map(FACILITY_TO_MS2LIPID)
    unmapped = set(d.ms2lipid_class.dropna()) - set(ref["class"])
    if unmapped:
        raise SystemExit(f"subclasses outside the reference table: {sorted(unmapped)}")
    return d


def agreement(d: pd.DataFrame, mask: pd.Series, truth_col: str,
              pred_col: str, label: str) -> dict:
    s = d[mask & d[truth_col].notna() & d[pred_col].notna()]
    if s.empty:
        return {"yardstick": label, "n": 0}
    hit = (s[truth_col] == s[pred_col])
    return {"yardstick": label, "n": len(s), "agree": int(hit.sum()),
            "accuracy": round(float(hit.mean()), 4),
            "median_p_agree": round(float(s.ms2lipid_p[hit].median()), 3)
            if hit.any() else np.nan,
            "median_p_disagree": round(float(s.ms2lipid_p[~hit].median()), 3)
            if (~hit).any() else np.nan}


def confusion(d: pd.DataFrame, mask: pd.Series, truth: str, pred: str) -> str:
    s = d[mask & d[truth].notna() & d[pred].notna()]
    if s.empty:
        return "(empty)"
    return pd.crosstab(s[truth], s[pred]).to_string()


def coverage_curve(d: pd.DataFrame, man: pd.DataFrame) -> pd.DataFrame:
    """Coverage on BOTH axes as the probability floor moves.

    Feature coverage and signal coverage are different numbers and the gap is the
    whole reason the 95% target had to be pinned to one of them. Both are reported
    at every floor so neither can be quoted without the other.
    """
    total_feat = len(man)
    total_sig = man.mean_bio_abundance.sum()
    rows = []
    for floor in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        ok = d[d.ms2lipid_p >= floor]
        memb = ok[ok.ref_membrane.isin(["yes", "no"])]
        rows.append({
            "p_floor": floor,
            "n_called": len(ok),
            "feature_cov": round(len(ok) / total_feat, 4),
            "signal_cov": round(ok.mean_bio_abundance.sum() / total_sig, 4),
            "n_membrane_decided": len(memb),
            "memb_feature_cov": round(len(memb) / total_feat, 4),
            "memb_signal_cov": round(memb.mean_bio_abundance.sum() / total_sig, 4),
            "frac_non_native": round(float((ok.ref_native_ecoli == "no").mean()), 4),
            "signal_frac_non_native": round(
                float(ok.loc[ok.ref_native_ecoli == "no", "mean_bio_abundance"].sum()
                      / max(ok.mean_bio_abundance.sum(), 1e-12)), 4),
        })
    return pd.DataFrame(rows)


def twins(d: pd.DataFrame) -> pd.DataFrame:
    """Features that are the same molecule seen in both polarities.

    A consistency check only. The earlier design pass measured that twin transfer
    adds 15 features as a coverage mechanism and that 113 named twin pairs agree
    on the name zero times, so this is here to score MS2Lipid's self-consistency
    across ion mode, not to fill anything in.
    """
    pos = d[(d.polarity == "pos") & d.neutral_mass.notna()].reset_index(drop=True)
    neg = d[(d.polarity == "neg") & d.neutral_mass.notna()].reset_index(drop=True)
    out = []
    nm = neg.neutral_mass.to_numpy()
    for r in pos.itertuples():
        tol = TWIN_PPM * 1e-6 * r.neutral_mass
        m = (np.abs(nm - r.neutral_mass) <= tol) & \
            (np.abs(neg.rt.to_numpy() - r.rt) <= TWIN_RT_MIN)
        for j in np.flatnonzero(m):
            n = neg.iloc[j]
            out.append({"pos_id": r.feature_id, "neg_id": n.feature_id,
                        "pos_class": r.ms2lipid_class, "neg_class": n.ms2lipid_class,
                        "pos_p": r.ms2lipid_p, "neg_p": n.ms2lipid_p,
                        "pos_group": r.ref_headgroup_group,
                        "neg_group": n.ref_headgroup_group,
                        "pos_membrane": r.ref_membrane,
                        "neg_membrane": n.ref_membrane})
    return pd.DataFrame(out)


def main() -> None:
    d = load()
    man = pd.read_csv(common.IDENT_DIR / "full_manifest.csv")

    print("=" * 78)
    print("MS2Lipid on SCADC consensus spectra -- validation")
    print("=" * 78)
    print(f"predicted: {len(d)} of {len(man)} features "
          f"({len(d)/len(man):.1%} of features, "
          f"{d.mean_bio_abundance.sum()/man.mean_bio_abundance.sum():.2%} of signal)")

    # ---------------------------------------------------------------- plausibility
    print("\n--- PLAUSIBILITY: does the call name something E. coli can make? ---")
    plaus = d.groupby("polarity").ref_native_ecoli.value_counts(normalize=True)
    print(plaus.round(3).to_string())
    print("\ntop non-native classes called (feature count, signal share):")
    nn = d[d.ref_native_ecoli == "no"]
    tot_sig = d.mean_bio_abundance.sum()
    tab = nn.groupby(["polarity", "ms2lipid_class"]).agg(
        n=("feature_id", "size"), signal=("mean_bio_abundance", "sum"))
    tab["signal_pct"] = (100 * tab.signal / tot_sig).round(2)
    print(tab.sort_values("n", ascending=False).groupby(level=0).head(6)
          .drop(columns="signal").to_string())

    # ------------------------------------------------------------------ yardsticks
    print("\n--- YARDSTICK 1+2: our own MS/MS evidence, per polarity ---")
    rows = [
        agreement(d, d.channel == "mass-balance", "headgroup_group",
                  "ref_headgroup_group", "neg mass-balance (group)"),
        agreement(d, d.channel == "pos-diagnostic-ion", "headgroup_group",
                  "ref_headgroup_group", "pos diagnostic-ion (group)"),
        agreement(d, d.final_class.notna(), "facility_ms2lipid",
                  "ms2lipid_class", "facility class (subclass)"),
        agreement(d, (d.final_class.notna()) & (d.polarity == "pos"),
                  "facility_ms2lipid", "ms2lipid_class",
                  "facility class (subclass), pos"),
        agreement(d, (d.final_class.notna()) & (d.polarity == "neg"),
                  "facility_ms2lipid", "ms2lipid_class",
                  "facility class (subclass), neg"),
        agreement(d, d.phospholipid.isin(["yes", "no"]), "phospholipid",
                  "ref_membrane", "membrane gate vs mass balance"),
    ]
    summ = pd.DataFrame(rows)
    print(summ.to_string(index=False))

    print("\nconfusion, neg mass-balance (rows = mass balance, cols = MS2Lipid):")
    print(confusion(d, d.channel == "mass-balance", "headgroup_group",
                    "ref_headgroup_group"))
    print("\nconfusion, pos diagnostic-ion:")
    print(confusion(d, d.channel == "pos-diagnostic-ion", "headgroup_group",
                    "ref_headgroup_group"))
    print("\nconfusion, facility subclass (rows = facility, cols = MS2Lipid):")
    print(confusion(d, d.final_class.notna(), "facility_ms2lipid", "ms2lipid_class"))

    # ---------------------------------------------------------- yardstick 4: blind
    print("\n--- YARDSTICK 4: the three blind controls, named individually ---")
    for fid, meta in common.CONTROL_FEATURES.items():
        r = d[d.feature_id == fid]
        if r.empty:
            print(f"  {fid}  expected {meta['class']:5s}  -> NO PREDICTION (abstained)")
            continue
        r = r.iloc[0]
        mark = "HIT " if r.ms2lipid_class == meta["class"] else "MISS"
        print(f"  {fid}  expected {meta['class']:5s}  got {str(r.ms2lipid_class):10s}"
              f" p={r.ms2lipid_p:.3f}  peaks={r.n_peaks_consensus:3d}  [{mark}]")
        print(f"        candidates: {r.ms2lipid_candidates}")

    # ----------------------------------------------------------- yardstick 5: twins
    print("\n--- YARDSTICK 5: cross-polarity twins ---")
    tw = twins(d)
    if len(tw):
        same_cls = (tw.pos_class == tw.neg_class).mean()
        same_grp = (tw.pos_group == tw.neg_group)
        both_grp = tw.pos_group.notna() & tw.neg_group.notna()
        print(f"  {len(tw)} twin pairs at {TWIN_PPM:.0f} ppm / {TWIN_RT_MIN} min")
        print(f"  same subclass       : {same_cls:.1%}")
        print(f"  same headgroup group: {same_grp[both_grp].mean():.1%} "
              f"(of {int(both_grp.sum())} pairs where both map)")
        print(f"  same membrane call  : "
              f"{(tw.pos_membrane == tw.neg_membrane).mean():.1%}")
        tw.to_csv(common.IDENT_DIR / "ms2lipid_twins.csv", index=False)

    # ------------------------------------------------------------------- coverage
    print("\n--- COVERAGE vs PROBABILITY FLOOR (both axes, of all 2180 features) ---")
    print(coverage_curve(d, man).to_string(index=False))

    d.to_csv(OUT, index=False)
    print(f"\n[write] {OUT}")


if __name__ == "__main__":
    main()

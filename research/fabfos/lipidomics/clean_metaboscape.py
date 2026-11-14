"""T2: QC/blank cleanup for the MetaboScape facility table.

Reads the raw facility xlsx (via lipidio.load_metaboscape), then:
  1. BLANK FILTER  — keep a feature if its max biological-group mean is at least
     BLANK_RATIO× the mean across the 12 process blanks (drops carryover/solvent).
  2. QC-CV FILTER  — drop a feature if, in every QC flavor where it is detected,
     its CV across the QC injections exceeds QC_CV_MAX (drops irreproducible
     features). Features absent from all QC are kept (cannot be assessed).

Intensities stay RAW here — per-sample median normalization + log2 happen
downstream in the diff/overview scripts (same as the MS-DIAL path), so the
cleaned table is comparable across tools.

Writes to data/fabfos/runs/scadc_lipidomics/processed/metaboscape/:
  - features_clean.csv   feature metadata + the 48 biological-sample columns
  - metadata_bio.csv     one row per biological sample (the 48)
  - filter_report.txt    feature counts in→out at each step

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/clean_metaboscape.py
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from lipidio import (
    METABOSCAPE_DIR, MS_FEATURES_CLEAN, MS_METADATA_BIO, MS_FEATURE_COLS,
    load_metaboscape,
)

# --- filter thresholds (top-of-file knobs) ---------------------------------------
BLANK_RATIO = 5.0   # bio max-group mean must be >= 5x the blank mean to keep
QC_CV_MAX = 0.30    # drop features with CV > 30% in every QC flavor they appear in


def _group_means(abund: pd.DataFrame, meta: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Mean intensity per (group) over the sample columns named in meta."""
    cols = meta["sample_basename"].tolist()
    sub = abund[cols]
    grouping = meta.set_index("sample_basename").loc[cols, keys].agg("|".join, axis=1)
    return sub.T.groupby(grouping.values).mean().T  # features × groups


def run() -> None:
    METABOSCAPE_DIR.mkdir(parents=True, exist_ok=True)
    feats, abund, smeta = load_metaboscape()
    n0 = len(feats)
    lines = [f"MetaboScape clean — {n0} features in, {abund.shape[1]} sample columns"]

    bio = smeta[smeta.sample_type == "sample"]
    blanks = smeta[smeta.sample_type == "blank"]
    qc = smeta[smeta.sample_type == "qc"]
    lines.append(f"  samples: {len(bio)} biological, {len(qc)} QC, {len(blanks)} blank")

    # 1) BLANK FILTER -------------------------------------------------------------
    bio_grp = _group_means(abund, bio, ["strain", "treatment", "fraction"])
    bio_max = bio_grp.max(axis=1)
    blank_mean = abund[blanks["sample_basename"].tolist()].mean(axis=1)
    # ratio with a tiny floor so blank_mean==0 (clean) keeps a detected feature
    ratio = bio_max / blank_mean.replace(0, np.nan)
    keep_blank = (blank_mean <= 0) & (bio_max > 0) | (ratio >= BLANK_RATIO)
    n1 = int(keep_blank.sum())
    lines.append(f"  blank filter (bio_max >= {BLANK_RATIO}x blank_mean): {n0} -> {n1} "
                 f"(dropped {n0 - n1})")

    # 2) QC-CV FILTER -------------------------------------------------------------
    # CV per QC flavor (P, SN/S); keep if reproducible (CV<=max) in >=1 flavor it
    # is detected in, or if absent from all QC (cannot assess).
    detected_any = pd.Series(False, index=abund.index)
    pass_any = pd.Series(False, index=abund.index)
    cv_by_flavor = []
    for frac, grp in qc.groupby("fraction"):
        cols = grp["sample_basename"].tolist()
        if len(cols) < 2:
            continue
        sub = abund[cols]
        mean = sub.mean(axis=1)
        cv = sub.std(axis=1, ddof=1) / mean.replace(0, np.nan)
        detected = mean > 0
        detected_any |= detected
        pass_any |= detected & (cv <= QC_CV_MAX)
        cv_by_flavor.append(cv)
    qc_cv_min = pd.concat(cv_by_flavor, axis=1).min(axis=1) if cv_by_flavor else pd.Series(np.nan, index=abund.index)
    # keep: not detected in any QC (can't judge) OR reproducible in some flavor
    qc_keep = (~detected_any) | pass_any
    keep = keep_blank & qc_keep
    n2 = int(keep.sum())
    lines.append(f"  QC-CV filter (CV <= {QC_CV_MAX:.0%} in >=1 QC flavor): {n1} -> {n2} "
                 f"(dropped {int((keep_blank & ~qc_keep).sum())} reproducibility failures; "
                 f"{int((~detected_any).sum())} features absent from QC kept)")

    feats_k = feats[keep].copy()
    abund_k = abund.loc[keep, bio["sample_basename"].tolist()].copy()

    # add CV diagnostics to feature metadata
    feats_k["qc_cv_min"] = qc_cv_min[keep]
    feats_k["blank_ratio"] = ratio[keep]

    out = feats_k.join(abund_k)
    out.index.name = "feature_id"
    out.to_csv(MS_FEATURES_CLEAN)
    bio.to_csv(MS_METADATA_BIO, index=False)

    lines.append(f"  lipid-class annotated (parse_shorthand): "
                 f"{int(feats_k['lipid_class'].notna().sum())}; "
                 f"flagged is_lipid: {int(feats_k['is_lipid'].sum())}")
    lines.append(f"\nwrote {MS_FEATURES_CLEAN} ({n2} features x {abund_k.shape[1]} bio samples)")
    lines.append(f"wrote {MS_METADATA_BIO} ({len(bio)} samples)")
    report = "\n".join(lines)
    (METABOSCAPE_DIR / "filter_report.txt").write_text(report + "\n")
    print(report)


if __name__ == "__main__":
    run()

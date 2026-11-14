"""Manifest for every analysed feature, not just the clone-response hits.

`build_manifest` assembles the 29 hits and their panel context. The headgroup
classifier needs the same evidence for the whole table, because a classifier that
only ever ran on hits cannot supply a null. This module reuses that module's
facility reader and `common.resolve_adduct` verbatim -- only the query set and the
target-sample rule change -- and writes to its own file so the published
identification lane keeps its inputs.

The analysed set is the 2180 rows of `features_clean.csv`: the facility table after
the blank-ratio and QC-CV filters in clean_metaboscape.py. Feature ids survive that
filter, so the join back to the facility metadata is by id and nothing is reindexed.

Every analysed feature appears in the output exactly once. Features with no
resolvable adduct keep a null polarity rather than being dropped -- downstream they
are indeterminate, which is a state, not an absence.

Run:  mamba run -n p312 python -m identify.full_manifest      (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lipidio  # noqa: E402
from identify import common  # noqa: E402
from identify.build_manifest import _read_facility  # noqa: E402

TOP_N_SAMPLES = 5
FULL_MANIFEST = "full_manifest.csv"


def _num(v) -> float | None:
    """Facility numerics, tolerant of the whole table rather than the 29 hits.

    The hit subset happened to be clean; the full table is not. mSigma carries a
    literal '∞' where the isotope fit failed, and blank cells appear in columns the
    hit lane always found populated. A failed parse becomes None, never a crash and
    never a zero -- a zero would read as a measurement.
    """
    x = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
    return None if pd.isna(x) else float(x)


def analysed_ids() -> list[str]:
    """Feature ids that survived the blank/QC filters -- the 2180."""
    df = pd.read_csv(lipidio.MS_FEATURES_CLEAN, usecols=["feature_id"])
    return df.feature_id.tolist()


def build() -> pd.DataFrame:
    common.ensure_dirs()
    meta, abund, runs = _read_facility()
    ids = analysed_ids()

    missing = [f for f in ids if f not in meta.index]
    if missing:
        raise KeyError(
            f"{len(missing)} analysed features absent from the facility table "
            f"(first few: {missing[:5]}) -- features_clean.csv and the xlsx have "
            "drifted; feature ids are row-order derived and cannot be reconciled"
        )

    bio_cols = [c for c in abund.columns if not c.startswith(("QC_", "Blank_"))]

    records = []
    for fid in ids:
        row = meta.loc[fid]
        mz = _num(row["mz meas."])
        neutral = _num(row["M meas."])
        ions = common.parse_ions(row["Ions"])
        if mz is None or neutral is None:
            adduct, err = None, None
        else:
            adduct, err = common.resolve_adduct(mz, neutral, ions)

        series = abund.loc[fid, bio_cols].sort_values(ascending=False)
        targets = [s for s in series.index[:TOP_N_SAMPLES] if series[s] > 0]

        records.append(
            {
                "feature_id": fid,
                "name": row["Name"],
                "formula": row["Molecular Formula"],
                "annotations": row["Annotations"],
                "mz": mz,
                "rt": _num(row["RT [min]"]),
                "ccs": _num(row["CCS (A2)"]),
                "neutral_mass": neutral,
                "adduct": adduct,
                "adduct_err_da": None if err is None else round(err, 6),
                "adducts_listed": ";".join(ions),
                "polarity": None if adduct is None else common.adduct_polarity(adduct),
                "charge": None if adduct is None else common.ADDUCTS[adduct][1],
                "msigma": _num(row["mSigma"]),
                "has_msms": bool(row["MS/MS"]),
                "msms_score": _num(row["MS/MS score"]),
                "mean_bio_abundance": float(abund.loc[fid, bio_cols].mean()),
                "target_samples": ";".join(targets),
                "is_control": fid in common.CONTROL_FEATURES,
            }
        )

    df = pd.DataFrame(records).set_index("feature_id")
    if len(df) != len(ids) or df.index.duplicated().any():
        raise AssertionError("manifest is not one row per analysed feature")

    df.to_csv(common.IDENT_DIR / FULL_MANIFEST)
    # The hit lane already wrote this; rewriting it from the same source is a
    # no-op, but keeps the full lane runnable on its own.
    (common.IDENT_DIR / "sample_runs.json").write_text(
        json.dumps({k: {"pos": v[0], "neg": v[1]} for k, v in runs.items()}, indent=2)
    )
    return df


def _report(df: pd.DataFrame) -> None:
    n = len(df)
    print(f"analysed features            {n}")
    print(f"  adduct resolved            {df.adduct.notna().sum()}")
    print(f"  UNRESOLVED adduct          {df.adduct.isna().sum()}   -> indeterminate")
    print(f"  MS/MS acquired             {int(df.has_msms.sum())}")
    print(f"  MS/MS acquired + polarity  "
          f"{int((df.has_msms & df.polarity.notna()).sum())}   <- extractable")
    print(f"  facility formula           {df.formula.notna().sum()}")
    print(f"  controls present           {int(df.is_control.sum())} / 3")
    print()
    print("  by polarity (features with MS/MS):")
    sub = df[df.has_msms]
    for pol, k in sub.polarity.value_counts(dropna=False).items():
        print(f"    {str(pol):<8} {k}")
    print()
    print("  charge states:")
    for c, k in df.charge.value_counts(dropna=False).items():
        print(f"    {str(c):<8} {k}")
    bad = df[df.adduct.isna()]
    if len(bad):
        print(f"\n  unresolved-adduct features carry MS/MS: "
              f"{int(bad.has_msms.sum())} of {len(bad)}")


if __name__ == "__main__":
    _report(build())

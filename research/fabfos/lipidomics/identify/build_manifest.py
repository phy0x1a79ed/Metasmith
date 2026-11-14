"""T1 -- assemble the clone-response hit features with all of their evidence.

`lipidio.load_metaboscape` keeps 8 of the facility table's 14 metadata columns.
The 6 it drops are exactly the ones identification needs: the deconvoluted
neutral mass, the adduct list, the isotope-pattern fit, the MS/MS-acquired flag,
the mass error and the structure flag. This module reads the xlsx directly to
keep them, while reusing lipidio's feature-id convention (row order -> F####) so
the ids stay joinable with every other table in the project.

It also recovers each sample's POS and NEG raw-run numbers from the column
headers, which is what lets T3 open the right mzML.

Run:  mamba run -n p312 python -m identify.build_manifest      (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lipidio  # noqa: E402
from identify import common  # noqa: E402

# Facility metadata columns, by position in sheet `Clean`.
META_COLS = [
    "Name", "Molecular Formula", "Annotations", "Structure", "RT [min]",
    "CCS (A2)", "dCCS [%]", "mz meas.", "dmz [ppm]", "M meas.", "mSigma",
    "Ions", "MS/MS", "MS/MS score",
]
N_META = 14
TOP_N_SAMPLES = 5


def _read_facility() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, tuple[str, str]]]:
    """Return (feature metadata, abundance, sample -> (pos_run, neg_run))."""
    path = lipidio._metaboscape_xlsx()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb["Clean"].iter_rows(min_row=2, values_only=True))
    header, data = rows[0], rows[1:]

    sample_headers = list(header[N_META:])
    keys, runs = [], {}
    for h in sample_headers:
        parsed = lipidio.parse_metaboscape_header(str(h))
        if parsed is None:
            raise ValueError(f"unparsed sample header: {h!r}")
        key = parsed["sample_basename"]
        keys.append(key)
        pair = common.parse_sample_runs(h)
        if pair is None:
            raise ValueError(f"no POS/NEG run numbers in header: {h!r}")
        runs[key] = pair

    ids = [f"F{i + 1:04d}" for i in range(len(data))]
    meta = pd.DataFrame(
        [list(r[:N_META]) for r in data], index=ids, columns=META_COLS
    )
    meta.index.name = "feature_id"
    abund = pd.DataFrame(
        [list(r[N_META:]) for r in data], index=ids, columns=keys
    ).apply(pd.to_numeric, errors="coerce").fillna(0.0)
    abund.index.name = "feature_id"
    return meta, abund, runs


def _hit_context() -> tuple[list[str], dict[str, list[dict]]]:
    """Feature ids from the clone-response hits, plus each hit's panel context."""
    with open(common.HITS_CSV) as fh:
        rows = list(csv.DictReader(fh))
    ctx: dict[str, list[dict]] = {}
    for r in rows:
        ctx.setdefault(r["feature_id"], []).append(
            {
                "clone": r["clone"],
                "fraction": r["fraction"],
                "comparison": r["comparison"],
                "direction": r["direction"],
                "log2fc": float(r["log2fc"]),
            }
        )
    return sorted(ctx), ctx


def build() -> pd.DataFrame:
    common.ensure_dirs()
    feature_ids, ctx = _hit_context()
    meta, abund, runs = _read_facility()

    missing = [f for f in feature_ids if f not in meta.index]
    if missing:
        raise KeyError(f"hit features absent from the facility table: {missing}")

    bio_cols = [c for c in abund.columns if not c.startswith(("QC_", "Blank_"))]

    records = []
    for fid in feature_ids:
        row = meta.loc[fid]
        mz = float(row["mz meas."])
        neutral = float(row["M meas."])
        ions = common.parse_ions(row["Ions"])
        adduct, err = common.resolve_adduct(mz, neutral, ions)

        series = abund.loc[fid, bio_cols].sort_values(ascending=False)
        top = [s for s in series.index[:TOP_N_SAMPLES] if series[s] > 0]

        # The runs worth pulling spectra from: the strongest samples overall,
        # plus the strongest inside each panel the feature was called in, since
        # those are the samples the biological claim rests on.
        panel_samples = []
        for c in ctx[fid]:
            frac = "P" if c["fraction"] == "pellet" else "S"
            cols = [s for s in bio_cols if s.startswith(f"{c['clone']}_") and f"_{frac}_" in s]
            if cols:
                panel_samples.append(abund.loc[fid, cols].idxmax())
        targets = list(dict.fromkeys(top + panel_samples))

        records.append(
            {
                "feature_id": fid,
                "name": row["Name"],
                "is_placeholder": pd.isna(row["Molecular Formula"]),
                "formula": row["Molecular Formula"],
                "annotations": row["Annotations"],
                "mz": mz,
                "rt": float(row["RT [min]"]),
                "ccs": None if pd.isna(row["CCS (A2)"]) else float(row["CCS (A2)"]),
                "neutral_mass": neutral,
                "adduct": adduct,
                "adduct_err_da": None if err is None else round(err, 6),
                "adducts_listed": ";".join(ions),
                "polarity": None if adduct is None else common.adduct_polarity(adduct),
                "msigma": None if pd.isna(row["mSigma"]) else float(row["mSigma"]),
                "has_msms": bool(row["MS/MS"]),
                "msms_score": None if pd.isna(row["MS/MS score"]) else float(row["MS/MS score"]),
                "n_panels": len(ctx[fid]),
                "panels": " | ".join(
                    f"{c['clone']}/{c['fraction']}/{c['comparison']}{c['direction']}"
                    for c in ctx[fid]
                ),
                "target_samples": ";".join(targets),
                "is_control": fid in common.CONTROL_FEATURES,
            }
        )

    df = pd.DataFrame(records).set_index("feature_id")
    common.IDENT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(common.IDENT_DIR / "hit_manifest.csv")
    (common.IDENT_DIR / "sample_runs.json").write_text(
        json.dumps({k: {"pos": v[0], "neg": v[1]} for k, v in runs.items()}, indent=2)
    )
    return df


def _report(df: pd.DataFrame) -> None:
    n = len(df)
    print(f"features                {n}")
    print(f"  adduct resolved       {df.adduct.notna().sum()}")
    print(f"  MS/MS acquired        {int(df.has_msms.sum())}")
    print(f"  molecular formula     {df.formula.notna().sum()}")
    print(f"  CCS present           {df.ccs.notna().sum()}")
    print(f"  polarity pos / neg    {(df.polarity == 'pos').sum()} / {(df.polarity == 'neg').sum()}")
    print(f"  controls              {int(df.is_control.sum())}")
    bad = df[df.adduct.isna()]
    if len(bad):
        print("\nUNRESOLVED ADDUCTS (neutral mass does not reproduce m/z):")
        print(bad[["mz", "neutral_mass", "adducts_listed", "adduct_err_da"]].to_string())
    worst = df.adduct_err_da.abs().max()
    print(f"\nlargest adduct residual  {worst:.6f} Da")


if __name__ == "__main__":
    _report(build())

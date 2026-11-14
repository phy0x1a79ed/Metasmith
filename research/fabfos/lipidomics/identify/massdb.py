"""T1 -- offline neutral-mass search against the RefMet reference dump.

`refmet_db.csv` (206k rows, exact masses plus LIPID MAPS / HMDB / ChEBI / KEGG
cross-references) has sat in the data tree with no reader since it was fetched.
It is a complete offline mass search: no rate limit, no network, reproducible.
This makes it the first evidence stream, and it is also what supplies the class
vocabulary the rest of the project already uses.

Mass tolerance defaults to 5 ppm. The three features the facility did annotate
came back at 0.7, 0.9 and -2.2 ppm, so 5 ppm is a real bound on this instrument
rather than a guess.

Run:  mamba run -n p312 python -m identify.massdb            (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

PPM_TOL = 5.0
MAX_PER_FEATURE = 25

_DB: pd.DataFrame | None = None


def db() -> pd.DataFrame:
    """The RefMet dump, mass-sorted, cached per process."""
    global _DB
    if _DB is None:
        df = pd.read_csv(common.REFMET_DB, low_memory=False)
        df.columns = [c.strip() for c in df.columns]  # leading space on refmet_id
        df = df[df.exactmass.notna()].copy()
        df["exactmass"] = pd.to_numeric(df.exactmass, errors="coerce")
        _DB = df[df.exactmass.notna()].sort_values("exactmass").reset_index(drop=True)
    return _DB


def search(neutral_mass: float, ppm_tol: float = PPM_TOL) -> pd.DataFrame:
    """RefMet entries whose exact mass matches, nearest first."""
    d = db()
    window = neutral_mass * ppm_tol / 1e6
    lo, hi = d.exactmass.searchsorted(
        [neutral_mass - window, neutral_mass + window]
    )
    hit = d.iloc[lo:hi].copy()
    if hit.empty:
        return hit
    hit["ppm_error"] = common.ppm(neutral_mass, hit.exactmass)
    return hit.reindex(hit.ppm_error.abs().sort_values().index)


def _ids(row: pd.Series) -> str:
    parts = []
    for col, tag in (
        ("refmet_id", "RefMet"), ("lipidmaps_id", "LM"), ("hmdb_id", "HMDB"),
        ("kegg_id", "KEGG"), ("chebi_id", "ChEBI"), ("pubchem_cid", "PubChem"),
    ):
        v = row.get(col)
        if pd.notna(v) and str(v).strip():
            parts.append(f"{tag}:{str(v).strip()}")
    return ";".join(parts)


def run(ppm_tol: float = PPM_TOL) -> pd.DataFrame:
    manifest = pd.read_csv(common.IDENT_DIR / "hit_manifest.csv")
    rows, per_feature = [], {}
    for _, f in manifest.iterrows():
        hits = search(float(f.neutral_mass), ppm_tol)
        per_feature[f.feature_id] = len(hits)
        for _, h in hits.head(MAX_PER_FEATURE).iterrows():
            rows.append(
                common.candidate_row(
                    f.feature_id, "refmet_mass",
                    candidate_name=h.refmet_name,
                    formula=h.formula,
                    lipid_class=None if pd.isna(h.sub_class) else h.sub_class,
                    super_class=h.super_class,
                    main_class=h.main_class,
                    sub_class=h.sub_class,
                    exactmass=h.exactmass,
                    ppm_error=round(float(h.ppm_error), 3),
                    external_ids=_ids(h),
                    notes=f"neutral-mass match within {ppm_tol} ppm",
                )
            )
    out = pd.DataFrame(rows, columns=common.CANDIDATE_COLS)
    common.IDENT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(common.IDENT_DIR / "candidates_refmet_mass.csv", index=False)

    covered = sum(1 for n in per_feature.values() if n)
    print(f"RefMet offline mass search @ {ppm_tol} ppm")
    print(f"  database rows           {len(db())}")
    print(f"  features with >=1 hit   {covered}/{len(manifest)}")
    print(f"  candidate rows written  {len(out)}  (capped at {MAX_PER_FEATURE}/feature)")
    truncated = [k for k, v in per_feature.items() if v > MAX_PER_FEATURE]
    if truncated:
        print(f"  truncated features      {len(truncated)}: {', '.join(truncated)}")
    print("\n  per-feature hit counts:")
    for k, v in per_feature.items():
        mark = "  <- control" if k in common.CONTROL_FEATURES else ""
        print(f"    {k}  {v:4d}{mark}")
    return out


if __name__ == "__main__":
    run()

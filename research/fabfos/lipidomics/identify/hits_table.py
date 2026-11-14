"""T4 -- the clone-response hits table, with identifications joined on.

`05_clone_response/clone_response_storey_hits.csv` is the statistics: which
features moved, in which panel, by how much. It says nothing about what they
are. This writes the same rows with the identification columns appended, so the
result and the chemistry can be read in one place.

Written as a NEW file beside the original rather than over it: the statistics
table is an input to this lane and stays as it was.

Row count matches the source exactly, including the feature that appears in two
panels -- this is a left join onto the hits, never a filter.

Run:  mamba run -n p312 python -m identify.hits_table          (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

OUT_NAME = "clone_response_storey_hits_identified.csv"

# Identification columns appended to each hit row, as (source column, new name).
ID_COLS = [
    ("best_level", "id_level"),
    ("best_candidate", "id_candidate"),
    ("formula", "id_formula"),
    ("lipid_class", "id_class"),
    ("evidence_source", "id_evidence"),
    ("ppm_error", "id_ppm_error"),
    ("ms2_cosine", "id_ms2_cosine"),
    ("n_candidates", "id_n_candidates"),
    ("acyl_chains_observed", "acyl_chains_from_msms"),
    ("repository_occurrence", "seen_in_public_data"),
    ("adduct", "adduct"),
    ("ccs", "ccs"),
    ("has_msms", "has_msms"),
    ("was_already_named", "named_by_facility"),
]
# Measurement context that lives on the manifest rather than the best-call table.
MANIFEST_COLS = [("neutral_mass", "neutral_mass"), ("polarity", "polarity")]


def _class_consensus() -> pd.DataFrame:
    """What class do a feature's candidates agree on, and how strongly.

    Within L3 the rank-1 candidate is close to arbitrary: dozens of compounds
    share a formula and therefore share a ppm error, so whichever the sort
    happens to put first can be a drug or a vitamin rather than a lipid. The
    class the candidates AGREE on is the part that carries information, so it is
    reported alongside, with the fraction agreeing so the reader can see how
    thin the agreement is.
    """
    cands = pd.read_csv(
        common.PUBLISH_DIR / "clone_response_identification_candidates.csv"
    )
    ident = cands[cands.confidence_level.isin(["L2", "L3"])].copy()
    ident["klass"] = ident.sub_class.fillna(ident.lipid_class)
    ident = ident[ident.klass.notna()]

    rows = []
    for fid, grp in ident.groupby("feature_id"):
        counts = grp.klass.value_counts()
        rows.append({
            "feature_id": fid,
            "id_class_consensus": counts.index[0],
            "id_class_agreement": round(counts.iloc[0] / len(grp), 3),
            "id_n_distinct_classes": int(counts.size),
        })
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    hits = pd.read_csv(common.HITS_CSV)
    best = pd.read_csv(common.PUBLISH_DIR / "clone_response_best_call_per_feature.csv")

    missing = set(hits.feature_id) - set(best.feature_id)
    if missing:
        raise KeyError(f"hits with no identification row: {sorted(missing)}")

    ident = best[["feature_id", *[c for c, _ in ID_COLS]]].rename(
        columns=dict(ID_COLS)
    )
    manifest = pd.read_csv(common.IDENT_DIR / "hit_manifest.csv")
    ident = ident.merge(
        manifest[["feature_id", *[c for c, _ in MANIFEST_COLS]]].rename(
            columns=dict(MANIFEST_COLS)
        ),
        on="feature_id", how="left", validate="one_to_one",
    )
    cons = _class_consensus()
    if len(cons):
        ident = ident.merge(cons, on="feature_id", how="left", validate="one_to_one")
    out = hits.merge(ident, on="feature_id", how="left", validate="many_to_one")

    if len(out) != len(hits):
        raise AssertionError(f"join changed row count: {len(hits)} -> {len(out)}")

    # The source table's `lipid_name` is MetaboScape's `RT_mz` placeholder for
    # everything it never named. Keep it (it is what the statistics were run
    # against) but say plainly which rows it is a placeholder on.
    out["lipid_name_is_placeholder"] = ~out["named_by_facility"].astype(bool)
    # Say it in the table, not just the readme: below L2 the named candidate is
    # one of many sharing the same composition, and is not a unique call.
    out["id_candidate_is_unique"] = out.id_level.eq("L2") & out.id_n_candidates.eq(1)

    dest = common.HITS_CSV.parent / OUT_NAME
    out.to_csv(dest, index=False)

    _report(out, dest)
    return out


def _report(out: pd.DataFrame, dest: Path) -> None:
    print(f"wrote {dest}")
    print(f"  rows                 {len(out)}  (unique features {out.feature_id.nunique()})")
    print(f"  columns              {len(out.columns)}")
    print("\n  hit rows by identification level:")
    for lvl, n in out.id_level.value_counts().items():
        print(f"    {lvl:<6} {n:3d}")
    named = int(out.named_by_facility.astype(bool).sum())
    acyl = int(out.acyl_chains_from_msms.notna().sum())
    print(f"\n  rows already named by the facility   {named}/{len(out)}")
    print(f"  rows with acyl chains from MS/MS     {acyl}/{len(out)}")
    print("\n  the L2/L3 calls, by class consensus (the informative part --")
    print("  the named candidate below L2 is one of many sharing the composition):")
    show = (out[out.id_level.isin(["L2", "L3"])]
            .drop_duplicates("feature_id")
            .sort_values(["id_level", "feature_id"]))
    for _, r in show.iterrows():
        chains = f"  chains {r.acyl_chains_from_msms}" if pd.notna(r.acyl_chains_from_msms) else ""
        agree = "  --" if pd.isna(r.id_class_agreement) else f"{r.id_class_agreement:.0%}"
        klass = "(no class on any candidate)" if pd.isna(r.id_class_consensus) \
            else str(r.id_class_consensus)[:34]
        print(f"    {r.feature_id}  {r.id_level}  {klass:<34} {agree:>4} of "
              f"{int(r.id_n_candidates):3d} cand.{chains}")


if __name__ == "__main__":
    run()

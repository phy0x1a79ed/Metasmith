"""T4 -- merge the evidence streams, grade them, publish.

Confidence follows the Schymanski/MSI scale and is assigned by ONE rule applied
uniformly, so the grade is auditable rather than a per-feature judgement call:

  L2  a spectral library match at or above the search cosine threshold; or the
      facility's own MS/MS library hit, but only for candidates whose class
      agrees with what that hit called -- a probable structure.
  L3  a curated database holds a compound with this mass or formula, but isomers
      (or competing formulas) are unresolved -- a tentative candidate.
  L4  the molecular formula is unequivocal -- exactly one plausible formula --
      but no database compound carries it.
  L5  exact mass only: several formulas fit and none is supported.
  occurrence
      the same spectrum appears in public repository data but is unnamed there.
      This is NOT an identification and is never counted as one; it is kept
      because it says the molecule is real and seen elsewhere.

Run:  mamba run -n p312 python -m identify.grade              (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

COSINE_MIN = 0.6
FACILITY_MSMS_MIN = 700.0

STREAMS = [
    "candidates_refmet_mass.csv",
    "candidates_web_formula.csv",
    "candidates_spectral.csv",
]
DB_SOURCES = {"refmet_mass", "lipidmaps_formula", "refmet_formula", "massbank_reference"}
NAMED_SPECTRAL = {"fasst_gnpslibrary"}
OCCURRENCE = {"fasst_repository"}
# GNPS "suspect" entries are annotations propagated across an explicit mass
# shift. They describe a *related* compound, so they are not evidence for this
# one at any level, and they get their own label rather than a number.
ANALOG = {"fasst_gnps_analog"}

LEVEL_ORDER = {
    "L2": 0, "L3": 1, "L4": 2, "L5": 3, "analog": 4, "occurrence": 5, "none": 6,
}

# LIPID MAPS spells classes out where the facility uses shorthand; the control
# check has to see through that.
CLASS_SYNONYM = {
    "PS": "phosphoserine",
    "PG": "phosphoglycerol",
    "PE": "phosphoethanolamine",
    "PC": "phosphocholine",
    "HBMP": "phosphoglycerol",
}


def _load_streams() -> pd.DataFrame:
    frames = []
    for name in STREAMS:
        p = common.IDENT_DIR / name
        if p.exists():
            df = pd.read_csv(p)
            if len(df):
                frames.append(df)
        else:
            print(f"  note: {name} absent -- that stream contributed nothing")
    if not frames:
        return pd.DataFrame(columns=common.CANDIDATE_COLS)
    return pd.concat(frames, ignore_index=True)


def _unambiguous_formula(manifest: pd.DataFrame) -> dict[str, bool]:
    """Whether a feature's molecular formula is pinned down.

    True when the facility assigned one, or when exactly one plausible formula
    survived enumeration and a database supports it.
    """
    support = {}
    p = common.IDENT_DIR / "formula_support_summary.csv"
    if p.exists():
        s = pd.read_csv(p).set_index("feature_id")
        for fid, row in s.iterrows():
            support[fid] = int(row.formulas_tried) == 1 or int(row.formulas_supported) == 1
    out = {}
    for _, f in manifest.iterrows():
        has_facility = isinstance(f.formula, str) and bool(str(f.formula).strip())
        out[f.feature_id] = bool(has_facility or support.get(f.feature_id, False))
    return out


def facility_class_token(name: object) -> str | None:
    """The lipid-class prefix of a facility name: 'HBMP14:0_16:1_16:0' -> 'HBMP'.

    Returns None for the `RT_mz` placeholders, which begin with a digit.
    """
    if not isinstance(name, str) or not name or name[0].isdigit():
        return None
    token = ""
    for ch in name:
        if ch.isalpha() or (ch == "-" and token):
            token += ch
        else:
            break
    return token or None


def assign_level(row: pd.Series, manifest_row: pd.Series, unambiguous: bool) -> str:
    src = row.evidence_source
    if src in OCCURRENCE:
        return "occurrence"
    if src in ANALOG:
        return "analog"
    if src in NAMED_SPECTRAL and pd.notna(row.ms2_cosine) and float(row.ms2_cosine) >= COSINE_MIN:
        return "L2"
    if src in DB_SOURCES:
        # The facility's own library match puts a real spectrum behind the
        # feature -- but it supports only the candidates that AGREE with what it
        # called. Letting it lift every isomer would stamp L2 on candidates the
        # spectrum actively contradicts (an Ox-PC beside a PS, say).
        token = facility_class_token(manifest_row["name"])
        if (
            token
            and pd.notna(manifest_row.msms_score)
            and float(manifest_row.msms_score) >= FACILITY_MSMS_MIN
        ):
            fields = " ".join(
                str(row[c]) for c in ("candidate_name", "sub_class", "lipid_class")
                if pd.notna(row[c])
            ).lower()
            if token.lower() in fields:
                return "L2"
        return "L3"
    return "L4" if unambiguous else "L5"


def run() -> pd.DataFrame:
    common.ensure_dirs()
    manifest = pd.read_csv(common.IDENT_DIR / "hit_manifest.csv")
    mindex = manifest.set_index("feature_id")
    cands = _load_streams()
    unamb = _unambiguous_formula(manifest)

    rows = []
    for _, c in cands.iterrows():
        m = mindex.loc[c.feature_id]
        level = assign_level(c, m, unamb.get(c.feature_id, False))
        rows.append({**c.to_dict(), "confidence_level": level})

    graded = pd.DataFrame(rows) if rows else pd.DataFrame(columns=[*common.CANDIDATE_COLS, "confidence_level"])

    # Features that no stream reached still appear, explicitly -- absence has to
    # be visible in the table, not inferred from a missing row.
    seen = set(graded.feature_id) if len(graded) else set()
    empties = [
        {**common.candidate_row(fid, "none", notes="no candidate from any source"),
         "confidence_level": "none"}
        for fid in manifest.feature_id if fid not in seen
    ]
    if empties:
        graded = pd.concat([graded, pd.DataFrame(empties)], ignore_index=True)

    graded = graded.drop_duplicates(
        subset=["feature_id", "evidence_source", "candidate_name"], keep="first"
    )
    graded["_lvl"] = graded.confidence_level.map(LEVEL_ORDER)
    graded["_ppm"] = graded.ppm_error.abs().fillna(999)
    graded["_cos"] = -graded.ms2_cosine.fillna(0)
    graded = graded.sort_values(["feature_id", "_lvl", "_cos", "_ppm"])
    graded["rank"] = graded.groupby("feature_id").cumcount() + 1

    # Attach the measurement context so the table stands alone.
    ctx = mindex[["mz", "rt", "ccs", "adduct", "neutral_mass", "polarity",
                  "has_msms", "panels"]]
    graded = graded.join(ctx, on="feature_id")

    cols = [
        "feature_id", "rank", "confidence_level", "evidence_source",
        "candidate_name", "formula", "lipid_class", "super_class", "main_class",
        "sub_class", "exactmass", "ppm_error", "ms2_cosine", "ms2_matched_peaks",
        "mz", "rt", "ccs", "adduct", "neutral_mass", "polarity", "has_msms",
        "external_ids", "notes", "panels",
    ]
    graded = graded[cols]

    common.PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    graded.to_csv(
        common.PUBLISH_DIR / "clone_response_identification_candidates.csv", index=False
    )
    graded.to_csv(common.IDENT_DIR / "graded_candidates.csv", index=False)

    best = _feature_summary(graded, manifest)
    best.to_csv(common.PUBLISH_DIR / "clone_response_best_call_per_feature.csv", index=False)
    _report(graded, best)
    return graded


def _acyl_chains() -> dict[str, str]:
    """Per-feature acyl chains read off the negative-mode MS/MS, if available.

    Carried alongside the grade rather than folded into it: a carboxylate anion
    identifies a chain, not the molecule that shed it.
    """
    p = common.IDENT_DIR / "acyl_fragments.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    if df.empty:
        return {}
    out = {}
    for fid, grp in df.groupby("feature_id"):
        grp = grp.sort_values("intensity", ascending=False)
        out[fid] = ", ".join(
            f"{r.chain}{'*' if r.cyclo_ambiguous else ''}" for _, r in grp.iterrows()
        )
    return out


def _feature_summary(graded: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    ident = graded[graded.confidence_level.isin(["L2", "L3", "L4", "L5"])]
    acyl = _acyl_chains()
    rows = []
    for fid in manifest.feature_id:
        sub = ident[ident.feature_id == fid]
        occ = graded[(graded.feature_id == fid) & (graded.confidence_level == "occurrence")]
        m = manifest[manifest.feature_id == fid].iloc[0]
        if len(sub):
            top = sub.sort_values("rank").iloc[0]
            klass = top.sub_class if pd.notna(top.sub_class) else top.lipid_class
            rows.append({
                "feature_id": fid, "best_level": top.confidence_level,
                "best_candidate": top.candidate_name, "formula": top.formula,
                "lipid_class": None if pd.isna(klass) else klass,
                "evidence_source": top.evidence_source,
                "n_candidates": len(sub), "ppm_error": top.ppm_error,
                "ms2_cosine": top.ms2_cosine, "repository_occurrence": len(occ) > 0,
                "acyl_chains_observed": acyl.get(fid),
                "mz": m.mz, "rt": m.rt, "ccs": m.ccs, "adduct": m.adduct,
                "has_msms": m.has_msms, "was_already_named": not m.is_placeholder,
                "is_control": m.is_control,
            })
        else:
            rows.append({
                "feature_id": fid, "best_level": "none", "best_candidate": None,
                "formula": None, "lipid_class": None, "evidence_source": None,
                "n_candidates": 0, "ppm_error": None, "ms2_cosine": None,
                "repository_occurrence": len(occ) > 0,
                "acyl_chains_observed": acyl.get(fid),
                "mz": m.mz, "rt": m.rt, "ccs": m.ccs, "adduct": m.adduct,
                "has_msms": m.has_msms, "was_already_named": not m.is_placeholder,
                "is_control": m.is_control,
            })
    return pd.DataFrame(rows)


def _report(graded: pd.DataFrame, best: pd.DataFrame) -> None:
    print("\nGraded candidate table")
    print(f"  candidate rows        {len(graded)}")
    print(f"  features covered      {graded.feature_id.nunique()}")
    print("\n  best level per feature:")
    for lvl in ("L2", "L3", "L4", "L5", "none"):
        n = (best.best_level == lvl).sum()
        print(f"    {lvl:<5} {n:3d}")
    dark = best[(best.best_level == "none")]
    print(f"\n  features with no candidate at all: {len(dark)}"
          + (f" ({', '.join(dark.feature_id)})" if len(dark) else ""))
    print(f"  features with repository occurrence: {int(best.repository_occurrence.sum())}")

    print("\n  CONTROLS (must recover their known identity):")
    for _, r in best[best.is_control].iterrows():
        truth = common.CONTROL_FEATURES[r.feature_id]
        # The class token may show up in the candidate name ("PS 34:3") or in a
        # spelled-out class ("Diacylglycerophosphoserines"), so both are checked
        # against the token and its expansion rather than the token alone.
        want = {truth["class"].lower(), CLASS_SYNONYM.get(truth["class"], "").lower()} - {""}
        blob = f"{r.best_candidate} {r.lipid_class}".lower()
        ok = any(w in blob for w in want)
        print(f"    {r.feature_id}  expect {truth['class']:<5} -> got "
              f"{str(r.best_candidate)[:22]:<22} / {str(r.lipid_class)[:34]:<34} "
              f"level {r.best_level}  {'PASS' if ok else 'CHECK'}")


if __name__ == "__main__":
    run()

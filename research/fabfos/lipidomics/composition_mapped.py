"""Composition + annotation-confidence on the REAL (RefMet/Goslin) lipid mapping.

Reads features_mapped.csv (lipid_map.py output) instead of the regex lipid_class.
Produces, under processed/metaboscape/:
  - composition_class_mapped.csv       % abundance per (condition) x final_class
  - composition_saturation_mapped.csv  abundance per (class, total_db)
  - composition_chainlen_mapped.csv    abundance per (class, total_carbon)
  - annotation_tiers.csv               per-feature confidence tier + the PC check
  - redox_carriers.csv                 redox-carrier abundance per condition

Annotation tiers (from MetaboScape `annotations` provenance + msms_score):
  T1 spectral  = a real MS/MS spectral-library hit (NIST / MetaBASE / MSMS-Public/
                 LipidBlast) AND msms_score >= 700
  T2 library   = spectral library tag but weak score, or in-silico "Lipid Species"
  T3 name-only = only "Target List - HMDB" / mass match, no MS/MS support

Env: p312. Run from the project dir: mamba run -n p312 python research/fabfos/lipidomics/composition_mapped.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipidio import median_normalize  # noqa: E402

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
FEAT = M / "features_mapped.csv"
META = M / "metadata_bio.csv"
SAMPLE_RE = r"^(Epi300|EpCC1|ESi300|ESCC1|Clone1|Clone2)_(ctrl|tol)_(P|S)_\d$"


def annotation_tier(row) -> str:
    ann = str(row.get("annotations", "") or "")
    score = row.get("msms_score", np.nan)
    score = float(score) if pd.notna(score) else 0.0
    spectral = any(k in ann for k in
                   ("Spectral Library", "NIST", "MetaboBASE", "MSMS-Public",
                    "LipidBlast", "experimentspectra"))
    if spectral and score >= 700:
        return "T1_spectral"
    if spectral or "Lipid Species" in ann:
        return "T2_library"
    return "T3_name_only"


def main():
    df = pd.read_csv(FEAT)
    bio = pd.read_csv(META)
    sample_cols = [c for c in df.columns if pd.Series([c]).str.match(SAMPLE_RE)[0]]
    print(f"[comp] {len(df)} features, {len(sample_cols)} sample cols")

    # --- annotation tiers + PC check ---------------------------------------
    df["tier"] = df.apply(annotation_tier, axis=1)
    df[["feature_id", "name", "final_class", "super_class", "msms_score",
        "annotations", "tier"]].to_csv(M / "annotation_tiers.csv", index=False)
    print("\n[tiers] all features:")
    print(df["tier"].value_counts().to_string())
    mapped = df[df["map_source"] != "unmapped"]
    print("\n[tiers] mapped-lipid features only:")
    print(mapped["tier"].value_counts().to_string())

    # abundance-weighted: total signal per class, and the PC question
    norm = median_normalize(df[sample_cols].fillna(0.0))
    df["tot_abund"] = norm.sum(axis=1).values
    print("\n[abund] class share of total ANNOTATED-lipid abundance:")
    cls = (df[df["final_class"].notna()]
           .groupby("final_class")["tot_abund"].sum().sort_values(ascending=False))
    share = 100 * cls / cls.sum()
    print(share.head(15).round(1).to_string())
    print("\n[PC check] PC abundance by annotation tier:")
    pc = df[df["final_class"] == "PC"]
    print(pc.groupby("tier")["tot_abund"].agg(["count", "sum"]).to_string())
    print("[PC check] PC features:")
    print(pc[["name", "tier", "msms_score", "tot_abund"]].to_string())

    # --- per-condition class composition -----------------------------------
    lognorm = norm
    rows = []
    for _, m in bio.iterrows():
        col = f"{m['strain']}_{m['treatment']}_{m['fraction']}_{m['replicate']}"
        if col not in lognorm.columns:
            continue
        sub = df[df["final_class"].notna()]
        for cl, g in sub.groupby("final_class"):
            rows.append(dict(strain=m["strain"], treatment=m["treatment"],
                             fraction=m["fraction"], replicate=m["replicate"],
                             final_class=cl, abund=lognorm.loc[g.index, col].sum()))
    comp = pd.DataFrame(rows)
    cond = comp.groupby(["strain", "treatment", "fraction", "final_class"])["abund"].mean().reset_index()
    cond.to_csv(M / "composition_class_mapped.csv", index=False)

    # saturation + chainlen on mapped C/DB
    sat = (df[df["final_class"].notna() & df["map_total_db"].notna()]
           .groupby(["final_class", "map_total_db"])["tot_abund"].sum().reset_index())
    sat.to_csv(M / "composition_saturation_mapped.csv", index=False)
    cl = (df[df["final_class"].notna() & df["map_total_c"].notna()]
          .groupby(["final_class", "map_total_c"])["tot_abund"].sum().reset_index())
    cl.to_csv(M / "composition_chainlen_mapped.csv", index=False)

    # --- redox carriers per condition --------------------------------------
    redox = df[(df["super_class"] == "Prenol Lipids")
               | df["name"].astype(str).str.contains(
                   "ubiquinol|ubiquinone|menaquinone|tocopher|coenzyme q",
                   case=False)]
    rr = []
    for _, m in bio.iterrows():
        col = f"{m['strain']}_{m['treatment']}_{m['fraction']}_{m['replicate']}"
        if col not in lognorm.columns:
            continue
        rr.append(dict(strain=m["strain"], treatment=m["treatment"],
                       fraction=m["fraction"], replicate=m["replicate"],
                       redox_abund=lognorm.loc[redox.index, col].sum()))
    rdf = pd.DataFrame(rr)
    rdf.groupby(["strain", "treatment", "fraction"])["redox_abund"].mean().reset_index().to_csv(
        M / "redox_carriers.csv", index=False)
    print("\n[redox] mean redox-carrier abundance per condition:")
    print(rdf.groupby(["fraction", "strain", "treatment"])["redox_abund"].mean().round(0).to_string())
    print(f"\n[comp] wrote composition_*_mapped.csv, annotation_tiers.csv, redox_carriers.csv -> {M}")


if __name__ == "__main__":
    main()

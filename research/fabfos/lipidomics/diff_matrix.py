"""Within-fraction strain pairs + pellet-vs-supernatant — completes the full matrix.

Two contrast families, each contrast its own BH-FDR family:
  1. STRAIN PAIRS  — every pair of strains within each (fraction, treatment) cell.
  2. P_VS_S        — pellet vs supernatant for strains present in both fractions
     (Clone1, Clone2), per treatment. P and S are different matrices; this is an
     explicit cross-matrix contrast, interpreted with that caveat.

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/diff_matrix.py metaboscape
"""
from __future__ import annotations
import sys
from itertools import combinations

import pandas as pd

from lipidio import (
    load_bio, median_normalize, log2, contrast, volcano, resolve_source,
)

STRAIN_PAIRS_FAMILY = "diff_strainpairs"
P_VS_S_FAMILY = "diff_pvss"
SHARED_STRAINS = ["Clone1", "Clone2"]  # present in both fractions


def run(arg: str) -> None:
    source, polarity, out_base, tag = resolve_source(arg)
    feats, abund, bio = load_bio(source=source, polarity=polarity)
    lg = log2(median_normalize(abund))

    # 1) STRAIN PAIRS within (fraction, treatment) -------------------------------
    sp_dir = out_base / STRAIN_PAIRS_FAMILY / tag
    sp_dir.mkdir(parents=True, exist_ok=True)
    sp_rows = []
    for (fraction, treatment), cell in bio.groupby(["fraction", "treatment"]):
        strains = sorted(cell.strain.unique())
        for s1, s2 in combinations(strains, 2):
            a = cell[cell.strain == s1].index.tolist()
            b = cell[cell.strain == s2].index.tolist()
            if len(a) < 2 or len(b) < 2:
                continue
            df = contrast(feats, abund, lg, a, b, fc_col="log2fc_a_vs_b")
            df.insert(1, "fraction", fraction)
            df.insert(2, "treatment", treatment)
            df.insert(3, "strain_a", s1)
            df.insert(4, "strain_b", s2)
            sp_rows.append(df)
            volcano(df, "log2fc_a_vs_b", f"{tag} {s1}/{s2} {fraction} {treatment}",
                    sp_dir / f"volcano_{s1}_vs_{s2}_{fraction}_{treatment}.png")

    # 2) P vs S for shared strains -----------------------------------------------
    ps_dir = out_base / P_VS_S_FAMILY / tag
    ps_dir.mkdir(parents=True, exist_ok=True)
    ps_rows = []
    for strain in SHARED_STRAINS:
        for treatment in ("ctrl", "tol"):
            p = bio[(bio.strain == strain) & (bio.fraction == "P") & (bio.treatment == treatment)].index.tolist()
            s = bio[(bio.strain == strain) & (bio.fraction == "S") & (bio.treatment == treatment)].index.tolist()
            if len(p) < 2 or len(s) < 2:
                continue
            df = contrast(feats, abund, lg, p, s, fc_col="log2fc_P_vs_S")
            df.insert(1, "strain", strain)
            df.insert(2, "treatment", treatment)
            ps_rows.append(df)
            volcano(df, "log2fc_P_vs_S", f"{tag} {strain} P/S {treatment}",
                    ps_dir / f"volcano_{strain}_P_vs_S_{treatment}.png")

    if sp_rows:
        sp = pd.concat(sp_rows, ignore_index=True)
        sp["contrast_family"] = STRAIN_PAIRS_FAMILY
        csv = out_base / f"{STRAIN_PAIRS_FAMILY}_{tag}.csv"
        sp.to_csv(csv, index=False)
        n_sig = ((sp.qvalue < 0.05) & (sp.log2fc_a_vs_b.abs() > 1)).sum()
        print(f"wrote {csv} ({len(sp)} rows, "
              f"{sp[['fraction','treatment','strain_a','strain_b']].drop_duplicates().shape[0]} pair-cells, "
              f"{n_sig} sig)")
    if ps_rows:
        ps = pd.concat(ps_rows, ignore_index=True)
        ps["contrast_family"] = P_VS_S_FAMILY
        csv = out_base / f"{P_VS_S_FAMILY}_{tag}.csv"
        ps.to_csv(csv, index=False)
        n_sig = ((ps.qvalue < 0.05) & (ps.log2fc_P_vs_S.abs() > 1)).sum()
        print(f"wrote {csv} ({len(ps)} rows, {n_sig} sig)")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "metaboscape")

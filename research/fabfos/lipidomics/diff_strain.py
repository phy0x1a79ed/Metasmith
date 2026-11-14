"""Differential abundance — engineered strain vs i300 parent, per (treatment, fraction).

Comparisons (within each treatment x fraction):
  - EpCC1, Clone1, Clone2 (pellet P) vs Epi300 (P)
  - ESCC1, Clone1, Clone2 (supernatant S) vs ESi300 (S)

The Epi300 line was acquired only as pellet; ESi300 only as supernatant, so the
parent reference is chosen per fraction. Welch + BH per contrast (one FDR family
each).

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/diff_strain.py metaboscape
"""
from __future__ import annotations
import sys

import pandas as pd

from lipidio import (
    load_bio, median_normalize, log2, contrast, volcano, resolve_source,
)

FAMILY = "diff_strain"
PARENT_BY_FRACTION = {"P": "Epi300", "S": "ESi300"}
ENGINEERED = {"P": ["EpCC1", "Clone1", "Clone2"], "S": ["ESCC1", "Clone1", "Clone2"]}


def run(arg: str) -> None:
    source, polarity, out_base, tag = resolve_source(arg)
    feats, abund, bio = load_bio(source=source, polarity=polarity)
    lg = log2(median_normalize(abund))

    out_dir = out_base / FAMILY / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for fraction, parent in PARENT_BY_FRACTION.items():
        for treatment in ("ctrl", "tol"):
            par = bio[(bio.strain == parent) & (bio.fraction == fraction) & (bio.treatment == treatment)].index.tolist()
            if len(par) < 2:
                continue
            for strain in ENGINEERED[fraction]:
                eng = bio[(bio.strain == strain) & (bio.fraction == fraction) & (bio.treatment == treatment)].index.tolist()
                if len(eng) < 2:
                    continue
                df = contrast(feats, abund, lg, eng, par, fc_col="log2fc_strain_vs_parent")
                df.insert(1, "strain", strain)
                df.insert(2, "parent", parent)
                df.insert(3, "treatment", treatment)
                df.insert(4, "fraction", fraction)
                rows.append(df)
                volcano(df, "log2fc_strain_vs_parent",
                        f"{tag} {strain}/{parent} {fraction} {treatment}",
                        out_dir / f"volcano_{strain}_vs_{parent}_{fraction}_{treatment}.png")

    if not rows:
        print("no eligible comparisons", file=sys.stderr)
        return
    full = pd.concat(rows, ignore_index=True)
    full["contrast_family"] = FAMILY
    csv = out_base / f"{FAMILY}_{tag}.csv"
    full.to_csv(csv, index=False)
    n_sig = ((full.qvalue < 0.05) & (full.log2fc_strain_vs_parent.abs() > 1)).sum()
    print(f"wrote {csv} ({len(full)} rows, {n_sig} sig q<0.05&|lfc|>1)")
    print(f"volcano plots -> {out_dir}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "metaboscape")

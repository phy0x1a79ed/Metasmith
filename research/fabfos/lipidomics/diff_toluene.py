"""Differential abundance — ±toluene, per (strain, fraction).

For each (strain, fraction) cell with >=2 samples in both tol and ctrl, runs
Welch's t-test, BH-corrects across the feature set (per cell = one FDR family),
and exports a long-form CSV + per-cell volcano plots.

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/diff_toluene.py metaboscape
     (or `pos`/`neg` for the MS-DIAL source)
"""
from __future__ import annotations
import sys

from lipidio import (
    load_bio, median_normalize, log2, contrast, volcano, resolve_source,
)
import pandas as pd

FAMILY = "diff_toluene"


def run(arg: str) -> None:
    source, polarity, out_base, tag = resolve_source(arg)
    feats, abund, bio = load_bio(source=source, polarity=polarity)
    lg = log2(median_normalize(abund))

    out_dir = out_base / FAMILY / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for (strain, fraction), cell in bio.groupby(["strain", "fraction"]):
        tol = cell[cell.treatment == "tol"].index.tolist()
        ctl = cell[cell.treatment == "ctrl"].index.tolist()
        if len(tol) < 2 or len(ctl) < 2:
            continue
        df = contrast(feats, abund, lg, tol, ctl, fc_col="log2fc_tol_vs_ctrl")
        df.insert(1, "strain", strain)
        df.insert(2, "fraction", fraction)
        rows.append(df)
        volcano(df, "log2fc_tol_vs_ctrl",
                f"{tag} {strain} {fraction} tol/ctrl (n={len(tol)}v{len(ctl)})",
                out_dir / f"volcano_{strain}_{fraction}.png")

    if not rows:
        print("no cells with sufficient replicates", file=sys.stderr)
        return
    full = pd.concat(rows, ignore_index=True)
    full["contrast_family"] = FAMILY
    csv = out_base / f"{FAMILY}_{tag}.csv"
    full.to_csv(csv, index=False)
    n_sig = ((full.qvalue < 0.05) & (full.log2fc_tol_vs_ctrl.abs() > 1)).sum()
    print(f"wrote {csv} ({len(full)} rows, {full[['strain','fraction']].drop_duplicates().shape[0]} cells, "
          f"{n_sig} sig q<0.05&|lfc|>1)")
    print(f"volcano plots -> {out_dir}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "metaboscape")

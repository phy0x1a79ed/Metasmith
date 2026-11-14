"""Table of the significant (red/blue) hits shown in clone_response_storey.png —
same 8 panels (2 clones x 4 comparisons), same Storey-FDR contrast_median call,
filtered to q<0.05 & |log2FC|>1.

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/od_clone_response_table.py
Writes: .awm/data/figures/publish/04_lipidomics/05_clone_response/clone_response_storey_hits.csv
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

from lipidio import load_bio, od_normalize, log2
from od_strain_volcano import cols_for, contrast_median, final_class

PUB = Path(".awm/data/figures/publish/04_lipidomics/05_clone_response")
CLONES = ["Clone1", "Clone2"]
CTRL_STRAIN_BY_FRACTION = {"P": "EpCC1", "S": "ESCC1"}
FRACTION_TITLE = {"P": "pellet", "S": "supernatant"}
PRIMARY_OD = "group_geomean"


def main():
    feats, abund_raw, bio = load_bio(source="metaboscape", polarity="merged")
    fclass = final_class(feats)

    abund_od = od_normalize(abund_raw, PRIMARY_OD)
    bio_od = bio.loc[abund_od.columns]
    lg_od = log2(abund_od)

    columns = []
    for fraction in ("P", "S"):
        ctrl_strain = CTRL_STRAIN_BY_FRACTION[fraction]
        columns.append((
            fraction, "Clone vs PCC1 (-Tol.)",
            lambda clone, fraction=fraction, ctrl_strain=ctrl_strain: (
                cols_for(bio_od, clone, fraction, "ctrl"),
                cols_for(bio_od, ctrl_strain, fraction, "ctrl")),
        ))
        columns.append((
            fraction, "+Tol. vs -Tol",
            lambda clone, fraction=fraction: (
                cols_for(bio_od, clone, fraction, "tol"),
                cols_for(bio_od, clone, fraction, "ctrl")),
        ))

    rows = []
    for clone in CLONES:
        for fraction, comparison, idx_fn in columns:
            a_idx, b_idx = idx_fn(clone)
            if len(a_idx) < 2 or len(b_idx) < 2:
                continue
            df = contrast_median(feats, abund_od, lg_od, a_idx, b_idx,
                                  fc_col="log2fc", fdr="storey")
            df["final_class"] = fclass.reindex(df["feature_id"]).values
            sig = (df.qvalue < 0.05) & (df["log2fc"].abs() > 1)
            hit = df[sig].copy()
            if hit.empty:
                continue
            hit.insert(0, "clone", clone)
            hit.insert(1, "fraction", FRACTION_TITLE[fraction])
            hit.insert(2, "comparison", comparison)
            hit["direction"] = hit["log2fc"].gt(0).map({True: "+", False: "-"})
            rows.append(hit)

    if not rows:
        print("no significant hits")
        return

    out = pd.concat(rows, ignore_index=True)
    out["neg_log10_q"] = -np.log10(out["qvalue"])
    out = out.drop(columns=["present_absent", "qvalue"])
    out = out.sort_values(["clone", "fraction", "comparison", "direction", "neg_log10_q"],
                          ascending=[True, True, True, True, False])
    csv = PUB / "clone_response_storey_hits.csv"
    out.to_csv(csv, index=False)
    print(f"wrote {csv} ({len(out)} hits: {(out.direction == '+').sum()} +, "
          f"{(out.direction == '-').sum()} -)")


if __name__ == "__main__":
    main()

"""S7: Membrane composition profile (lipid-annotated subset only).

Aggregates annotated lipid abundance by:
  1. lipid_class           → stacked-bar (% composition) per condition.
  2. (class, total_db)     → saturation heatmap.
  3. (class, total_carbon) → chain-length profile.

NOTE: only the ~87 features with a parseable lipid shorthand carry class/chain
metadata, out of ~2180 cleaned features — these figures are a class profile of
the annotated subset, not of the whole table.

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/composition.py metaboscape
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from lipidio import load_bio, median_normalize, parse_shorthand, resolve_source

FIGURES = Path(__file__).resolve().parents[3] / "data/fabfos/runs/scadc_lipidomics_figures"


def run(arg: str) -> None:
    source, polarity, out_base, tag = resolve_source(arg)
    feats, abund, bio = load_bio(source=source, polarity=polarity)

    norm = median_normalize(abund)

    # lipid_class may already be present (metaboscape loader); else parse it.
    if "lipid_class" in feats.columns:
        feats_p = feats.copy()
    else:
        parsed = feats["lipid_name"].apply(parse_shorthand).apply(pd.Series) if "lipid_name" in feats.columns else pd.DataFrame()
        feats_p = pd.concat([feats, parsed], axis=1)
    annotated = feats_p[feats_p.lipid_class.notna()]

    if annotated.empty:
        print("no annotated features — check that lipid annotation ran successfully", file=sys.stderr)
        return

    FIGURES.mkdir(parents=True, exist_ok=True)
    PROCESSED = out_base  # write tables next to the source's other outputs
    polarity = tag        # filename suffix

    abund_ann = norm.loc[annotated.index]
    bio_ann = bio.copy()
    bio_ann["condition"] = bio_ann[["strain", "treatment", "fraction"]].agg("_".join, axis=1)

    # 1) Class composition (% of total annotated abundance) per condition
    by_class = abund_ann.groupby(annotated.lipid_class.values).sum()
    by_class_pct = by_class.divide(by_class.sum(axis=0), axis=1) * 100
    class_cond = by_class_pct.T.join(bio_ann["condition"]).groupby("condition").mean()
    class_cond.plot(kind="bar", stacked=True, figsize=(10, 6), colormap="tab20")
    plt.ylabel("% of annotated lipid abundance")
    plt.title(f"{polarity.upper()} — class composition by condition")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES / f"class_composition_{polarity}.png", dpi=150)
    plt.savefig(FIGURES / f"class_composition_{polarity}.pdf")
    plt.close()

    # 2) Saturation heatmap: (class × total_db), averaged over samples per condition.
    df_sat = annotated.assign(abund=abund_ann.mean(axis=1)).groupby(
        ["lipid_class", "total_db"]
    )["abund"].sum().unstack(fill_value=0)
    plt.figure(figsize=(8, max(4, 0.3 * len(df_sat))))
    sns.heatmap(np.log10(df_sat + 1), cmap="viridis", cbar_kws={"label": "log10(abundance)"})
    plt.xlabel("# double bonds")
    plt.ylabel("lipid class")
    plt.title(f"{polarity.upper()} — saturation profile")
    plt.tight_layout()
    plt.savefig(FIGURES / f"saturation_{polarity}.png", dpi=150)
    plt.savefig(FIGURES / f"saturation_{polarity}.pdf")
    plt.close()

    # 3) Chain-length profile: (class × total_carbon)
    df_cl = annotated.assign(abund=abund_ann.mean(axis=1)).groupby(
        ["lipid_class", "total_carbon"]
    )["abund"].sum().unstack(fill_value=0)
    plt.figure(figsize=(10, max(4, 0.3 * len(df_cl))))
    sns.heatmap(np.log10(df_cl + 1), cmap="viridis", cbar_kws={"label": "log10(abundance)"})
    plt.xlabel("total acyl carbons")
    plt.ylabel("lipid class")
    plt.title(f"{polarity.upper()} — chain-length profile")
    plt.tight_layout()
    plt.savefig(FIGURES / f"chain_length_{polarity}.png", dpi=150)
    plt.savefig(FIGURES / f"chain_length_{polarity}.pdf")
    plt.close()

    # Also save the aggregated tables
    class_cond.to_csv(PROCESSED / f"composition_class_{polarity}.csv")
    df_sat.to_csv(PROCESSED / f"composition_saturation_{polarity}.csv")
    df_cl.to_csv(PROCESSED / f"composition_chainlen_{polarity}.csv")
    print(f"wrote 3 composition CSVs + 3 figures for polarity={polarity}")
    print(f"figures → {FIGURES}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "metaboscape")

"""T4: Top-level ordination + sample clustering across all conditions.

On the cleaned, median-normalized, log2 abundance matrix (biological samples
only):
  - PCA (numpy SVD on mean-centered features) — three scatter plots of PC1/PC2
    colored by fraction, strain, treatment. Shows how the conditions separate.
  - A top-variance-feature heatmap with samples hierarchically clustered, so
    replicate grouping and the dominant axis are visible directly.

Because P (pellet) and S (supernatant) are different biological matrices, a
fraction-faceted PCA is also written — within-fraction is where the strain /
toluene structure lives once the matrix difference is removed.

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/overview.py metaboscape
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

from lipidio import load_bio, median_normalize, log2, resolve_source

FIGURES = Path(__file__).resolve().parents[3] / "data/fabfos/runs/scadc_lipidomics_figures"
TOP_VAR = 50  # features in the clustered heatmap


def pca(mat: np.ndarray, n: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """PCA via SVD on samples × features (rows centered per feature).
    Returns (scores [samples × n], explained-variance-ratio [n])."""
    x = mat - mat.mean(axis=0, keepdims=True)
    u, s, vt = np.linalg.svd(x, full_matrices=False)
    scores = u[:, :n] * s[:n]
    evr = (s ** 2 / (s ** 2).sum())[:n]
    return scores, evr


def _scatter(ax, scores, evr, labels, title):
    cats = sorted(set(labels))
    cmap = plt.get_cmap("tab10")
    for i, c in enumerate(cats):
        m = np.array(labels) == c
        ax.scatter(scores[m, 0], scores[m, 1], label=str(c), s=40,
                   color=cmap(i % 10), alpha=0.85, edgecolor="k", linewidth=0.3)
    ax.set_xlabel(f"PC1 ({evr[0]*100:.0f}%)")
    ax.set_ylabel(f"PC2 ({evr[1]*100:.0f}%)")
    ax.set_title(title)
    ax.legend(fontsize=7, loc="best")


def run(arg: str) -> None:
    source, polarity, out_base, tag = resolve_source(arg)
    feats, abund, bio = load_bio(source=source, polarity=polarity)
    lg = log2(median_normalize(abund))           # features × samples
    mat = lg.T.to_numpy()                          # samples × features
    FIGURES.mkdir(parents=True, exist_ok=True)

    # --- global PCA (all samples) -----------------------------------------------
    scores, evr = pca(mat)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    _scatter(axes[0], scores, evr, bio.fraction.tolist(), f"{tag} PCA — fraction")
    _scatter(axes[1], scores, evr, bio.strain.tolist(), f"{tag} PCA — strain")
    _scatter(axes[2], scores, evr, bio.treatment.tolist(), f"{tag} PCA — treatment")
    fig.tight_layout()
    fig.savefig(FIGURES / f"pca_global_{tag}.png", dpi=150)
    plt.close(fig)

    pd.DataFrame({"sample": bio.index, "PC1": scores[:, 0], "PC2": scores[:, 1],
                  "strain": bio.strain.values, "treatment": bio.treatment.values,
                  "fraction": bio.fraction.values}).to_csv(
        out_base / f"pca_global_{tag}.csv", index=False)

    # --- per-fraction PCA (matrix difference removed) ---------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, frac in zip(axes, ["P", "S"]):
        sel = bio.fraction.values == frac
        if sel.sum() < 3:
            continue
        sc, ev = pca(mat[sel])
        sub = bio[sel]
        lbl = (sub.strain + "_" + sub.treatment).tolist()
        _scatter(ax, sc, ev, lbl, f"{tag} {frac}-fraction PCA — strain_treatment")
    fig.tight_layout()
    fig.savefig(FIGURES / f"pca_byfraction_{tag}.png", dpi=150)
    plt.close(fig)

    # --- top-variance clustered heatmap -----------------------------------------
    var = lg.var(axis=1).sort_values(ascending=False)
    top = lg.loc[var.index[:TOP_VAR]]
    # z-score per feature for visualization
    z = top.sub(top.mean(axis=1), axis=0).div(top.std(axis=1).replace(0, 1), axis=0)
    col_colors = bio.fraction.map({"P": "#4477AA", "S": "#EE6677"})
    g = sns.clustermap(z, cmap="vlag", center=0, figsize=(14, 10),
                       col_colors=col_colors.values, xticklabels=True,
                       yticklabels=[str(n)[:24] for n in feats["lipid_name"].reindex(top.index).values],
                       cbar_kws={"label": "z-score (log2)"})
    g.fig.suptitle(f"{tag} — top {TOP_VAR} variance features (samples clustered; blue=P, red=S)", y=1.02)
    g.savefig(FIGURES / f"heatmap_topvar_{tag}.png", dpi=150)
    plt.close(g.fig)

    print(f"PCA global EVR: PC1={evr[0]*100:.1f}% PC2={evr[1]*100:.1f}%")
    print(f"figures -> {FIGURES} (pca_global_{tag}.png, pca_byfraction_{tag}.png, heatmap_topvar_{tag}.png)")
    print(f"PCA coords -> {out_base / f'pca_global_{tag}.csv'}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "metaboscape")

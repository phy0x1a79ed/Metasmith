"""2x2 scatter: per-feature toluene response (OD-normalized log2FC tol/ctrl),
clone (x) vs control (y). Pellet (cell) fraction.

  columns = clones     : Clone1, Clone2
  rows    = controls   : Epi300 (parent), EpCC1 (empty-vector)
  each dot = one lipid feature (ALL 2180, annotated or not)

If the controls raise per-cell lipid under toluene while the clones stay flat,
the cloud sits ABOVE the y=x diagonal: control log2FC positive, clone log2FC ~0.

Source: processed/metaboscape/od_toluene_metaboscape.csv  (OD-normalized contrast)
Writes png+svg to .awm/data/figures/publish/04_lipidomics/
Env: p312.  Run: mamba run -n p312 python research/fabfos/lipidomics/od_lfc_scatter.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
PUB = Path(".awm/data/figures/publish/04_lipidomics")
PUB.mkdir(parents=True, exist_ok=True)

FRACTION = "P"                       # pellet = cell fraction
CLONES = ["Clone1", "Clone2"]        # x-axis (columns)
CONTROLS = ["Epi300", "EpCC1"]       # y-axis (rows)
CTRL_TITLE = {"Epi300": "Epi300 (parent)", "EpCC1": "EpCC1 (empty vector)"}

C_ANN, C_DARK = "#B8B8B8", "#2A6F7F"  # unannotated grey / annotated teal
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def lfc_table():
    d = pd.read_csv(M / "od_toluene_metaboscape.csv")
    d = d[d.fraction == FRACTION]
    wide = d.pivot_table(index="feature_id", columns="strain",
                         values="log2fc_tol_vs_ctrl", aggfunc="first")
    ann = d.groupby("feature_id")["final_class"].first()   # annotated iff non-null
    wide["annotated"] = ann.reindex(wide.index).notna()
    return wide


def main():
    w = lfc_table()
    n_total = len(w)

    # symmetric limits from the 99th pct of finite values across all four strains
    vals = w[CLONES + CONTROLS].to_numpy().ravel()
    vals = vals[np.isfinite(vals)]
    lim = float(np.nanpercentile(np.abs(vals), 99))
    lim = np.ceil(lim * 2) / 2                              # round up to 0.5

    fig, axes = plt.subplots(2, 2, figsize=(9.2, 9.2), sharex=True, sharey=True)
    for r, ctrl in enumerate(CONTROLS):
        for c, clone in enumerate(CLONES):
            ax = axes[r, c]
            sub = w[[clone, ctrl, "annotated"]].dropna(subset=[clone, ctrl])
            sub = sub[np.isfinite(sub[clone]) & np.isfinite(sub[ctrl])]
            un = sub[~sub.annotated]; an = sub[sub.annotated]
            ax.scatter(un[clone], un[ctrl], s=9, c=C_ANN, alpha=0.45, lw=0,
                       label=f"unannotated ({len(un)})")
            ax.scatter(an[clone], an[ctrl], s=14, c=C_DARK, alpha=0.8, lw=0,
                       label=f"annotated ({len(an)})")
            # references: y=x diagonal, zero axes
            ax.plot([-lim, lim], [-lim, lim], "--", color="#999", lw=0.8, zorder=0)
            ax.axhline(0, color="k", lw=0.5, zorder=0); ax.axvline(0, color="k", lw=0.5, zorder=0)
            # stats: correlation + how many features actually respond on each axis
            r_p = sub[clone].corr(sub[ctrl])
            resp_x = (sub[clone].abs() > 1).mean()
            resp_y = (sub[ctrl].abs() > 1).mean()
            ax.text(0.04, 0.96,
                    f"n={len(sub)}\nr={r_p:+.2f}\nresp |LFC|>1:\n  {clone} {resp_x:.0%}\n"
                    f"  {CTRL_TITLE[ctrl].split()[0]} {resp_y:.0%}",
                    transform=ax.transAxes, va="top", ha="left", fontsize=7.5,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#ccc", alpha=0.85))
            ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
            if r == 1:
                ax.set_xlabel(f"{clone}  log2FC(+tol / −tol)")
            if c == 0:
                ax.set_ylabel(f"{CTRL_TITLE[ctrl]}\nlog2FC(+tol / −tol)")
            if r == 0 and c == 1:
                ax.legend(loc="lower right", frameon=True, fontsize=7.5, markerscale=1.4)
    fig.suptitle("Per-feature toluene response — controls (y) vs clones (x), pellet fraction\n"
                 "responses uncorrelated (r≈0); controls move ~2× more features & harder — "
                 "clones stay near-flat (tight to x=0)",
                 fontsize=10.5, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    for ext in ("png", "svg"):
        fig.savefig(PUB / f"03_toluene_lfc_clone_vs_control.{ext}", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"[publish] wrote 03_toluene_lfc_clone_vs_control  (features total={n_total})")


if __name__ == "__main__":
    main()

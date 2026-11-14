"""Figures for the OD-normalized toluene analysis. Writes to data/fabfos/runs/scadc_lipidomics_figures/.

  od_summary_metaboscape.png  4-panel:
    A  OD600 growth (ctrl vs tol) per culture + % retained  — the tolerance phenotype
    B  total lipid signal per OD, log2(tol/ctrl), per strain x fraction  — the headline
    C  # toluene-responsive features per strain (OD-normalized, q<0.05 & |lfc|>1)
    D  why OD-norm is needed: total-lipid log2(tol/ctrl) under raw / median / OD

Env: p312. Run: mamba run -n p312 python research/fabfos/lipidomics/od_figures.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipidio import load_od  # noqa: E402

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
FIG = Path("data/fabfos/runs/scadc_lipidomics_figures")
FIG.mkdir(parents=True, exist_ok=True)

C_CTRL, C_TOL = "#4C72B0", "#DD8452"        # control (blue) / toluene (orange)
C_BG, C_CLONE = "#B0B0B0", "#2A9D8F"        # background (grey) / clone (teal)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def panelA(ax):
    od = load_od().groupby(["culture", "treatment"])["od600"].agg(["mean", "std"]).reset_index()
    cultures = ["EPI300", "EpCC1", "Clone1", "Clone2"]
    x = np.arange(len(cultures)); w = 0.38
    for i, tr in enumerate(("ctrl", "tol")):
        d = od[od.treatment == tr].set_index("culture").reindex(cultures)
        ax.bar(x + (i - 0.5) * w, d["mean"], w, yerr=d["std"], capsize=3,
               color=C_CTRL if tr == "ctrl" else C_TOL,
               label="− toluene" if tr == "ctrl" else "+ toluene")
    ret = od.pivot(index="culture", columns="treatment", values="mean").reindex(cultures)
    for i, cu in enumerate(cultures):
        pct = 100 * ret.loc[cu, "tol"] / ret.loc[cu, "ctrl"]
        ax.text(i, ret.loc[cu, "ctrl"] + 0.05, f"{pct:.0f}%", ha="center", fontsize=8,
                color="#333")
    ax.set_xticks(x); ax.set_xticklabels(cultures)
    ax.set_ylabel("OD$_{600}$ (6 d)"); ax.set_title("A  Growth phenotype — % retained in toluene")
    ax.legend(frameon=False, fontsize=8)


def panelB(ax):
    tot = pd.read_csv(M / "od" / "od_total_lipid.csv")
    tot["lab"] = tot["strain"] + " [" + tot["fraction"] + "]"
    order = ["Epi300", "EpCC1", "Clone1", "Clone2", "ESi300", "ESCC1", "Clone1", "Clone2"]
    frac = ["P", "P", "P", "P", "S", "S", "S", "S"]
    labs, vals, cols = [], [], []
    for st, fr in zip(order, frac):
        r = tot[(tot.strain == st) & (tot.fraction == fr)]
        if r.empty:
            continue
        labs.append(f"{st}\n[{fr}]"); vals.append(r["log2_per_od_tol_over_ctrl"].iloc[0])
        cols.append(C_CLONE if st in ("Clone1", "Clone2") else C_BG)
    y = np.arange(len(labs))
    ax.barh(y, vals, color=cols)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=7.5); ax.invert_yaxis()
    ax.set_xlabel("log2 (total lipid per OD:  tol / ctrl)")
    ax.set_title("B  Per-biomass lipid change under toluene")
    ax.text(0.97, 0.04, "grey = background   teal = clone", transform=ax.transAxes,
            ha="right", fontsize=7, color="#555")


def panelC(ax):
    tol = pd.read_csv(M / "od_toluene_metaboscape.csv")
    sig = (tol.qvalue < 0.05) & (tol.log2fc_tol_vs_ctrl.abs() > 1)
    tol = tol.assign(sig=sig)
    rows = []
    for (fr, st), g in tol.groupby(["fraction", "strain"]):
        rows.append((f"{st} [{fr}]", int((g.sig & (g.log2fc_tol_vs_ctrl > 0)).sum()),
                     int((g.sig & (g.log2fc_tol_vs_ctrl < 0)).sum()), st))
    d = pd.DataFrame(rows, columns=["lab", "up", "dn", "strain"])
    d = d.sort_values("up", ascending=True)
    y = np.arange(len(d))
    ax.barh(y, d["up"], color=[C_CLONE if s in ("Clone1", "Clone2") else C_BG for s in d.strain])
    for yi, (u, dn) in enumerate(zip(d["up"], d["dn"])):
        ax.text(u + 2, yi, f"{u}↑" + (f" {dn}↓" if dn else ""), va="center", fontsize=7)
    ax.set_yticks(y); ax.set_yticklabels(d["lab"], fontsize=7.5)
    ax.set_xlabel("# toluene-responsive features (q<0.05, |log2FC|>1)")
    ax.set_title("C  Toluene remodels the background lipidome, not the clones'")


def panelD(ax):
    cmp = pd.read_csv(M / "od" / "od_norm_comparison.csv")
    cmp = cmp[cmp.fraction == "P"].set_index("strain").reindex(["Epi300", "EpCC1", "Clone1", "Clone2"])
    schemes = [("totlfc_raw", "raw", "#999"), ("totlfc_median", "median", "#C44E52"),
               ("totlfc_od_geomean", "OD (biomass)", "#2A9D8F")]
    x = np.arange(len(cmp)); w = 0.26
    for i, (col, lab, c) in enumerate(schemes):
        ax.bar(x + (i - 1) * w, cmp[col], w, color=c, label=lab)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels(cmp.index)
    ax.set_ylabel("log2 (total lipid  tol / ctrl)")
    ax.set_title("D  The toluene signal appears only under OD normalization  [pellet]")
    ax.legend(frameon=False, fontsize=8, title="normalization", title_fontsize=8)


def main():
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    panelA(axes[0, 0]); panelB(axes[0, 1]); panelC(axes[1, 0]); panelD(axes[1, 1])
    fig.suptitle("OD-normalized lipidomics — toluene effect in Clone1/Clone2 vs EPI300 background",
                 fontsize=12, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    out = FIG / "od_summary_metaboscape.png"
    fig.savefig(out, dpi=160); fig.savefig(out.with_suffix(".pdf"))
    print(f"[od_figures] wrote {out} (+ .pdf)")


if __name__ == "__main__":
    main()

"""Mechanistic read of the OD-normalized lipidome: what distinguishes the tolerant
clones' membranes, constitutively and under toluene.

Tests the classic solvent-tolerance levers on the SCADC data (all OD-normalized,
group-geomean; env p312):
  1. Membrane order   — abundance-weighted mean acyl double-bond count + chain length
  2. Headgroup mix    — anionic PL (PG/PA/PS), PE, PC, lyso-PL fractions
  3. Membrane damage  — lyso-lipid (LPE/LPC/MAG) load: parent+tol vs clones+tol
  4. Constitutive clone signature — features up in BOTH clones vs parent in CTRL

Writes processed/metaboscape/od/od_mechanism_{membrane,constitutive}.csv and prints a summary.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipidio import load_bio, od_normalize, log2  # noqa: E402

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
OUT = M / "od"
PARENT = {"P": "Epi300", "S": "ESi300"}
ANIONIC = {"PG", "PA", "PS", "O-PG", "O-PA", "O-PS", "HBMP"}   # HBMP = bis(monoacylglycero)P
LYSO = {"LPE", "LPC", "LPG", "LPA", "LPS", "MAG"}


def groups(bio):
    for frac in ("P", "S"):
        for st in ([PARENT[frac]] + (["EpCC1", "Clone1", "Clone2"] if frac == "P"
                                     else ["ESCC1", "Clone1", "Clone2"])):
            for tr in ("ctrl", "tol"):
                cols = bio[(bio.strain == st) & (bio.fraction == frac) &
                           (bio.treatment == tr)].index.tolist()
                if cols:
                    yield frac, st, tr, cols


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    feats, abund_raw, bio = load_bio(source="metaboscape", polarity="merged")
    fm = pd.read_csv(M / "features_mapped.csv", index_col="feature_id")
    od = od_normalize(abund_raw, "group_geomean")
    bio = bio.loc[od.columns]

    db = fm["total_db"].reindex(od.index)
    cc = fm["total_carbon"].reindex(od.index)
    cls = fm["final_class"].reindex(od.index)
    mean_amp = od.T.groupby([bio.strain, bio.fraction, bio.treatment]).mean().T  # feature x group

    rows = []
    for frac, st, tr, cols in groups(bio):
        amp = od[cols].mean(axis=1)                       # per-feature mean OD-norm abundance
        m = db.notna() & (amp > 0)
        w = amp[m]
        rec = dict(fraction=frac, strain=st, treatment=tr,
                   wmean_double_bonds=float((w * db[m]).sum() / w.sum()),
                   wmean_chain_C=float((w * cc[m]).sum() / w.sum()))
        tot = amp.sum()
        for grpname, members in [("anionic_frac", ANIONIC), ("lyso_frac", LYSO),
                                 ("PE_frac", {"PE", "O-PE", "PE-P", "PE-NMe"}),
                                 ("PC_frac", {"PC", "O-PC", "PC-P", "LPC"})]:
            inmem = cls.isin(members)
            rec[grpname] = float(amp[inmem].sum() / tot)
        rec["mapped_total_od"] = float(amp[cls.notna()].sum())
        rows.append(rec)
    mem = pd.DataFrame(rows)
    mem.to_csv(OUT / "od_mechanism_membrane.csv", index=False)

    # --- constitutive clone signature: up in BOTH clones vs parent, CTRL, pellet ------
    lg = log2(od)
    def mean_lg(st, tr, frac):
        cols = bio[(bio.strain == st) & (bio.fraction == frac) & (bio.treatment == tr)].index
        return lg[cols].mean(axis=1)
    sig_rows = []
    for frac in ("P", "S"):
        par = PARENT[frac]
        p = mean_lg(par, "ctrl", frac)
        c1 = mean_lg("Clone1", "ctrl", frac)
        c2 = mean_lg("Clone2", "ctrl", frac)
        d = pd.DataFrame({"clone1_vs_parent": c1 - p, "clone2_vs_parent": c2 - p,
                          "final_class": cls, "mz": fm["mz"].reindex(od.index),
                          "rt": fm["rt"].reindex(od.index),
                          "name": fm["lipid_name"].reindex(od.index)})
        d["fraction"] = frac
        d["both_up"] = (d.clone1_vs_parent > 1) & (d.clone2_vs_parent > 1)
        d["both_dn"] = (d.clone1_vs_parent < -1) & (d.clone2_vs_parent < -1)
        sig_rows.append(d)
    con = pd.concat(sig_rows).reset_index()
    con.to_csv(OUT / "od_mechanism_constitutive.csv", index=False)

    pd.set_option("display.width", 170, "display.max_columns", 20)
    print("=== membrane order & headgroup mix (OD-normalized, mapped features) ===")
    show = mem.copy()
    for c in ["wmean_double_bonds", "wmean_chain_C", "anionic_frac", "lyso_frac", "PE_frac", "PC_frac"]:
        show[c] = show[c].round(3)
    print(show[["fraction", "strain", "treatment", "wmean_double_bonds", "wmean_chain_C",
                "anionic_frac", "PE_frac", "PC_frac", "lyso_frac"]].to_string(index=False))

    print("\n=== constitutive clone signature (CTRL): #features up/down in BOTH clones vs parent (|log2|>1) ===")
    for frac in ("P", "S"):
        g = con[con.fraction == frac]
        print(f"  [{frac}] vs {PARENT[frac]}: {int(g.both_up.sum())} up in both clones, "
              f"{int(g.both_dn.sum())} down in both; "
              f"of the up: {int(g[g.both_up].final_class.notna().sum())} annotated")
        top = g[g.both_up].assign(minfc=g[g.both_up][['clone1_vs_parent','clone2_vs_parent']].min(axis=1))
        top = top.sort_values("minfc", ascending=False).head(8)
        for _, r in top.iterrows():
            print(f"      +{r.minfc:4.1f} log2  {str(r.final_class or '(dark)'):10s} m/z {r.mz:8.3f} RT {r.rt:5.2f}  {str(r['name'])[:32]}")

    print("\n=== membrane-damage (lyso) load: parent+tol vs clones+tol ===")
    for frac in ("P", "S"):
        sub = mem[(mem.fraction == frac) & (mem.treatment == "tol")]
        print(f"  [{frac}] lyso_frac  " + "  ".join(
            f"{r.strain}={r.lyso_frac:.3f}" for _, r in sub.iterrows()))
    print(f"\n[od_mechanism] wrote -> {OUT}/od_mechanism_membrane.csv, od_mechanism_constitutive.csv")


if __name__ == "__main__":
    main()

"""Master tally across every differential-contrast family.

Reads the per-family CSVs written by diff_toluene / diff_strain / diff_matrix /
diff_global and produces one summary row per contrast: features tested, features
significant (q<0.05 & |log2FC|>1), and present/absent on-off features. This is
the at-a-glance answer to "the significant differences between the conditions".

Run: mamba run --no-capture-output -n p312 python -u research/fabfos/lipidomics/diff_summary.py metaboscape
"""
from __future__ import annotations
import sys

import pandas as pd

from lipidio import resolve_source

# family file stem -> (grouping columns, fold-change column or None)
FAMILIES = {
    "diff_toluene": (["strain", "fraction"], "log2fc_tol_vs_ctrl"),
    "diff_strain": (["strain", "parent", "treatment", "fraction"], "log2fc_strain_vs_parent"),
    "diff_strainpairs": (["fraction", "treatment", "strain_a", "strain_b"], "log2fc_a_vs_b"),
    "diff_pvss": (["strain", "treatment"], "log2fc_P_vs_S"),
    "diff_global": (["fraction"], None),  # omnibus: q only (anova q in `qvalue`)
}


def run(arg: str) -> None:
    _, _, out_base, tag = resolve_source(arg)
    out_rows = []
    for stem, (group_cols, fc_col) in FAMILIES.items():
        csv = out_base / f"{stem}_{tag}.csv"
        if not csv.exists():
            print(f"skip (missing): {csv}", file=sys.stderr)
            continue
        df = pd.read_csv(csv)
        for keys, g in df.groupby(group_cols):
            keys = keys if isinstance(keys, tuple) else (keys,)
            if fc_col is not None:
                sig = ((g.qvalue < 0.05) & (g[fc_col].abs() > 1)).sum()
                sig_label = "q<0.05 & |log2FC|>1"
            else:
                sig = (g.qvalue < 0.05).sum()
                sig_label = "anova q<0.05"
            out_rows.append({
                "family": stem,
                "contrast": " / ".join(f"{c}={v}" for c, v in zip(group_cols, keys)),
                "n_tested": len(g),
                "n_significant": int(sig),
                "sig_criterion": sig_label,
                "n_present_absent": int(g.present_absent.sum()) if "present_absent" in g else 0,
            })

    summary = pd.DataFrame(out_rows)
    csv = out_base / f"diff_summary_{tag}.csv"
    summary.to_csv(csv, index=False)
    print(f"wrote {csv} ({len(summary)} contrasts)\n")
    with pd.option_context("display.max_rows", None, "display.width", 160):
        print(summary.to_string(index=False))
    print("\n== significant features by family ==")
    print(summary.groupby("family").n_significant.sum().to_string())


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "metaboscape")

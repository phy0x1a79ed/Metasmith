"""Summarise model_balance.py's interventions.

    summarise_interventions.py <model_balance_B.jsonl> <model_balance_U.jsonl> <out_dir>

Writes model_interventions.tsv (one row per sampled model, without the reaction lists) and
intervention_summary.tsv (per rung, the share of inconsistent models each intervention repairs).
"""
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

STEPS = ["drop_exclusive", "drop_changed", "patch_changed", "drop_h_only", "patch_and_drop"]


def main(b, u, out):
    out = Path(out)
    d = pd.DataFrame([json.loads(l) for p in (b, u) for l in open(p)])
    d["changed_held"] = d.changed_held.map(lambda l: [i for i in l if i != "Growth"])
    for c in ("exclusive_held", "changed_held", "h_only_held"):
        d[f"n_{c}"] = d[c].map(len)
    d.drop(columns=["reaction_ids", "exclusive_held", "changed_held", "h_only_held"]).to_csv(out / "model_interventions.tsv", sep="\t", index=False)
    rows = []
    for rung, x in d.groupby("rung"):
        inc = x[~x.consistent]
        row = {"rung": rung, "models": len(x), "consistent_as_built": round(x.consistent.mean(), 3), "inconsistent": len(inc),
               "median_exclusive_held": x.n_exclusive_held.median(), "median_changed_held": x.n_changed_held.median(),
               "median_h_only_held": x.n_h_only_held.median()}
        row.update({f"repaired_by_{s}": round(inc[s].mean(), 3) if len(inc) else None for s in STEPS})
        rows.append(row)
    pd.DataFrame(rows).to_csv(out / "intervention_summary.tsv", sep="\t", index=False)
    print(pd.DataFrame(rows).T.to_string())
    for rung, x in d.groupby("rung"):
        inc = x[~x.consistent]
        print(rung, "reactions held by inconsistent models:",
              Counter(i for l in inc[inc.n_changed_held > 0].changed_held for i in l).most_common(6))


if __name__ == "__main__":
    main(*sys.argv[1:])

"""Break MEMOTE 0.17's consistency score into its five tests, rung by rung.

    consistency_tests.py <per_test_asbuilt.tsv> <per_test_rewritten.tsv> <out_dir>

Reads per_test.py's tables. MEMOTE's consistency section is the weighted mean of 1 - metric over five
tests (weights below, read from memote.suite.reporting.ReportConfiguration). Writes
consistency_by_test.tsv (per lane and test: B and U medians and means, the paired B-to-U change, and its
share of the consistency change) and consistency_per_model.tsv (one row per model).
"""
import json
import sys
from pathlib import Path

import pandas as pd

WEIGHTS = {
    "test_stoichiometric_consistency": 3,
    "test_reaction_mass_balance": 1,
    "test_reaction_charge_balance": 1,
    "test_find_disconnected": 1,
    "test_find_reactions_unbounded_flux_default_condition": 1,
}
TOTAL = sum(WEIGHTS.values())


def scored(path):
    d = pd.read_csv(path, sep="\t")
    for t in WEIGHTS:
        d[t] = 1 - d[f"m:{t}"]
    d["consistency"] = sum(w * d[t] for t, w in WEIGHTS.items()) / TOTAL
    return d


def by_test(d, lane):
    wide = {t: d.pivot(index="bin", columns="source", values=t) for t in [*WEIGHTS, "consistency"]}
    rows = []
    for t, w in [*WEIGHTS.items(), ("consistency", TOTAL)]:
        b, u = wide[t]["B"], wide[t]["U"]
        diff = (u - b).dropna()
        rows.append({
            "lane": lane, "test": t, "weight": w,
            "median_B": b.median(), "median_U": u.median(), "mean_B": b.mean(), "mean_U": u.mean(),
            "paired_mean_change": diff.mean(), "paired_median_change": diff.median(),
            "share_of_consistency_change_pts": w / TOTAL * diff.mean(),
            "pass_rate_B": (b >= 0.999).mean(), "pass_rate_U": (u >= 0.999).mean(),
            "bins_improved": (diff > 0.01).mean(), "bins_worse": (diff < -0.01).mean(), "bins": len(diff),
        })
    return rows


def main(asbuilt, rewritten, out):
    out = Path(out)
    lanes = {"as_built": scored(asbuilt), "rewritten": scored(rewritten)}
    rows = [r for lane, d in lanes.items() for r in by_test(d, lane)]
    pd.DataFrame(rows).round(4).to_csv(out / "consistency_by_test.tsv", sep="\t", index=False)
    frames = []
    for lane, d in lanes.items():
        ids = d["ids:test_unconserved_metabolites"].map(lambda v: ",".join(json.loads(v)) if isinstance(v, str) else "")
        frames.append(d.assign(lane=lane, unconserved=ids)[["lane", "source", "bin", *WEIGHTS, "consistency", "unconserved"]])
    pd.concat(frames).round(4).to_csv(out / "consistency_per_model.tsv", sep="\t", index=False)


if __name__ == "__main__":
    main(*sys.argv[1:])

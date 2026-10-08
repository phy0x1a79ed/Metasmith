"""Score each ablation rung's pooled catalogue against Pratama's 257,252 vOTUs, and join the CPU ledger.

Per rung: vOTU count, Pratama recovery at ANI >= 95 / AF >= 85 on the published side, the rung's own vOTUs matched
the same way on its side, and the one-to-one identity distribution (votu_lib.pair, as e3_pairing.py). Writes
rungs.json next to this file. The rung catalogues are too large to commit and are read from
$E3_FIG (default ~/scratch/e3_fig), as are the paired tables written back there.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("E3_FIG", "~/scratch/e3_fig")).expanduser()
sys.path.insert(0, str(HERE.parent))
from votu_lib import pair, violin  # noqa: E402

TALLY = HERE.parent / "published_votu_tally.tsv.gz"
ANI_MIN, AF_MIN = 95, 85
GRID = np.round(np.arange(10, 100.0001, 0.5), 2)
RUNGS = {
    "R0": (DATA / "final_votus.fna", DATA / "final_skani.tsv"),
    **{r: (next((DATA / "ablation" / r / "e3-final_votu_representatives").glob("*.fna")),
           next((DATA / "ablation" / r / "e3-final_votu_recovery_table").iterdir())) for r in ("R1", "R2", "R3", "R4")},
}

pub = pd.read_csv(TALLY, sep="\t")[["name", "lane"]]
assert len(pub) == 257252, len(pub)
pub_idx = pd.Series(np.arange(len(pub)), index=pub.name)
recovered_any = np.zeros(len(pub), bool)

out = {"grid": GRID.tolist(), "thresholds": {"ani": ANI_MIN, "af": AF_MIN}, "published": len(pub), "rungs": {}}
for rung, (fna, skani) in RUNGS.items():
    heads = subprocess.run(["grep", "-F", ">", str(fna)], capture_output=True, text=True, check=True).stdout
    ours = pd.DataFrame({"name": [h[1:].split()[0] for h in heads.splitlines()]})
    ours["lane"] = ours.name.str.split("|").str[1]
    ours_idx = pd.Series(np.arange(len(ours)), index=ours.name)

    sk = pd.read_csv(skani, sep="\t",
                     usecols=["ANI", "Align_fraction_ref", "Align_fraction_query", "Ref_name", "Query_name"])
    sk.columns = ["ani", "af_ours", "af_pub", "ours", "pub"]
    sk["ours"] = sk.ours.str.split().str[0]
    sk["pub"] = sk.pub.str.split().str[0]
    assert sk.pub.isin(pub_idx.index).all() and sk.ours.isin(ours_idx.index).all(), rung
    sk["i"] = pub_idx[sk.pub].to_numpy()
    sk["j"] = ours_idx[sk.ours].to_numpy()
    # Identity over the published vOTU's whole length: its unaligned bases count as mismatches.
    sk["identity"] = sk.ani * sk.af_pub / 100

    hit = (sk.ani >= ANI_MIN) & (sk.af_pub >= AF_MIN)
    recovered = np.zeros(len(pub), bool)
    recovered[sk.i[hit]] = True
    recovered_any |= recovered
    matched = np.zeros(len(ours), bool)
    matched[sk.j[(sk.ani >= ANI_MIN) & (sk.af_ours >= AF_MIN)]] = True

    paired = pair(sk, len(pub), len(ours))
    paired.to_csv(DATA / "ablation" / f"{rung}_paired.tsv", sep="\t")
    v = violin(paired.identity, GRID, 3)
    out["rungs"][rung] = {
        "votus": len(ours), "matched": int(matched.sum()),
        "lanes": ours.lane.value_counts().to_dict(),
        "matched_lanes": ours.lane[matched].value_counts().to_dict(),
        "recovered": int(recovered.sum()), "recovery": round(recovered.mean(), 4),
        "paired": v,
        "paired_recovered": int(((paired.ani >= ANI_MIN) & (paired.af_pub >= AF_MIN)).sum()),
    }
    r = out["rungs"][rung]
    print(rung, {k: r[k] for k in ("votus", "matched", "recovered", "recovery", "paired_recovered")},
          (v["n"], v["median"], v["q1"], v["q3"]), r["lanes"], file=sys.stderr, flush=True)

out["recovered_any_rung"] = int(recovered_any.sum())
cpu = json.loads((HERE / "cpu.json").read_text())
for rung, r in out["rungs"].items():
    r["cpu_h"] = cpu["rungs"][rung]
out["cpu_units"] = cpu["units"]
out["cpu_proxied"] = cpu["proxied"]
out["ablation_spent"] = cpu["ablation_spent"]
(HERE / "rungs.json").write_text(json.dumps(out))

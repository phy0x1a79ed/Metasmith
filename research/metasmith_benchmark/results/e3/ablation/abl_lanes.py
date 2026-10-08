"""Pratama recovery per published assembler lane (ANI >= 95, af_pub >= 85, any rung vOTU), per rung."""
import json
import os
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("E3_FIG", "~/scratch/e3_fig")).expanduser()
TALLY = HERE.parent / "published_votu_tally.tsv.gz"
pub = pd.read_csv(TALLY, sep="\t")[["name", "lane"]]
TABLES = {"R0": DATA / "final_skani.tsv",
          **{r: next((DATA / "ablation" / r / "e3-final_votu_recovery_table").iterdir()) for r in ("R1", "R2", "R3", "R4")}}
out = {"published": pub.lane.value_counts().to_dict()}
for rung, t in TABLES.items():
    sk = pd.read_csv(t, sep="\t", usecols=["ANI", "Align_fraction_query", "Query_name"])
    hit = set(sk.Query_name[(sk.ANI >= 95) & (sk.Align_fraction_query >= 85)].str.split().str[0])
    rec = pub[pub.name.isin(hit)].lane.value_counts()
    out[rung] = {lane: round(rec.get(lane, 0) / n, 4) for lane, n in out["published"].items()}
    print(rung, out[rung], flush=True)
(HERE / "lanes.json").write_text(json.dumps(out, indent=1))

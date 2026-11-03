# Figure 2C's KOfam and KOfam + DIAMOND lanes. Adds them to the E4R, E4M and E4 constants of reproduction.html in place:
# bars from evidence_fig2c.tsv, violins from the per-bin reaction Jaccard against metaGEM in evidence_parity.tsv. Both
# lanes exist only on the E4 ablation's 1,408-bin subset. Inputs are on feat/engine/bench-E5; run with the msm env.
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BENCH = Path.home() / "agentic_workspace/projects/metasmith/engine/bench-E5/research/metasmith_benchmark"
E4_DIR = BENCH / "results/e4"
PAGE = HERE / "reproduction.html"
LANES = {"kofam": "kofam", "both": "both"}
STUDIES = ["sunagawa2015", "karlsson2013", "bissett_base", "li2019", "korem2015"]

fig = pd.read_csv(E4_DIR / "evidence_fig2c.tsv", sep="\t")
fig = fig[fig.study != "pooled"].set_index(["lane", "metric", "study"])
parity = pd.read_csv(E4_DIR / "evidence_parity.tsv", sep="\t")
parity = parity[parity.against == "metagem"]


def bars(lane, metric, digits):
    return {st: {"n": int(r.n), "q1": round(r.q1, digits), "median": round(r["median"], digits), "q3": round(r.q3, digits)}
            for st in STUDIES for r in [fig.loc[(lane, metric, st)]]}


page = PAGE.read_text()
const = {n: json.loads(re.search(rf"const {n} = (.*?);</script>", page)[1]) for n in ("E4R", "E4M", "E4")}
for lane in LANES:
    const["E4R"][lane] = bars(lane, "reactions", 2)
    const["E4M"][lane] = bars(lane, "memote_total", 4)
    q = parity[parity.lane == lane]
    const["E4"][lane] = {st: [round(x, 4) for x in q[q.study == st].reactions_jaccard] for st in STUDIES}
    for st in STUDIES:
        assert len(const["E4"][lane][st]) == const["E4R"][lane][st]["n"], (lane, st)

print("study  lane  memote  reactions  jaccard  n(memote/reactions/jaccard)", file=sys.stderr)
for lane in LANES:
    for st in STUDIES:
        print(st, lane, const["E4M"][lane][st]["median"], const["E4R"][lane][st]["median"],
              fig.loc[(lane, "reactions_jaccard_metagem", st), "median"],
              const["E4M"][lane][st]["n"], const["E4R"][lane][st]["n"], len(const["E4"][lane][st]), file=sys.stderr)
print("modern reactions, subset (M) vs full run", file=sys.stderr)
for st in STUDIES:
    sub, full = fig.loc[("M", "reactions", st), "median"], const["E4R"]["modern"][st]["median"]
    print(st, sub, full, round(sub - full, 1), f"{100 * (sub - full) / full:+.1f}%", file=sys.stderr)

for name, value in const.items():
    page, n = re.subn(rf"const {name} = .*?;</script>", lambda _: f"const {name} = {json.dumps(value)};</script>", page)
    assert n == 1, name
PAGE.write_text(page)

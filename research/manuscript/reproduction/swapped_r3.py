# Figure 2B's vOTU counts, identity violins and CPU bars with the E3 ablation's rung R3 (run osU8IP4o) as the swapped
# assemblers: its MEGAHIT lane for the de Bruijn group, its MEGAHIT -> OPERA-MS lane for the hybrid group.
# Rewrites the E3K and E3C constants of reproduction.html in place. Inputs are the scored catalogues in
# ~/scratch/e3_fig and the E3 helpers on feat/engine/bench-E3; run with the msm env.
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SCRATCH = Path.home() / "scratch/e3_fig"
ABL = SCRATCH / "ablation"
BENCH = Path.home() / "agentic_workspace/projects/metasmith/engine/bench-E3/research/metasmith_benchmark"
sys.path.insert(0, str(BENCH / "results/e3"))
from votu_lib import pair, violin  # noqa: E402
from votu_recovery_curve import run_keys  # noqa: E402

ANI_MIN, AF_MIN = 95, 85
GRID = np.round(np.arange(10, 100.0001, 0.5), 2)
PAGE = HERE / "reproduction.html"

keys = run_keys()
label_run = dict(reversed(l.strip().split("/")) for l in open(SCRATCH / "e3_labels.txt"))
pub = pd.read_csv(BENCH / "results/e3/published_votu_tally.tsv.gz", sep="\t")[["sample", "lane", "name"]]
pub_idx = pd.Series(np.arange(len(pub)), index=pub.name)


def catalogue(fna, skani):
    heads = subprocess.run(["grep", "-F", ">", str(fna)], capture_output=True, text=True, check=True).stdout
    ours = pd.DataFrame({"name": [h[1:].split()[0] for h in heads.splitlines()]})
    ours["sample"] = ours.name.str.split("|").str[0].map(label_run).map(keys)
    ours["lane"] = ours.name.str.split("|").str[1]
    assert ours["sample"].notna().all(), fna
    sk = pd.read_csv(skani, sep="\t", usecols=["ANI", "Align_fraction_ref", "Align_fraction_query", "Ref_name", "Query_name"])
    sk.columns = ["ani", "af_ours", "af_pub", "ours", "pub"]
    sk["ours"] = sk.ours.str.split().str[0]
    sk["pub"] = sk.pub.str.split().str[0]
    sk["i"] = pub_idx[sk.pub].to_numpy()
    sk["j"] = pd.Series(np.arange(len(ours)), index=ours.name)[sk.ours].to_numpy()
    sk["identity"] = sk.ani * sk.af_pub / 100
    return ours, sk


e3, e3_sk = catalogue(SCRATCH / "final_votus.fna", SCRATCH / "final_skani.tsv")
r3, r3_sk = catalogue(next((ABL / "R3/e3-final_votu_representatives").glob("*.fna")),
                      next((ABL / "R3/e3-final_votu_recovery_table").iterdir()))
SETS = {"repro": (e3, e3_sk, ["spades", "megahit"]), "spades_only": (e3, e3_sk, ["spades"]),
        "hybrid": (e3, e3_sk, ["hybrid"]), "megahit_r3": (r3, r3_sk, ["megahit"]), "opera_ms_r3": (r3, r3_sk, ["hybrid"])}
GROUPS = {"short": (["spades", "megahit"], ["repro", "spades_only", "megahit_r3"]),
          "hybrid": (["hybrid"], ["hybrid", "opera_ms_r3"])}
VIOLINS = {"short": ["repro", "spades_only", "megahit_r3"], "hybrid": ["opera_ms_r3"]}

counts = lambda total, solid, n: {"n": n, "total": int(total), "matched": int(solid),
                                  "per_sample": round(total / n, 1), "matched_per_sample": round(solid / n, 1)}
core = {"violins": {}}
for group, (lanes, members) in GROUPS.items():
    own = {k: SETS[k][0][SETS[k][0].lane.isin(SETS[k][2])] for k in members}
    samples = set.intersection(*(set(d["sample"]) for d in own.values()))
    p = pub[pub.lane.isin(lanes) & pub["sample"].isin(samples)]
    own = {k: d[d["sample"].isin(samples)] for k, d in own.items()}
    hits = {k: SETS[k][1][SETS[k][1].i.isin(p.index) & SETS[k][1].j.isin(d.index) & (SETS[k][1].ani >= ANI_MIN)]
            for k, d in own.items()}
    recovered = set().union(*(set(h.i[h.af_pub >= AF_MIN]) for h in hits.values()))
    n = len(samples)
    core[group] = {"pratama": counts(len(p), len(recovered), n)}
    for k, d in own.items():
        h = hits[k]
        core[group][k] = counts(len(d), len(set(h.j[h.i.isin(recovered) & (h.af_ours >= AF_MIN)])), n)
    core["violins"][group] = {}
    for k in VIOLINS[group]:
        ours, sk = SETS[k][:2]
        q = pair(sk[sk.i.isin(p.index) & sk.j.isin(own[k].index)], len(pub), len(ours))
        core["violins"][group][k] = violin(q.identity, GRID, 3)
    print(group, n, json.dumps(core[group]), {k: (v["n"], v["median"]) for k, v in core["violins"][group].items()},
          file=sys.stderr)

SACCT = ["sacct_pratama_all.txt", "sacct_abl_jobs.txt", "sacct_r4first.txt"]
sa = pd.concat([pd.read_csv(ABL / "cpu" / f, sep="|", header=None, dtype={"job": str},
                            names=["job", "name", "state", "elapsed", "cpus", "start", "end", "workdir"]) for f in SACCT])
sa = sa.drop_duplicates("job")
sa["cpu_h"] = sa.elapsed * sa.cpus / 3600


def stats(x):
    return {"n": len(x), "mean": round(x.mean(), 1), "sd": round(x.std(), 1), "q1": round(x.quantile(.25), 1),
            "median": round(x.median(), 1), "q3": round(x.quantile(.75), 1)}


# A2 is the reproduction's own MEGAHIT array in Son2YJiI, which R3 served from cache.
a2 = sa[(sa.state == "COMPLETED") & sa.workdir.str.contains("/runs/Son2YJiI/") & (sa.start < "2026-10-01")
        & sa.name.str.match(r"nf-p04__megahit_\(\d+\)$")]
assert len(a2) == 65, len(a2)

# A6 ran one hybrid sample in the smoke run 1DdONH9q and the other 16 in osU8IP4o. A draft and its OPERA-MS task are
# paired through the sample inputs both consume, read from each task's archived .command.cache.
PAIR_SLOTS = ("F1ypKJ4g", "A9vMPJmL", "rVQo8jCC", "Ub6VCm2B")
a6 = []
for run in ("osU8IP4o", "1DdONH9q"):
    t = pd.read_csv(ABL / f"cpu/{run}.tasks.csv")
    t = t[(t.status == "COMPLETED") & t.name.str.match(r"p0[57]__(megahit_draft|opera_ms)_pratama \(")]
    with tarfile.open(SCRATCH / f"abl_archive/meta_local/nxf_command_cache_{run}.tar.gz") as tar:
        caches = {m.name.split("/")[1] + "/" + m.name.split("/")[2][:6]: m for m in tar if m.name.endswith(".command.cache")}
        for r in t.itertuples():
            c = json.load(tar.extractfile(caches[r.hash]))
            a6.append({"job": str(r.native_id), "pairing": tuple(c["consumes"][s][0] for s in PAIR_SLOTS)})
a6 = pd.DataFrame(a6).merge(sa[["job", "cpu_h"]], on="job", how="left")
assert a6.cpu_h.notna().all() and len(a6) == 34
a6 = a6.groupby("pairing").cpu_h.agg(["sum", "size"])
assert len(a6) == 17 and (a6["size"] == 2).all()

page = PAGE.read_text()
e3c = json.loads(re.search(r"const E3C = (.*?);</script>", page)[1])
for gone in ("megahit_e5", "opera_ms"):
    e3c.pop(gone, None)
e3c["megahit_r3"] = stats(a2.cpu_h)
e3c["opera_ms_r3"] = stats(a6["sum"])
print("cpu", e3c["megahit_r3"], e3c["opera_ms_r3"], file=sys.stderr)
for name, value in (("E3K", core), ("E3C", e3c)):
    page, n = re.subn(rf"const {name} = .*?;</script>", lambda _: f"const {name} = {json.dumps(value)};</script>", page)
    assert n == 1, name
PAGE.write_text(page)

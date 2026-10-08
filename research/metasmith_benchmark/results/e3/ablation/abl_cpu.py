"""Allocated CPU-hours per ablation rung, crediting each cached unit to the run that computed it.

A unit is one step over one assembly set (an assembler, its contig split, one viral caller) or one rung's pooled
tail. Cost is elapsed x allocated cpus of the successful attempt. E3's own units ran over several relaunches of
Son2YJiI and nP0Jxo8W, some twice, so each is priced as the mean successful task times its task count in the
September trace of nP0Jxo8W. The ablation's units come from each run's nxf_tasks.csv joined to sacct by native_id.
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SEPT_TRACE = HERE / "cpu/nP0Jxo8W.sept.tsv"
R4_RELAUNCH = "2026-10-07T04:48"
ABLATION_RUNS = ["nP0Jxo8W", "arThlxPI", "osU8IP4o", "wdiikdGR", "1DdONH9q", "5dqexz5s", "YyZ06A4o"]

# A dated sacct query drops some array elements, so the ablation's jobs are also queried by id.
SACCT = ["sacct_pratama_all.txt", "sacct_abl_jobs.txt", "sacct_r4first.txt"]
sa = pd.concat([pd.read_csv(HERE / "cpu" / f, sep="|", header=None, dtype={"job": str},
                            names=["job", "name", "state", "elapsed", "cpus", "start", "end", "workdir"]) for f in SACCT])
sa = sa.drop_duplicates("job")
sa["run"] = sa.workdir.str.extract(r"/runs/([^/]+)")[0]
sa["step"] = sa.name.str.replace(r"^nf-", "", regex=True).str.replace(r"_\(\d+\)$", "", regex=True)
sa["cpu_h"] = sa.elapsed * sa.cpus / 3600
done = sa[sa.state == "COMPLETED"]

sept = pd.read_csv(SEPT_TRACE, sep="\t")
sept = sept[sept.status == "COMPLETED"]
sept_n = sept.name.str.replace(r" \(\d+\)$", "", regex=True).str.replace("_cached$", "", regex=True).value_counts()


def e3_unit(run, step, n=None, before="2026-10-01", proxy=None):
    """sacct holds under half of some E3 units' tasks, the rest having run where sacct cannot see them. Such a unit
    is priced at the mean of the proxy step, R1's run of the same transform over the matching lane."""
    g = done[(done.run == run) & (done.step == step) & (done.start < before)]
    n = int(sept_n[step]) if n is None else n
    assert len(g), (run, step)
    if len(g) < n / 2:
        assert proxy, (run, step, len(g), n)
        coverage_gaps[f"{run}:{step}"] = {"sacct_tasks": len(g), "tasks": n, "proxy": proxy}
        g = done[(done.run == N) & (done.step == proxy) & (done.start >= "2026-10-05")]
    return round(g.cpu_h.mean() * n, 1)


def computed(run, steps, before=None, after=None):
    """Successful CPU-h of the given steps in one run, from its task list where one survives, else from sacct."""
    csv = HERE / f"cpu/{run}.tasks.csv"
    if csv.exists() and before is None:
        t = pd.read_csv(csv)
        t = t[(t.status == "COMPLETED") & ~t.name.str.contains("_cached")]
        t["step"] = t.name.str.replace(r" \(\d+\)$", "", regex=True)
        t = t[t.step.isin(steps)].merge(sa[["job", "cpu_h"]], left_on="native_id", right_on="job", how="left")
        assert t.cpu_h.notna().all(), (run, t[t.cpu_h.isna()].name.tolist()[:5])
        return round(t.cpu_h.sum(), 1)
    g = done[(done.run == run) & done.step.isin(steps)]
    if before:
        g = g[g.start < before]
    return round(g.cpu_h.sum(), 1)


def r4_unit(step, n):
    """R4's hybrid lane ran over a smoke run, a first launch and a relaunch. Some first-launch tasks finished after
    the stop and never reached the cache, so a unit is priced as its mean successful task times its task count."""
    g = done[done.run.isin(["wdiikdGR", "5dqexz5s"]) & (done.step == step)]
    return round(g.cpu_h.mean() * n, 1)


def callers(lo):
    return [f"p{lo:02d}__deepvirfinder_pratama", f"p{lo + 1:02d}__vibrant_pratama",
            f"p{lo + 2:02d}__virsorter2_pratama", f"p{lo + 3:02d}__genomad_pratama"]


S, N = "Son2YJiI", "nP0Jxo8W"
coverage_gaps = {}
qc = sum(e3_unit(S, s, 65) for s in ("p01__seqkit_reads", "p02__bbduk_pratama", "p03__fastp_report_pratama"))

assembly = {
    "A1_spades": e3_unit(S, "p05__spades_pratama", 65),
    "A2_megahit": e3_unit(S, "p04__megahit", 65),
    "A3_hybrid_spades": e3_unit(N, "p06__spades_hybrid_pratama", 17),
    "A4_spades_noec": computed(N, ["p05__spades_pratama_noec"]),
    "A5_hybrid_spades_noec": computed(N, ["p06__spades_hybrid_pratama_noec"]),
    "A6_opera_ms": computed("osU8IP4o", ["p05__megahit_draft_pratama", "p07__opera_ms_pratama"])
                   + computed("1DdONH9q", ["p05__megahit_draft_pratama", "p07__opera_ms_pratama"]),
    "A7A8_flye_polca": r4_unit("p04__flye_pratama", 17) + r4_unit("p06__polca_pratama", 17),
}

# Lane order in the R0/R1 plan (one key): p10/p13-15 hybrid, p11/p16-18 MEGAHIT, p12/p19-21 short metaSPAdes.
# Son2YJiI ran VIBRANT and geNomad first, under its own numbering: p11/p13 MEGAHIT, p14/p16 metaSPAdes.
viral = {
    "A1_spades": e3_unit(S, "p07__splitContigsForAmr", 65)
                 + e3_unit(N, "p12__deepvirfinder_pratama") + e3_unit(N, "p20__virsorter2_pratama")
                 + e3_unit(S, "p14__vibrant_pratama", int(sept_n["p19__vibrant_pratama"]), proxy="p19__vibrant_pratama")
                 + e3_unit(S, "p16__genomad_pratama", int(sept_n["p21__genomad_pratama"]), proxy="p21__genomad_pratama"),
    "A2_megahit": e3_unit(S, "p06__splitContigsForAmr", 65)
                  + e3_unit(N, "p11__deepvirfinder_pratama") + e3_unit(N, "p17__virsorter2_pratama")
                  + e3_unit(S, "p11__vibrant_pratama", int(sept_n["p16__vibrant_pratama"]))
                  + e3_unit(S, "p13__genomad_pratama", int(sept_n["p18__genomad_pratama"])),
    "A3_hybrid_spades": e3_unit(N, "p07__split_hybrid_contigs_pratama", 17)
                        + sum(e3_unit(N, s) for s in ["p10__deepvirfinder_pratama", "p13__vibrant_pratama",
                                                       "p14__virsorter2_pratama", "p15__genomad_pratama"]),
    "A4_spades_noec": computed(N, ["p09__splitContigsForAmr", "p12__deepvirfinder_pratama", "p19__vibrant_pratama",
                                   "p20__virsorter2_pratama", "p21__genomad_pratama"]),
    "A5_hybrid_spades_noec": computed(N, ["p07__split_hybrid_contigs_pratama", "p10__deepvirfinder_pratama",
                                          "p13__vibrant_pratama", "p14__virsorter2_pratama", "p15__genomad_pratama"]),
    "A6_opera_ms": computed("osU8IP4o", ["p08__split_hybrid_contigs_pratama"] + callers(13))
                   + computed("1DdONH9q", ["p08__split_hybrid_contigs_pratama"] + callers(13)),
    # The relaunch recomputed DVF under the 2 Mbp guard, so only its DVF counts.
    "A7A8_flye_polca": r4_unit("p07__split_hybrid_contigs_pratama", 17) + r4_unit("p11__vibrant_pratama", 29)
                       + r4_unit("p12__virsorter2_pratama", 29) + r4_unit("p13__genomad_pratama", 29)
                       + computed("wdiikdGR", ["p09__deepvirfinder_pratama"]),
}

TAIL_R0 = [f"p{i}__{s}" for i, s in zip(range(22, 35), [
    "merge_candidate_calls_pratama", "split_viral_contigs_pratama", "contig_length_table", "pratama_votu_recovery",
    "checkv_batch_pratama", "curate_trim_batch_pratama", "checkv_merge_pratama", "curate_merge_pratama",
    "mmseqs_votu_pratama", "votu_representatives_pratama", "genomad_island_annotate_pratama", "island_filter_pratama",
    "final_votu_recovery_pratama"])]


def tail_steps(first, merge="merge_candidate_calls_pratama_nospades"):
    names = [merge] + [s.split("__")[1] for s in TAIL_R0[1:]]
    return [f"p{first + k:02d}__{n}" for k, n in enumerate(names)]


tail = {
    "R0": round(sum(e3_unit(N, s, int(sept_n[s])) for s in TAIL_R0), 1),
    "R1": computed(N, TAIL_R0),
    "R2": computed("arThlxPI", tail_steps(16)),
    "R3": computed("osU8IP4o", tail_steps(17)),
    "R4": computed("wdiikdGR", tail_steps(17)),
}

SETS = {"R0": ["A1_spades", "A2_megahit", "A3_hybrid_spades"],
        "R1": ["A4_spades_noec", "A2_megahit", "A5_hybrid_spades_noec"],
        "R2": ["A2_megahit", "A5_hybrid_spades_noec"],
        "R3": ["A2_megahit", "A6_opera_ms"],
        "R4": ["A2_megahit", "A7A8_flye_polca"]}

out = {"units": {"qc": round(qc, 1), "assembly": assembly, "viral": {k: round(v, 1) for k, v in viral.items()},
                 "tail": tail}, "proxied": coverage_gaps, "rungs": {}}
for rung, sets in SETS.items():
    asm = sum(assembly[s] for s in sets)
    vir = sum(viral[s] for s in sets) + tail[rung]
    out["rungs"][rung] = {"sets": sets, "qc": round(qc, 1), "assembly": round(asm, 1), "viral": round(vir, 1),
                          "total": round(qc + asm + vir, 1)}

ab = sa[sa.run.isin(ABLATION_RUNS) & (sa.start >= "2026-10-05")]
out["ablation_spent"] = {"all_attempts": round(ab.cpu_h.sum(), 1),
                         "failed_or_cancelled": round(ab[ab.state != "COMPLETED"].cpu_h.sum(), 1),
                         "r4_dvf_megahit_recompute": computed("wdiikdGR", ["p10__deepvirfinder_pratama"])}
print(json.dumps(out, indent=1))
(HERE / "cpu.json").write_text(json.dumps(out, indent=1))

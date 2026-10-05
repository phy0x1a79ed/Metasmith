#!/usr/bin/env python3
"""E5's viral lane on several finished assemblies of the same Pratama hybrid samples, one study each.

Asks whether Flye + POLCA finds fewer viruses than hybrid metaSPAdes or different ones. Every arm's
assembly is a given `sequences::assembly` under its own study and read_metadata, so the per-study merge
and the vOTU clustering never pool two arms or two samples, and every arm runs the same plan: E5's
callers, CheckV, curation, MMseqs2 vOTUs, the 5 kb cut and the island filter, from e5.build_transforms
for the hybrid shape of batch 3.

Arms (all read-only inputs staged on fir):
  flye_polca     Flye + POLCA
  spades_hybrid  E3's hybrid metaSPAdes 3.15.5
  opera          E5 pilot OPERA-MS
  flye           unpolished Flye (not run by default)

Subcommands: list, import [--arms ...], run [--arms ...] [--dag] [--stage-only|--launch|--materialise] [--import].
"""

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CACHE_DIR = Path(os.environ.get("E5VOTU_CACHE_DIR", HERE / ".cache" / "e5_votu_arms"))

import _common as c  # noqa: E402
import e5  # noqa: E402
from metasmith.python_api import DataInstanceLibrary, TargetBuilder  # noqa: E402

ROOT = Path("/scratch/phyberos/bench/flye_votu")
SAMPLES = ("SRR32696698", "SRR32696707")
ARMS = {
    "flye_polca": lambda s: ROOT / s / "flye_polca.fna",
    "spades_hybrid": lambda s: (Path("/scratch/phyberos/bench/spades_noec/baseline") / f"{s}.fna"
                                if s == "SRR32696698" else ROOT / s / "spades_hybrid.fna"),
    "opera": lambda s: ROOT / s / "opera.fna",
    "flye": lambda s: ROOT / s / "flye.fna",
}
DEFAULT_ARMS = ("flye_polca", "spades_hybrid", "opera")
QUEUE_SIZE = 40
ARRAY_WIDTH = 20


def declare_givens(smith, arms, ensure):
    givens = smith.PoolGivens()
    for arm in arms:
        for s in SAMPLES:
            sid = f"{s}.{arm}"
            tags = ["e5votu", arm, s]
            ns = f"e5votu/{arm}/{s}"
            study = c.add_value(givens, f"{ns}/study", {"study": sid}, "sequences::study", tags=tags)
            meta = c.add_value(givens, f"{ns}/read_metadata",
                               {"sample": sid, "parity": "paired", "length_class": "short"},
                               "sequences::read_metadata", parents=[study], tags=tags)
            c.add_file(givens, f"{ns}/assembly", ARMS[arm](s), "sequences::assembly", parents=[meta], tags=tags)
    return c.cite(givens, CACHE_DIR / "inputs.xgdb", e5.TYPE_LIBS, ensure)


def build_targets():
    # e5.build_targets' viral half. A given cannot be a target, so the frozen set has no assembly parent;
    # it is one per study either way.
    t = TargetBuilder()
    frozen = t.Add("viromics::dereplicated_candidate_virus")
    for dtype in ("viromics::contig_length_table", "viromics::checkv_contamination",
                  "viromics::checkv_quality_summary"):
        t.Add(dtype, parents=[frozen])
    curated = t.Add("e3::curated_candidate_virus", parents=[frozen])
    t.Add("viromics::votu_cluster_table", parents=[curated])
    t.Add("e3::final_votu_representatives", parents=[curated])
    return t


def solve(args):
    arms = args.arms
    n = len(arms) * len(SAMPLES)
    print(f"=== {n} studies: {', '.join(arms)} x {', '.join(SAMPLES)}", flush=True)
    importing = args.cmd == "import"
    remote = importing or args.stage_only or args.launch or args.materialise
    smith = c.agent_for("e5", remote, CACHE_DIR / "dryrun_home")
    ensure = importing or args.import_givens or not remote
    inputs = declare_givens(smith, arms, ensure)
    pratama_globals = c.pratama_globals(smith, CACHE_DIR, ensure)
    if importing:
        print(f"the pool at {smith.home.GetPath()} holds the givens of {n} arm-samples")
        return 0

    task = smith.GenerateWorkflow(
        samples=list(inputs.AsSamples("sequences::read_metadata")),
        resources=[DataInstanceLibrary.Load(c.MLIB / "resources" / "env"),
                   DataInstanceLibrary.Load(c.MLIB / "resources" / "lib"),
                   DataInstanceLibrary.Load(c.LIBRARY / "resources" / "bench"),
                   DataInstanceLibrary.Load(c.LIBRARY / "resources" / "e5"),
                   pratama_globals],
        transforms=e5.build_transforms("hybrid", pre_e5_assembly=True),
        targets=build_targets(),
    )
    c.check_plan(task, {"sequences::study": n, "sequences::read_metadata": n, "sequences::assembly": n})
    c.print_plan(task, width=34)
    reads = sorted({i.dtype_name for i in task.plan.given if "reads" in i.dtype_name})
    assert not reads, f"the viral lane cites reads: {reads}"
    if args.dag:
        c.write_dag(task, "e5_votu_arms", CACHE_DIR)
    if remote:
        c.stage_and_run(smith, task, CACHE_DIR, args.tag or f"e5votu_{'_'.join(arms)}", stage_only=args.stage_only,
                        params=dict(executor=dict(queueSize=args.queue_size),
                                    process=dict(tries=4, array=min(ARRAY_WIDTH, args.queue_size))),
                        scaled=e5.SCALED, materialise=args.materialise,
                        on_exist="clear" if args.clear else "update")
    else:
        print(f"key={task.GetKey()} (dry run; nothing staged or submitted)")
    return 0


def cmd_list(args):
    for arm in args.arms:
        for s in SAMPLES:
            print(f"{arm:14s} {s}  {ARMS[arm](s)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("list", cmd_list), ("import", solve), ("run", solve)):
        p = sub.add_parser(name)
        p.add_argument("--arms", nargs="+", default=list(DEFAULT_ARMS), choices=list(ARMS))
        p.set_defaults(fn=fn, dag=False, stage_only=False, launch=False, materialise=False, tag=None,
                       import_givens=False, clear=False, queue_size=QUEUE_SIZE)
        if name == "run":
            p.add_argument("--dag", action="store_true")
            mode = p.add_mutually_exclusive_group()
            mode.add_argument("--stage-only", action="store_true")
            mode.add_argument("--launch", action="store_true")
            mode.add_argument("--materialise", action="store_true", help="stage, fetch every image the plan needs, stop")
            p.add_argument("--tag")
            p.add_argument("--queue-size", type=int, default=QUEUE_SIZE)
            p.add_argument("--clear", action="store_true")
            p.add_argument("--import", dest="import_givens", action="store_true",
                           help="import what the pool lacks before planning, as `import` does")
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

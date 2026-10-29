#!/usr/bin/env python3
"""Solve the proposed pipeline for Kalen's Plasmidsaurus order XQTPYV and render its DAG.

Real transforms come from the metasmith standard library; the gaps are the `crage` stubs under
`mocklib/`. Every input is DEFERRED or a small value, so nothing here touches reads: the plan is
the deliverable.

`build.sh` compiles the mock library and then runs this.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get("MSM_SRC", HERE.parents[1] / "src"))
sys.path.insert(0, str(SRC))

from metasmith.models.dag_draw import Label
from metasmith.python_api import DEFERRED, DataInstanceLibrary, Spec, record_library

MLIB = SRC / "metasmith_libraries"
MOCK = HERE / "mocklib"

# Plasmidsaurus order XQTPYV, delivered 2026-10-30: three colonies from one CRAGE transformation
# of E. coli EPI300, as whole-genome nanopore. The names are the directory names as delivered.
COLONIES = [f"XQTPYV_{i}_Colony_{i}" for i in (1, 2, 3)]

# The parent strain. getNcbiAssembly wants the name first and the accession under it.
PARENT = ("Escherichia coli EPI300", "GCF_052692645.1")

# Nanopore, median Q23 by Plasmidsaurus's own read stats. flye reads this off read_qc_stats and
# picks --nano-hq; naming the platform keeps it off the HiFi preset if a rerun's quality drifts.
PLATFORM = "ont"

# One target, not nine. A metasmith target is a slot the planner must satisfy consistently with
# every other slot, so the count multiplies the search instead of adding to it; everything the
# report requires comes out of the plan anyway.
TARGETS = ["crage::report"]


def inputs() -> DataInstanceLibrary:
    lib = DataInstanceLibrary(Path(tempfile.mkdtemp(prefix="kalen-crage-")))
    for tl in ("sequences.yml", "annotation.yml", "alignment.yml", "ncbi.yml", "ref.yml"):
        lib.AddTypeLibrary(MLIB / "data_types" / tl)
    lib.AddTypeLibrary(MOCK / "data_types" / "crage.yml")

    # One order is one experiment: the parent genome and the insertion plasmid are givens under
    # it, so every colony meets the same reference and the same construct.
    run = lib.AddValue("run_XQTPYV.txt", "Plasmidsaurus order XQTPYV", "crage::run")
    name = lib.AddValue("parent_genome.txt", PARENT[0], "ncbi::genome_name", parents={run})
    lib.AddValue("parent_accession.txt", PARENT[1], "ncbi::assembly_accession", parents={name})
    lib.AddItem(DEFERRED, "crage::insertion_plasmid", parents={run})

    for colony in COLONIES:
        meta = lib.AddValue(f"read_metadata_{colony}.json",
                            {"sample": colony, "parity": "single", "length_class": "long",
                             "long_read_platform": PLATFORM},
                            "sequences::read_metadata", parents={run})
        lib.AddItem(DEFERRED, "sequences::long_reads", parents={meta})
        # The modified-base alignment is a separate delivery from the reads, and the order as
        # delivered has neither. Deferred here so the plan says what the methylation arm needs.
        lib.AddItem(DEFERRED, "crage::modified_base_bam", parents={meta})
    return record_library(lib)


def main(out: Path) -> None:
    spec = Spec(
        input_library=inputs(),
        target_types=TARGETS,
        transform_libraries=[MLIB / "transforms" / n
                             for n in ("logistics", "assembly", "metagenomics", "functionalAnnotation", "kbase")]
                            + [MOCK / "transforms" / "crage"],
        resource_libraries=[MLIB / "resources" / "env", MLIB / "resources" / "lib"],
    )
    task = spec.Solve()
    print(f"{len(task.plan.steps)} steps, ok={task.ok}, dropped={sorted(task.plan.dropped_targets)}")
    for hint in getattr(task.plan, "hints", []) or []:
        print(f"  hint: {hint}")
    for step in task.plan.steps:
        uses = sorted({u.dtype_name for u in step.uses if not u.dtype_name.startswith(("env::", "lib::"))})
        print(f"  {step.transform.name:<32} <- {', '.join(uses)}")
    dag = task.plan.BuildDAG(given_root=False, target_sink=False)
    # Tag each transform with the library it came from, so real and mock steps read apart.
    # BuildDAG names a transform node "<order> <name>"; DagRenderer has no public relabel.
    for step in task.plan.steps:
        root = Path(step.transform_library.location).name
        dag._labels[f"{step.order} {step.transform.name}"] = Label(
            name=step.transform.name, namespace="PROPOSED" if root == "crage" else root)
    out.parent.mkdir(parents=True, exist_ok=True)
    steps = [{
        "order": step.order,
        "name": step.transform.name,
        "library": Path(step.transform_library.location).name,
        "uses": sorted({u.dtype_name for u in step.uses
                        if not u.dtype_name.startswith(("env::", "lib::"))}),
        "makes": sorted({d.dtype_name for group in step.produces for d in group}),
    } for step in task.plan.steps]
    (out.parent / "plan.json").write_text(json.dumps(
        {"ok": task.ok, "targets": TARGETS, "colonies": COLONIES,
         "parent": PARENT, "platform": PLATFORM, "steps": steps}, indent=2))
    # render() reads a dotted basename's suffix as the format, so pass the stem.
    for fmt in ("svg", "png"):
        print(dag.render(out.with_suffix(""), fmt))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results" / "kalen_crage_dag.svg")

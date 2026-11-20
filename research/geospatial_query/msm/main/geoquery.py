#!/usr/bin/env python3
"""Plan, run and publish the geoquery DAG for one AOI table: normalise, fetch every source, aggregate."""
import argparse, csv
from pathlib import Path
from metasmith.python_api import (Agent, Source, Runtime, DataInstanceLibrary,
                                  TransformInstanceLibrary, TargetBuilder)
from publish import publish, image_digest

MSM = Path(__file__).resolve().parent.parent
SOURCES = MSM.parent / "poc" / "geoquery" / "sources.tsv"
TARGETS = ["aois", "source_table", "observations_long", "features_wide", "coverage", "gaps"]


def plan(agent: Agent, aoi_table: Path, dataset: str, work: Path, sources: list[str]):
    givens = agent.PoolGivens()
    table = givens.Add(aoi_table.resolve(), "geoquery::aoi_table", name=f"{dataset}/aoi_table")
    for s in sources:
        givens.Value(f"{dataset}/source/{s}", {"adapter": s}, "geoquery::source", parents=[table])
    inputs = givens.Build(work / "inputs.xgdb",
                          type_library_paths=[MSM / "data_types" / "geoquery.yml"])

    targets = TargetBuilder()
    for t in TARGETS:
        targets.Add(f"geoquery::{t}")
    return agent.GenerateWorkflow(
        samples=list(inputs.AsSamples("geoquery::aoi_table")),
        resources=[DataInstanceLibrary.Load(MSM / "resources" / "containers"), inputs],
        transforms=[TransformInstanceLibrary.Load(MSM / "transforms" / "geoquery")],
        targets=targets,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aois", type=Path, required=True, help="AOI table, KML or GeoJSON")
    ap.add_argument("--dataset", required=True, help="dataset id, e.g. mmap_canada_mining")
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--sources", help="comma-separated subset; default every source")
    ap.add_argument("--run", action="store_true", help="stage, run and wait for the workflow")
    ap.add_argument("--timeout", type=float, default=3600, help="seconds to wait for the run")
    ap.add_argument("--publish", type=Path, help="dataset dir to publish into, e.g. data/geospatial_query/<dataset>")
    a = ap.parse_args()
    with open(SOURCES) as fh:
        sources = [r["source"] for r in csv.DictReader(fh, delimiter="\t")]
    if a.sources:
        sources = [s for s in sources if s in a.sources.split(",")]
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    agent = Agent(home=Source.FromLocal(work / "msm_home"), runtime=Runtime.DOCKER)
    if a.run:
        agent.Deploy()
    task = plan(agent, a.aois, a.dataset, work, sources)
    if not task.ok:
        raise SystemExit(f"plan failed, dropped targets: {sorted(task.plan.dropped_targets)}")
    for s in task.plan.steps:
        print(f"{Path(s.transform._path).stem:16s} x{len(s.group_by_instances)}")
    task.plan.RenderDAG(str(work / "dag"), format="svg")
    print(f"plan {task.GetKey()} -> {work}/dag.svg")
    if not a.run:
        return
    agent.StageWorkflow(task, on_exist="update")
    agent.RunWorkflow(task)
    result = agent.WaitForWorkflow(task, timeout_s=a.timeout, poll_s=10.0)
    print(f"run {result['status']} after {result['elapsed_s']:.0f}s")
    if result["status"] != "completed":
        raise SystemExit("\n".join(result["tail"]))
    results = Path(agent.GetResultSource(task).GetPath())
    missing = [t for t in TARGETS if not any((results / f"geoquery-{t}").glob("*"))]
    if missing:  # metasmith reports a run that launched nothing as completed
        raise SystemExit(f"run produced no {missing}; see {results}/_metadata/logs.latest")
    print(f"results {results}")
    if a.publish:
        uri = (MSM / "resources" / "containers" / "geoquery.oci").read_text().strip()
        n = publish(results, a.aois.resolve(), a.publish.resolve(), SOURCES, task.GetKey(), image_digest(uri))
        print(f"published {a.publish}: {n}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from metasmith.agents import Spec
from metasmith.constants import AgentPaths
from metasmith.env import Runtime
from metasmith.models.libraries import DataInstanceLibrary
from metasmith.models.remote import Source
from metasmith.models.workflow import NextflowGenContext, WorkflowTask
from metasmith.testing.pool_fixtures import pool_backed

from .conftest import _build_samples_lib, _build_transform_lib, _build_type_lib
from .test_setup_subplan import ANNOTATE, FETCH

DB = {"kind": "refdb", "name": "toy", "version": "1"}
VERSIONED_FETCH = FETCH.replace(
    "TransformInstance(protocol=protocol, model=model, group_by=src)",
    "TransformInstance(protocol=protocol, model=model, group_by=src, version='3', params={'k': 'v'})",
)


def _generate(tmp_path: Path, monkeypatch, declare: bool = True) -> str:
    types_path = _build_type_lib(tmp_path / "types.yml")
    samples = _build_samples_lib(tmp_path, types_path, n_samples=1, dtype="assembly")
    refs = DataInstanceLibrary(tmp_path / "refs.xgdb")
    refs.AddTypeLibrary(types_path, namespace="mock")
    (refs.location / "image.txt").write_text("image")
    refs.AddItem(Path("image.txt"), "mock::container", props=DB if declare else None)
    pool_backed(refs)
    refs.Save()
    tr_lib = _build_transform_lib(tmp_path / "tr", types_path, {"fetch": VERSIONED_FETCH, "annotate": ANNOTATE})
    task = Spec.SolveViews(
        samples=list(samples.AsSamples("mock::assembly")), resources=[refs],
        transforms=[tr_lib], targets=["mock::annotated"],
    )
    assert task.ok, task.plan.hints
    home = tmp_path / "home"
    monkeypatch.setattr(AgentPaths, "HOME_ROOT", home)
    monkeypatch.setattr(AgentPaths, "WORK_ROOT", home / "_ws")
    task_path = AgentPaths.to_task(task.GetKey())
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task.SaveAs(Source.FromLocal(task_path))
    staged = WorkflowTask.Load(task_path, alt_data_paths=[AgentPaths.to_data()])
    ws = task_path.parent.parent
    staged.PrepareNextflow(NextflowGenContext(
        workflow_file=AgentPaths.NXF_WORKFLOW, work_dir=ws, external_work=ws,
        home_dir=home, external_home=home, runtime=Runtime.APPTAINER,
        resources_file=AgentPaths.NXF_RES, cache_root=home / "cache",
    ))
    return (ws / AgentPaths.NXF_WORKFLOW).read_text()


def _ext(workflow: str, process: str) -> str:
    body = workflow.split(f"process {process}", 1)[1]
    return next(l for l in body.splitlines() if l.strip().startswith("ext baitan:")).strip()


def test_each_process_carries_its_declared_set(tmp_path, monkeypatch):
    wf = _generate(tmp_path, monkeypatch)
    fetch = _ext(wf, "p01__fetch")
    assert "'contract': 'fetch'" in fetch and "'version': '3'" in fetch and "'params': ['k': 'v']" in fetch
    assert "/image.txt': ['kind': 'refdb', 'name': 'toy', 'version': '1']" in fetch
    annotate = _ext(wf, "p02__annotate")
    assert "'contract': 'annotate'" in annotate and "'msm':" in annotate and "image.txt" not in annotate


def test_an_undeclared_reference_falls_back_to_the_metasmith_id(tmp_path, monkeypatch):
    fetch = _ext(_generate(tmp_path, monkeypatch, declare=False), "p01__fetch")
    assert "'msm':" in fetch and "'kind'" not in fetch


def test_declared_props_survive_the_index_yaml(tmp_path, monkeypatch):
    _generate(tmp_path, monkeypatch)
    loaded = DataInstanceLibrary.Load(tmp_path / "refs.xgdb")
    assert loaded.instance_meta[Path("image.txt")]["props"] == DB

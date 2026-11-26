from __future__ import annotations

from pathlib import Path

import pytest

from metasmith.agents import Agent, Plan, Spec, TargetBuilder
from metasmith.env import Runtime
from metasmith.models.direct_run import RunTransform
from metasmith.models.remote import Source
from metasmith.models.variadic import VariadicError
from metasmith.models.workflow import WorkflowPlan
from metasmith.testing import mock_transforms as mt

from .conftest import (
    _MOCK_TYPE_PROPERTIES, BuiltPlan, _build_samples_lib, _build_transform_lib, _build_type_lib, run_and_load,
)

BINNERS = ["metabat2", "maxbin2", "concoct"]


def _library(tmp_path: Path, binners=BINNERS):
    # `mock::bins` is the supertype every `mock::<binner>_bins` is a.
    types_path = _build_type_lib(tmp_path / "types.yml", [*_MOCK_TYPE_PROPERTIES, "bins"])
    samples = _build_samples_lib(tmp_path, types_path, n_samples=1, dtype="assembly")
    transforms = mt.variadic_aggregator("das", "mock::bins", "mock::merged", "mock::assembly")
    for b in binners:
        transforms |= mt.step_transform(b, {"asm": ("mock::assembly", [])}, f"mock::{b}_bins", "asm")
    return samples, _build_transform_lib(tmp_path / "tr", types_path, transforms)


def _plan(samples, tr_lib, targets):
    return Plan([Spec(input_library=samples, target_types=targets, sample_type="mock::assembly")], transform_libraries=[tr_lib])


def _das_reads(task) -> list[list[str]]:
    return sorted(
        sorted(u.dtype_name.split("::")[1].removesuffix("_bins") for u in s.uses if u.dtype_name.endswith("_bins"))
        for s in task.plan.steps if s.transform.name == "das"
    )


def _targets(*sets):
    tb = TargetBuilder()
    for s in sets:
        tb.Add("mock::merged", parents=[tb.Set(*(f"mock::{b}_bins" for b in s))])
    return tb


@pytest.mark.parametrize("sets, reads", [
    pytest.param([["metabat2", "maxbin2"]], [["maxbin2", "metabat2"]], id="exact-membership"),
    pytest.param([["concoct"]], [["concoct"]], id="one-member"),
    pytest.param([["metabat2", "maxbin2"], BINNERS], [["concoct", "maxbin2", "metabat2"], ["maxbin2", "metabat2"]], id="two-sets-two-steps"),
])
def test_the_aggregator_reads_exactly_its_set(tmp_path, sets, reads):
    task = _plan(*_library(tmp_path), _targets(*sets))
    assert task.ok, task.plan.dropped_targets
    assert _das_reads(task) == reads


def test_a_lineage_pin_beside_the_set_stays_a_pin(tmp_path):
    tb = TargetBuilder()
    published = tb.Add("mock::metabat2_bins")
    tb.Add("mock::merged", parents=[published, tb.Set("mock::metabat2_bins", "mock::maxbin2_bins")])
    task = _plan(*_library(tmp_path), tb)
    assert task.ok, task.plan.dropped_targets
    assert _das_reads(task) == [["maxbin2", "metabat2"]]
    assert sum(s.transform.name == "metabat2" for s in task.plan.steps) == 1


def test_a_member_nobody_makes_drops_the_target(tmp_path):
    task = _plan(*_library(tmp_path, binners=["metabat2"]), _targets(["metabat2", "maxbin2"]))
    assert not task.ok
    assert _das_reads(task) == []


def test_an_aggregate_with_no_set_is_refused(tmp_path):
    with pytest.raises(VariadicError, match="name its members as a set"):
        _plan(*_library(tmp_path), ["mock::merged"])


def test_a_member_outside_the_variadic_type_is_refused(tmp_path):
    tb = TargetBuilder()
    tb.Add("mock::merged", parents=[tb.Set("mock::bam")])
    with pytest.raises(VariadicError, match="no variadic transform"):
        _plan(*_library(tmp_path), tb)


def test_each_case_solves_with_its_own_set(tmp_path):
    samples, tr_lib = _library(tmp_path)
    task = Plan([
        Spec(input_library=samples, name="pair", target_types=_targets(["metabat2", "maxbin2"]), sample_type="mock::assembly"),
        Spec(input_library=samples, name="all", target_types=_targets(BINNERS), sample_type="mock::assembly"),
    ], transform_libraries=[tr_lib])
    assert task.ok, task.plan.dropped_targets
    by_case = {tuple(s.cases): sorted(u.dtype_name for u in s.uses if u.dtype_name.endswith("_bins"))
               for s in task.plan.steps if s.transform.name == "das"}
    assert by_case == {
        ("pair",): ["mock::maxbin2_bins", "mock::metabat2_bins"],
        ("all",): ["mock::concoct_bins", "mock::maxbin2_bins", "mock::metabat2_bins"],
    }


def _libraries(task) -> dict:
    return {lib.GetKey(): lib for lib in [*task.transform_libraries, *task.data_libraries]}


def _shape(plan) -> list:
    return [(s.transform.GetKey(), sorted(d.key for d in s.dependency_map), [u.instance_id for u in s.uses]) for s in plan.steps]


def test_a_saved_plan_reloads_each_specialized_step(tmp_path):
    task = _plan(*_library(tmp_path), _targets(["metabat2", "maxbin2"], BINNERS))
    restored = WorkflowPlan.Unpack(task.plan.Pack(), _libraries(task))
    assert _shape(restored) == _shape(task.plan)
    assert _das_reads(type(task)(ok=True, plan=restored, data_libraries=[], transform_libraries=[])) == _das_reads(task)


@pytest.mark.parametrize("corrupt, match", [
    pytest.param(lambda s: s.update(schema="v9"), "schema", id="unknown-schema"),
    pytest.param(lambda s: s["dependency_map"].update(nope=[]), "does not declare", id="unknown-dependency"),
])
def test_a_step_this_version_cannot_read_is_refused(tmp_path, corrupt, match):
    task = _plan(*_library(tmp_path), _targets(["metabat2", "maxbin2"]))
    packed = task.plan.Pack()
    (das,) = [s for s in packed["steps"] if s.get("members")]
    corrupt(das)
    with pytest.raises(ValueError, match=match):
        WorkflowPlan.Unpack(packed, _libraries(task))


def test_a_compiled_plan_runs_the_specialized_step(tmp_path, virtual_runtime):
    task = _plan(*_library(tmp_path), _targets(["metabat2", "maxbin2"]))
    _, results = run_and_load(virtual_runtime, BuiltPlan(task.plan, task.data_libraries[0], list(task.transform_libraries)))
    assert "mock::merged" in set(results.manifest.values())


@pytest.fixture
def agent_home(tmp_path) -> Path:
    home = tmp_path / "msm_home"
    (home / "lib").mkdir(parents=True)
    Agent(home=Source.FromLocal(home), runtime=Runtime.DOCKER).Save(home / "lib" / "agent.yml")
    return home


def test_a_direct_run_reads_each_member_given(tmp_path, agent_home):
    samples, tr_lib = _library(tmp_path)
    (asm,) = [p for p, t in samples.manifest.items() if t == "mock::assembly"]
    for b in ["metabat2", "maxbin2"]:
        (samples.location / f"{b}.tsv").write_text("c1\tb1\n", encoding="utf-8")
        samples.AddItem(Path(f"{b}.tsv"), f"mock::{b}_bins")
    samples.Save()
    work = tmp_path / "work"
    result = RunTransform(
        transform=tr_lib.location / "das.py", data_library=samples, work_dir=work, agent_home=agent_home,
        inputs=[("anchor", asm), ("members", Path("metabat2.tsv")), ("members", Path("maxbin2.tsv"))],
    )
    assert result.success
    (out,) = [p for p in work.iterdir() if not p.name.startswith((".", "_"))]
    assert out.read_text().split() == ["mock::maxbin2_bins", "mock::metabat2_bins"]

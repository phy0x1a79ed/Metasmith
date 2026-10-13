from __future__ import annotations

from metasmith.coms.cli import _main
from metasmith.ops import runtime as op_runtime


def _parse(*argv):
    return _main._build_parser().parse_args(["workflow", "run", *argv])


def test_workflow_run_values_land_in_their_own_parameters(monkeypatch):
    seen = {}
    monkeypatch.setattr(op_runtime, "run", lambda *a, **kw: seen.update(args=a, kwargs=kw))

    args = _parse(
        "agent.yml", "task1",
        "--preset", "slurm",
        "--params", '{"k": 1}',
        "--override", "step1=cpus:4,memory_gb:8.5",
        "--override", "step2=duration_h:2",
        "--stub-delay", "1.5",
    )
    args.func(args)

    bound = dict(zip(["agent_path", "task_key"], seen["args"]), **seen["kwargs"])
    assert bound == {
        "agent_path": "agent.yml",
        "task_key": "task1",
        "config_preset": "slurm",
        "params": {"k": 1},
        "resource_overrides": {
            "step1": {"cpus": 4, "memory_gb": 8.5},
            "step2": {"duration_h": 2.0},
        },
        "stub_delay": 1.5,
    }


def test_workflow_run_defaults_leave_optionals_unset(monkeypatch):
    seen = {}
    monkeypatch.setattr(op_runtime, "run", lambda *a, **kw: seen.update(args=a, kwargs=kw))

    args = _parse("agent.yml", "task1")
    args.func(args)

    assert seen["kwargs"].get("config_file") is None
    assert seen["kwargs"]["config_preset"] is None
    assert seen["kwargs"]["params"] is None
    assert seen["kwargs"]["resource_overrides"] is None
    assert seen["kwargs"]["stub_delay"] == 0

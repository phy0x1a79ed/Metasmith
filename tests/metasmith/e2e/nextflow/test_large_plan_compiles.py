import os
import shutil
import subprocess

import pytest

from tests.metasmith.cache._cache_harness import (
    build_samples_library,
    build_transform_library,
    build_types_library,
    build_workflow_task,
    identity_transform_code,
)
from tests.metasmith.cache.test_codegen import _stage
from tests.metasmith.e2e.nextflow.harness import host_nextflow, orchestrator_src

STEPS = 500


# The JVM caps a method at 64 KB of bytecode and Nextflow compiles a workflow
# body to one method, so a plan of under a hundred steps once failed to compile
# with MethodTooLargeException. `inspect` compiles the script and runs the body
# in preview, then exits.
def test_a_plan_of_hundreds_of_steps_compiles(tmp_path):
    if host_nextflow() is None:
        pytest.skip("no nextflow on PATH or beside this python")
    names = ["seed"] + [f"s{i}" for i in range(1, STEPS + 1)]
    types = build_types_library(tmp_path, tuple(names))
    samples = build_samples_library(tmp_path, types, count=1, input_type="seed")
    transforms = {
        f"tr{i}": identity_transform_code(f"tr{i}", names[i - 1], names[i])
        for i in range(1, STEPS + 1)
    }
    task = build_workflow_task(
        samples, build_transform_library(tmp_path / "tr", types, transforms),
        sample_type="seed", target_specs=[("last", {names[-1]})],
    )
    assert len(task.plan.steps) == STEPS
    staged = _stage(task, tmp_path)
    (staged / "lib").mkdir()
    shutil.copy(orchestrator_src(), staged / "lib" / "Orchestrator.groovy")

    done = subprocess.run(
        [str(host_nextflow()), "inspect", "workflow.nf"],
        cwd=staged, capture_output=True, text=True, timeout=600,
        env={**os.environ, "NXF_ANSI_LOG": "false"},
    )
    assert done.returncode == 0, (done.stdout + done.stderr)[-3000:]

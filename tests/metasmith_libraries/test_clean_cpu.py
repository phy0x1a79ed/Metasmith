"""CLEAN plans on CPU only in a run that opts in, and then asks for no GPU.

clean.py and clean_cpu.py both produce a clean_predictions and the planner picks between them
arbitrarily, so the marker is what keeps every plan without it on clean.py.
"""

import sys
import tempfile
from pathlib import Path

from conftest import MLIB

sys.path.insert(0, str(MLIB))
import _authoring as A  # noqa: E402
from metasmith.python_api import DEFERRED, DataInstanceLibrary, Spec, record_library  # noqa: E402


def _solve(opted_in: bool):
    lib = DataInstanceLibrary(Path(tempfile.mkdtemp(prefix="msm-clean-cpu-")))
    for t in ("sequences.yml", "annotation.yml", "env.yml"):
        lib.AddTypeLibrary(A.TYPES / t)
    lib.AddItem(DEFERRED, "sequences::orfs")
    shared = [str(lib.AddItem(DEFERRED, "annotation::clean_on_cpu"))] if opted_in else []
    return Spec(
        input_library=record_library(lib),
        sample_type="sequences::orfs",
        shared_input_paths=shared,
        target_types=["annotation::clean_cpu_predictions"],
        transform_libraries=A.transforms("functionalAnnotation"),
        resource_libraries=[A.envs(), A.MLIB / "resources" / "lib"],
    ).Solve()


def test_clean_runs_on_cpu_only_when_opted_in():
    assert not _solve(opted_in=False).ok
    steps = [s.transform for s in _solve(opted_in=True).plan.steps]
    assert [t.name for t in steps] == ["clean_cpu"]
    assert not steps[0].resources.wants_gpu

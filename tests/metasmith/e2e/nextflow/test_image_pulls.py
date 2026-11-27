# A pull step in codegen's shape, run on the host's Nextflow against the real
# Orchestrator.groovy: the steps reading its env wait for it, and the launch's
# workflow.pulls.json can skip it.

import pytest

from tests.metasmith.e2e.nextflow.harness import (
    assert_ok,
    assert_slot,
    assert_slow_task_was_slow,
    assert_started_after,
)

SAMPLES = ["s0", "s1", "s2"]
PULL_S = 6


# A step whose env has a pull starts after that pull, and a launch that finds
# the image in the store skips the pull and holds nothing back.
@pytest.mark.parametrize("pulls", [None, "[1]", "[]"])
def test_a_tool_step_waits_on_its_pull_unless_the_launch_skips_it(ws, pulls):
    ws.given("env", ["e"])
    ws.given("reads", SAMPLES)
    # A member with no `reads` lineage is named "x" by the mocks.
    ws.spec("p01", label="pulled", by="env", slow={"x": PULL_S})
    ws.spec("p02", label="out")
    if pulls is not None:
        (ws.root / "workflow.pulls.json").write_text(pulls)

    result = ws.run("pull_gate.nf")
    assert_ok(result)

    p02 = result.members("p02", set(SAMPLES))
    for s in SAMPLES:
        assert_slot(p02[s], 1, names={"env_e.txt"})
    if pulls == "[]":
        assert result.received("p01") == []
        assert "PUBLISHED" not in result.stdout
    else:
        assert_slow_task_was_slow(result, "p01", "x", PULL_S)
        for s in SAMPLES:
            assert_started_after(result, ("p02", s), ("p01", "x"))
        assert "PUBLISHED pulled" in result.stdout

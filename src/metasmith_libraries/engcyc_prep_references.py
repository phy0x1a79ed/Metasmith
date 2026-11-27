#!/usr/bin/env python3
import sys

import _authoring as A
import engcyc_metagenomics as M
from metasmith.models.workflow.setup import tool_envs
from metasmith.models.workflow.steps import PULL_TRANSFORM

NAME = "engcyc_prep_references"
DESCRIPTION = """
Fetches and builds every reference database and tool image that
engcyc_metagenomics needs, and takes no samples. Run it once on an agent before
the real run; engcyc_metagenomics then finds these products in the cache.

Its targets are engcyc_metagenomics' references case, so the two templates name
the same reference steps: the long-read lanes' references and the Metabuli database
build included. Licensed packages are left out, as in engcyc_metagenomics. The plan
summary shows the download total; the largest are iPHoP's 278 GB, the Metabuli
build's 180 GB of sources and Centrifuger's 176 GB. Each archive is deleted once its
database is built. See engcyc_metagenomics' description for each lane's size.
"""


PULLED = "env::pulled_container"


def _shift(target: dict, by: int) -> dict:
    return target | {"parents": [p + by for p in target["parents"]]} if "parents" in target else target


def reference_side(plan) -> tuple[set, list[str]]:
    # A step is reference-side when nothing it consumes descends from a sample. Returns
    # those steps, as (transform, product ids), and the products a sample-side step
    # consumes, which are the targets.
    sample_made = {str(i.path) for i in plan.given if i.dtype_name.startswith("sequences::")}
    steps, ref_made, consumed_by_samples = set(), {}, set()
    for step in sorted(plan.steps, key=lambda s: s.order):
        ins = [str(i.path) for i in step.uses]
        outs = [i for g in step.produces for i in g]
        if any(i in sample_made for i in ins):
            sample_made |= {str(i.path) for i in outs}
            consumed_by_samples |= set(ins)
        else:
            ref_made |= {str(i.path): i.dtype_name for i in outs}
            steps.add((step.transform.name, frozenset(i.instance_id for i in outs)))
    return steps, sorted({t for i, t in ref_made.items() if i in consumed_by_samples})


def image_targets(task) -> list[dict]:
    # A pull of each tool image `task` runs, as targets: each env, bound to the input that
    # holds it, anchors one pulled_container under it. A prep run then pulls on the
    # driver's host every image its paired workflow's steps need, in any case.
    targets: list[dict] = []
    for env in sorted({e.dtype_name for e in tool_envs(task)}):
        targets += [{"type": env}, {"type": PULLED, "parents": [len(targets)]}]
    return targets


def prep_for(main_template, references, name, description, rebuild):
    main = main_template.Plan()
    assert main.ok, f"{main_template.name} does not plan: {sorted(main.plan.dropped_targets)}"
    steps, targets = reference_side(main.plan)
    assert set(targets) == set(references), (
        f"{main_template.name}' samples read references its references case does not name: "
        f"missing {sorted(set(targets) - set(references))}, unread {sorted(set(references) - set(targets))}"
    )
    images = image_targets(main)
    template = M.template_for(name, rebuild=rebuild, description=description,
                              targets=references + [_shift(t, len(references)) for t in images])
    prep = template.Plan()
    assert prep.ok, f"{name} does not plan: {sorted(prep.plan.dropped_targets)}"
    pulled = {i.dtype_name for s in prep.plan.steps if s.transform.name == PULL_TRANSFORM for i in s.uses}
    assert pulled == {t["type"] for t in images[::2]}, (
        f"{name} pulls a different image set than {main_template.name} runs: "
        f"{sorted(pulled ^ {t['type'] for t in images[::2]})}"
    )
    mine, _ = reference_side(prep.plan)
    mine = {s for s in mine if s[0] != PULL_TRANSFORM}
    assert mine == steps, (
        f"{name} and {main_template.name} plan different reference steps: "
        f"only here {sorted(t for t, _ in mine - steps)}, only there {sorted(t for t, _ in steps - mine)}"
    )
    return template


def build_template(rebuild: bool = False):
    return prep_for(M.build_template(rebuild=rebuild), M.REFERENCES, NAME, DESCRIPTION, rebuild)


if __name__ == "__main__":
    A.cli(sys.modules[__name__])

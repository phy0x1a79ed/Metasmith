"""The declared set a generated process hands the baitan Nextflow executor as `task.ext.baitan`.

Every field is optional: a process with no declaration runs on its task hash, and any other
executor ignores `ext`.
"""
from __future__ import annotations

from typing import Any


def groovy_literal(v: Any) -> str:
    if isinstance(v, dict):
        if not v:
            return "[:]"
        return "[" + ", ".join(f"{groovy_literal(str(k))}: {groovy_literal(x)}" for k, x in v.items()) + "]"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(groovy_literal(x) for x in v) + "]"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"'{s}'"


def given_props(inst) -> dict[str, str]:
    """The property set an imported instance declares in its index YAML, else its metasmith id."""
    declared = inst.parent_lib.instance_meta.get(inst.path, {}).get("props")
    return dict(declared) if declared else {"msm": inst.instance_id}


def _declared_set(tr, step, given) -> dict:
    return {
        "contract": str(tr.name or tr.GetKey()),
        "version": tr.version,
        "source": tr._protocol_source_hash,
        "params": {str(k): str(v) for k, v in tr.params.items()},
        "givens": {str(inst.ResolvePath()): given_props(inst) for inst in step.uses if inst in given} if step else {},
    }


def step_declaration(step, given, steps=()) -> dict:
    """Contract, version, output-affecting params, and the declared set of each given file the step reads.

    A contract with a checker adds its metric axes and the checker's declared set, built as the plan's own
    step of the checker contract is, so the two share identity.
    """
    tr = step.transform
    decl = _declared_set(tr, step, given)
    if tr.checker is not None:
        c = tr.checker
        peer = next((s for s in steps if s.transform.name == c.contract), None)
        decl["axes"] = [
            {"name": a.name, "column": a.column or a.name, "higher_better": a.higher_better, "weight": a.weight}
            for a in tr.axes
        ]
        decl["checker"] = {
            **_declared_set(peer.transform if peer else step.transform_library.GetTransform(c.contract), peer, given),
            "script": c.script, "report": c.report, "input": c.input,
        }
    return decl


def ext_line(decl: dict) -> str:
    return f"ext baitan: {groovy_literal(decl)}"

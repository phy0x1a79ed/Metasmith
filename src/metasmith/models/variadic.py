"""Variadic requirements: specialize a transform's one-or-more slot into one slot per named member, before the solver sees it."""
from __future__ import annotations

from typing import Iterable, Sequence

from .solver import Dependency, Node, Transform


class VariadicError(ValueError):
    pass


def Specialize(tr: Transform, members: Sequence[Node]) -> tuple[Transform, list[Dependency]]:
    v = tr.variadic
    assert v is not None, f"[{tr}] has no variadic requirement"
    if not members:
        raise VariadicError(f"[{tr}] needs at least one member for its variadic requirement")
    for m in members:
        if not m.IsA(v):
            raise VariadicError(f"member {sorted(m.properties)} is not a {sorted(v.properties)}")
    props = [frozenset(m.properties) for m in members]
    if len(set(props)) != len(props):
        raise VariadicError(f"[{tr}] names one member type twice; members must be distinct types")
    members = sorted(members, key=lambda m: sorted(m.properties))

    out = Transform()
    remap: dict[Dependency, Dependency] = {}
    slots: list[Dependency] = []
    for r in tr.requires:
        parents = {remap[p] for p in r.parents}
        if r is v:
            for m in members:
                slots.append(out.AddRequirement(properties=m.properties, parents=parents))
        else:
            remap[r] = out.AddRequirement(properties=r.properties, parents=parents)
    for i, group in enumerate(tr.produces):
        if i > 0: out.NewProductGroup()
        for p in group:
            parents: set[Dependency] = set()
            for a in p.parents:
                parents |= set(slots) if a is v else {remap[a]}
            out.AddProduct(properties=p.properties, parents=parents)
    return out, slots


def SpecializeForTarget(transforms: Iterable[Transform], target: Transform, exact: bool=False) -> tuple[list[Transform], Transform]:
    """Replace each variadic transform with one specialization per target slot it can fill.

    A target slot's members are its lineage parents that are a subtype of the variadic element.
    A variadic transform no target names members for is dropped: the bare model would fill its
    product from the fixed slots alone. With `exact`, the specialization's product and the target
    slot both carry a property naming the members, so a superset step cannot fill the slot.
    """
    fixed: list[Transform] = []
    variadic: list[Transform] = []
    for tr in transforms:
        (variadic if tr.variadic is not None else fixed).append(tr)
    made: dict[str, Transform] = {}
    tag: dict[Dependency, str] = {}
    for t in target.requires:
        for tr in variadic:
            if not any(p.IsA(t) for g in tr.produces for p in g):
                continue
            members = [p for p in t.parents if p.IsA(tr.variadic)]
            if not members:
                raise VariadicError(
                    f"target {sorted(t.properties)} is made by variadic [{tr}], which needs its"
                    " members named as the target's parents"
                )
            sp, _ = Specialize(tr, members)
            if exact:
                mark = "members:" + "+".join(sorted("|".join(sorted(m.properties)) for m in members))
                sp = _with_product_property(sp, mark)
                tag[t] = mark
            made.setdefault(sp.key, sp)
    if tag:
        target = _with_requirement_properties(target, tag)
    return fixed + list(made.values()), target


def _rebuild(tr: Transform, req_extra: dict[Dependency, str], prod_extra: str|None) -> Transform:
    out = Transform()
    remap: dict[Dependency, Dependency] = {}
    for r in tr.requires:
        props = set(r.properties) | ({req_extra[r]} if r in req_extra else set())
        remap[r] = out.AddRequirement(properties=props, parents={remap[p] for p in r.parents})
    for i, group in enumerate(tr.produces):
        if i > 0: out.NewProductGroup()
        for p in group:
            props = set(p.properties) | ({prod_extra} if prod_extra else set())
            out.AddProduct(properties=props, parents={remap[a] for a in p.parents})
    return out


def _with_product_property(tr: Transform, prop: str) -> Transform:
    return _rebuild(tr, {}, prop)


def _with_requirement_properties(tr: Transform, extra: dict[Dependency, str]) -> Transform:
    return _rebuild(tr, extra, None)

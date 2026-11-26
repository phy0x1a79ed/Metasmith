"""Variadic requirements: a target names a member set, and the planner specializes the variadic slot per member before the solver sees it."""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from .solver import Dependency, Node, Transform


class VariadicError(ValueError):
    pass


TOKEN = "members:"


def SetToken(names: Iterable[str]) -> str:
    """One property naming a member set, so two sets are two types and neither subsumes the other."""
    return TOKEN + "+".join(sorted(names))


def StripToken(properties: Iterable[str]) -> set[str]:
    return {p for p in properties if not p.startswith(TOKEN)}


def Specialize(tr: Transform, members: Sequence[Node], token: str) -> tuple[Transform, dict[Dependency, Dependency]]:
    """One ordinary slot per member in place of the variadic slot; every product carries the set's token."""
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
            remap[p] = out.AddProduct(properties=set(p.properties) | {token}, parents=parents)
    return out, remap


def SpecializeForTarget(
    transforms: Iterable[Transform],
    target: Transform,
    sets: Mapping[Dependency, Sequence[Node]],
) -> list[Transform]:
    """Replace each variadic transform with one specialization per target slot whose member set it can take.

    `sets` maps a target slot to its member set; the slot must already carry the set's token.
    A variadic transform no set reaches is dropped, because the bare model would fill its product
    from the fixed slots alone.
    """
    fixed: list[Transform] = []
    variadic: list[Transform] = []
    for tr in transforms:
        (variadic if tr.variadic is not None else fixed).append(tr)
    made: dict[str, Transform] = {}
    origins: dict[Transform, tuple[Transform, dict[Dependency, Dependency]]] = {}
    for t, members in sets.items():
        tokens = [p for p in t.properties if p.startswith(TOKEN)]
        assert len(tokens) == 1, f"target slot {sorted(t.properties)} does not carry one set token"
        token = tokens[0]
        bare = Node(properties=StripToken(t.properties), parents=set())
        takers = [tr for tr in variadic
                  if any(p.IsA(bare) for g in tr.produces for p in g)
                  and all(m.IsA(tr.variadic) for m in members)]
        if not takers:
            raise VariadicError(f"no variadic transform makes {sorted(bare.properties)} from {[sorted(m.properties) for m in members]}")
        for tr in takers:
            sp, remap = Specialize(tr, members, token)
            if sp.key not in made:
                made[sp.key] = sp
                origins[sp] = (tr, remap)
    for t in target.requires:
        if t in sets: continue
        if any(p.IsA(t) for tr in variadic for g in tr.produces for p in g) \
                and not any(p.IsA(t) for tr in [*fixed, *made.values()] for g in tr.produces for p in g):
            raise VariadicError(
                f"target {sorted(t.properties)} is made only by a variadic transform; name its members as a set"
            )
    SpecializeForTarget.origins = origins
    return fixed + list(made.values())


def SpecializeInstances(transform2inst: dict, inst2trlib: dict, targets: Iterable[Transform]) -> None:
    """POC: swap each bare variadic model in the planner's maps for its specializations."""
    import dataclasses
    models = list(transform2inst)
    origins: dict = {}
    for target in targets:
        sets = getattr(target, "variadic_sets", {})
        SpecializeForTarget(models, target, sets)
        for sp, o in SpecializeForTarget.origins.items():
            if all(x.key != sp.key for x in origins):
                origins[sp] = o
    for m in models:
        if m.variadic is not None:
            del transform2inst[m]
    for sp, (bare, remap) in origins.items():
        inst = transform2inst.get(sp) or _clone(transform2inst, inst2trlib, bare, sp, remap, models)


def _clone(transform2inst, inst2trlib, bare, sp, remap, models):
    import dataclasses
    # `bare` was deleted from the map above; find its instance through the library map.
    inst = next(i for i in inst2trlib if i.model is bare)
    clone = dataclasses.replace(inst, model=sp, group_by=remap[inst.group_by])
    clone.name, clone._path, clone._key, clone._hash = inst.name, inst._path, sp.key, sp.hash
    transform2inst[sp] = clone
    inst2trlib[clone] = inst2trlib[inst]
    return clone

"""Variadic requirements: a target names a member set, and the planner specializes the variadic slot per member before the solver sees it."""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from .solver import Dependency, Node, Transform


class VariadicError(ValueError):
    pass


def SetToken(members: Iterable[Iterable[str]]) -> str:
    """One property naming a member set, so two sets are two types and neither subsumes the other."""
    names = sorted("|".join(sorted(m)) for m in members)
    return "members:" + "+".join(names)


def Specialize(tr: Transform, members: Sequence[Node]) -> Transform:
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
    token = SetToken(m.properties for m in members)

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
            out.AddProduct(properties=set(p.properties) | {token}, parents=parents)
    return out


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
    for t, members in sets.items():
        token = SetToken(m.properties for m in members)
        assert token in t.properties, f"target slot {sorted(t.properties)} does not carry its set's token"
        bare = Node(properties=set(t.properties) - {token}, parents=set())
        takers = [tr for tr in variadic
                  if any(p.IsA(bare) for g in tr.produces for p in g)
                  and all(m.IsA(tr.variadic) for m in members)]
        if not takers:
            raise VariadicError(f"no variadic transform makes {sorted(bare.properties)} from {[sorted(m.properties) for m in members]}")
        for tr in takers:
            sp = Specialize(tr, members)
            made.setdefault(sp.key, sp)
    for t in target.requires:
        if t in sets: continue
        if any(p.IsA(t) for tr in variadic for g in tr.produces for p in g) \
                and not any(p.IsA(t) for tr in fixed for g in tr.produces for p in g):
            raise VariadicError(
                f"target {sorted(t.properties)} is made only by a variadic transform; name its members as a set"
            )
    return fixed + list(made.values())

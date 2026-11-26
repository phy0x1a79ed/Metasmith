"""Variadic requirements: a target names a member set, and the planner specializes the variadic slot per member before the solver sees it."""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Mapping, Sequence

from .solver import Dependency, Endpoint, Node, Transform

if TYPE_CHECKING:
    from .libraries import TransformInstance, TransformInstanceLibrary


class VariadicError(ValueError):
    pass


TOKEN = "members:"


def SetToken(names: Iterable[str]) -> str:
    """One property naming a member set, so two sets are two types and neither subsumes the other."""
    return TOKEN + "+".join(sorted(names))


def StripToken(properties: Iterable[str]) -> set[str]:
    return {p for p in properties if not p.startswith(TOKEN)}


def _token(slot: Dependency) -> str:
    tokens = [p for p in slot.properties if p.startswith(TOKEN)]
    assert len(tokens) == 1, f"target slot {sorted(slot.properties)} does not carry one set token"
    return tokens[0]


def Specialize(tr: Transform, members: Sequence[Node], token: str) -> tuple[Transform, dict[Dependency, Dependency], list[Dependency]]:
    """One ordinary slot per member in place of the variadic slot; every product carries the set's token.

    Returns the specialized model, the map from each other bare dependency to its copy, and the member slots in member order.
    """
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
            slots = [out.AddRequirement(properties=m.properties, parents=parents) for m in members]
        else:
            remap[r] = out.AddRequirement(properties=r.properties, parents=parents)
    for i, group in enumerate(tr.produces):
        if i > 0: out.NewProductGroup()
        for p in group:
            parents: set[Dependency] = set()
            for a in p.parents:
                parents |= set(slots) if a is v else {remap[a]}
            remap[p] = out.AddProduct(properties=set(p.properties) | {token}, parents=parents)
    return out, remap, slots


def _makes(tr: Transform, t: Node) -> bool:
    return any(p.IsA(t) for g in tr.produces for p in g)


def SpecializeCases(
    sets_by_case: Sequence[Mapping[Dependency, Sequence[Endpoint]]],
    targets: Sequence[Transform],
    transform2inst: dict[Transform, TransformInstance],
    inst2trlib: dict[TransformInstance, TransformInstanceLibrary],
) -> list[list[Transform]]:
    """Swap every bare variadic model in the planner's maps for the specializations the cases' member sets ask for.

    Returns, per case, the models that case may solve with: every fixed model plus that case's own specializations.
    Equal specializations across cases are one instance. A bare variadic model never reaches the solver, because it
    would fill its product from the fixed slots alone.
    """
    bare = [i for m, i in transform2inst.items() if m.variadic is not None]
    for i in bare:
        del transform2inst[i.model]
    fixed = list(transform2inst)
    made: dict[str, TransformInstance] = {}
    per_case: list[list[Transform]] = []
    for sets, target in zip(sets_by_case, targets):
        own: dict[str, TransformInstance] = {}
        for slot, members in sets.items():
            token = _token(slot)
            want = Node(properties=StripToken(slot.properties), parents=set())
            takers = [i for i in bare if _makes(i.model, want) and all(m.IsA(i.model.variadic) for m in members)]
            if not takers:
                raise VariadicError(f"no variadic transform makes {sorted(want.properties)} from {[sorted(m.properties) for m in members]}")
            for i in takers:
                sp = i.Specialized(members, token)
                own[sp.GetKey()] = made.setdefault(sp.GetKey(), sp)
        models = fixed + [i.model for i in own.values()]
        for t in target.requires:
            if t in sets: continue
            if any(_makes(i.model, t) for i in bare) and not any(_makes(m, t) for m in models):
                raise VariadicError(f"target {sorted(t.properties)} is made only by a variadic transform; name its members as a set")
        per_case.append(models)
    for sp in made.values():
        transform2inst[sp.model] = sp
        inst2trlib[sp] = inst2trlib[sp.bare]
    return per_case

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from ..models.libraries import Resources, TransformInstance

@dataclass(frozen=True)
class TargetSet:
    """A member set: one parent that fills a variadic requirement, one element per type."""
    dtype_names: tuple[str, ...]

@dataclass(frozen=True)
class TargetSpec:
    dtype_name: str
    parents: tuple["TargetSpec|TargetSet", ...] = ()

    @property
    def members(self) -> tuple[str, ...]:
        return next((p.dtype_names for p in self.parents if isinstance(p, TargetSet)), ())

class TargetBuilder:
    def __init__(self) -> None:
        self._items: list[TargetSpec] = []

    def Add(self, target_type: str, parents: Iterable[TargetSpec]|None=None) -> TargetSpec:
        assert "::" in target_type, f'expected @type to in the form of "namespace::type_name" but got [{target_type}]'
        parents = tuple(parents or ())
        for p in parents:
            assert isinstance(p, (TargetSpec, TargetSet)), (
                f'target [{target_type}] was given [{p!r}] as a parent, which is'
                ' a type name rather than a handle. Parents are the TargetSpec'
                ' values Add returns; pass the handle you got back from the'
                " parent's own Add."
            )
        assert sum(isinstance(p, TargetSet) for p in parents) <= 1, f"target [{target_type}] names more than one member set"
        spec = TargetSpec(target_type, parents)
        for existing in self._items:
            assert existing != spec, f'target [{target_type}] with identical parents already added'
        self._items.append(spec)
        return spec

    def Set(self, *dtype_names: str) -> TargetSet:
        assert dtype_names, "a member set has at least one member"
        assert len(set(dtype_names)) == len(dtype_names), f"a member set names a type twice: {dtype_names}"
        return TargetSet(tuple(sorted(dtype_names)))

    def AddAll(self, target_types: Iterable[str|dict]) -> list[TargetSpec]:
        specs: list[TargetSpec] = []
        for i, target in enumerate(target_types):
            if isinstance(target, str):
                name, parents = target, ()
            else:
                name = target.get("type")
                assert name, f"target #{i + 1} has no type"
                parents = tuple(target.get("parents") or ())
            handles = []
            for p in parents:
                assert isinstance(p, int) and 0 <= p < len(specs), (
                    f"target #{i + 1} [{name}] names parent #{p + 1 if isinstance(p, int) else p}, "
                    f"which is not one of the {len(specs)} target(s) declared before it"
                )
                handles.append(specs[p])
            if not isinstance(target, str) and target.get("set"):
                handles.append(self.Set(*target["set"]))
            specs.append(self.Add(name, parents=handles or None))
        return specs

    def Pack(self) -> list[str|dict]:
        """The `AddAll` form: a bare name, or a dict with parent indices and a member set."""
        index = {s: i for i, s in enumerate(self._items)}
        out: list[str|dict] = []
        for s in self._items:
            parents = [index[p] for p in s.parents if isinstance(p, TargetSpec)]
            if not parents and not s.members:
                out.append(s.dtype_name)
                continue
            d: dict = {"type": s.dtype_name}
            if parents: d["parents"] = parents
            if s.members: d["set"] = list(s.members)
            out.append(d)
        return out

    def resolve(self) -> list[TargetSpec]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

ResourceOverrides = dict[int|Literal["all"]|Literal["*"]|str|TransformInstance, Resources]

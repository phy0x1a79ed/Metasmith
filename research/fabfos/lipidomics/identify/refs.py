"""Loader for the cited lipid-class reference tables in `identify/refs/`.

These tables replace three hard-coded dictionaries that used to live at the top of
membrane.py. The mapping from lipid class to "is it a membrane lipid" and "does it
force curvature" is pure literature, and it should read that way: every non-
abstaining row names the citation that licenses it, and the citation travels with
the call instead of sitting in a comment.

Four tables, each answering a different question:

  lipid_class_reference.tsv      per subclass -- category, membrane gate, curvature,
                                 chain count, and whether E. coli makes it at all
  headgroup_group_curvature.tsv  per four-way MS/MS mass-balance group -- a weaker
                                 claim than the above, deliberately, because mass
                                 balance cannot resolve PE from PC or PA from PI
  facility_class_crosswalk.tsv   MetaboScape/RefMet names against the reference
                                 vocabulary
  citations.tsv                  citation keys resolved to full references

Everything here is derived, cached, and read-only; nothing writes back.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

REFS_DIR = Path(__file__).resolve().parent / "refs"

# Categories the facility uses that hold no class in the reference vocabulary.
# Their gate is settled anyway -- neither is a membrane lipid -- so they are stated
# here rather than being given fake rows in a table of MS2Lipid subclasses.
EXTRA_CATEGORY_MEMBRANE = {"Polyketides": "no", "Saccharolipids": "no"}


@lru_cache(maxsize=None)
def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(REFS_DIR / name, sep="\t", comment="#")


def classes() -> pd.DataFrame:
    """Per-subclass reference table, indexed by class."""
    return _read("lipid_class_reference.tsv").set_index("class")


def group_curvature() -> pd.DataFrame:
    """Per-headgroup-group curvature, indexed by group."""
    return _read("headgroup_group_curvature.tsv").set_index("headgroup_group")


def citations() -> pd.DataFrame:
    return _read("citations.tsv").set_index("key")


def cite(keys: str) -> str:
    """Resolve a `;`-separated citation_key field to full references."""
    c = citations()
    return " | ".join(c.citation.get(k, f"<unknown key {k}>")
                      for k in str(keys).split(";") if k)


def facility_crosswalk() -> dict[str, str]:
    x = _read("facility_class_crosswalk.tsv")
    return dict(zip(x.facility_class, x["class"]))


# ----------------------------------------------------- views keyed by facility class
def _by_facility(column: str) -> dict[str, str]:
    ref, x = classes(), facility_crosswalk()
    out = {}
    for fac, cls in x.items():
        if cls in ref.index:
            v = ref.loc[cls, column]
            if isinstance(v, str) and v not in ("abstain", "NA"):
                out[fac] = v
    return out


def membrane_by_facility_class() -> dict[str, str]:
    """Facility class -> yes/no. `abstain` rows are omitted, so a lookup miss and
    a deliberate abstain are the same thing to the caller -- which is correct,
    because both mean "this table does not settle it"."""
    return _by_facility("membrane")


def group_by_facility_class() -> dict[str, str]:
    return _by_facility("headgroup_group")


def lyso_facility_classes() -> set[str]:
    """Single-chain glycerolipids and glycerophospholipids.

    Restricted to those two categories on purpose: a cholesteryl ester also
    carries one acyl chain, but calling it "lyso" would be a category error.
    """
    ref, x = classes(), facility_crosswalk()
    cats = {"Glycerophospholipids", "Glycerolipids"}
    return {fac for fac, cls in x.items()
            if cls in ref.index
            and ref.loc[cls, "n_chains"] == 1
            and ref.loc[cls, "lipid_maps_category"] in cats}


def membrane_by_super_class() -> dict[str, str]:
    """LIPID MAPS category -> yes/no, as the facility spells the category.

    Sphingolipids are absent by construction: the category holds sphingomyelin,
    which is a phospholipid, and ceramides, which are not, so it does not settle
    the gate. E. coli makes neither.
    """
    ref = classes()
    out = dict(EXTRA_CATEGORY_MEMBRANE)
    for cat, sub in ref.groupby("lipid_maps_category"):
        vals = set(sub.membrane)
        if vals <= {"yes"} or vals <= {"no"}:
            out[cat] = vals.pop()
    return out


def curvature_by_group(prior: bool = False) -> dict[str, str]:
    g = group_curvature()
    return g["curvature_prior" if prior else "curvature_strict"].to_dict()

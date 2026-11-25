"""The frozen capsule families and the pilot draw. PROTOCOL.md states the rules.

    python3 split.py        print the split as JSON
"""
from __future__ import annotations

import json
import random

# Assigned from question text on 2026-11-24, before any agent run. Do not revise.
FAMILIES = {
    "tabular": "2 6 7 8 10 14 16 17 18 19 20 29 37 39 41 42 47 51 52 54",
    "expression": "1 3 5 9 13 22 24 26 27 30 31 32 33 36 43 46 49 53",
    "phylogenetics": "4 11 12 21 25 28 34 35 38 45 55 56 57 58 60",
    "reads": "61",
}
FAMILY = {f"bix-{n}": family for family, numbers in FAMILIES.items() for n in numbers.split()}

SEED = 20261125
STRATA = {"tabular": (["tabular"], 3), "expression": (["expression"], 3), "heavy_tool": (["phylogenetics", "reads"], 2)}


def number(capsule: str) -> int:
    return int(capsule.split("-")[1])


def pilot() -> list[str]:
    rng = random.Random(SEED)
    drawn = []
    for families, k in STRATA.values():
        pool = sorted((c for c, f in FAMILY.items() if f in families), key=number)
        drawn += rng.sample(pool, k)
    return sorted(drawn, key=number)


PILOT = pilot()
CONFIRMATORY = sorted(set(FAMILY) - set(PILOT), key=number)

if __name__ == "__main__":
    print(json.dumps({"seed": SEED, "pilot": {c: FAMILY[c] for c in PILOT},
                      "confirmatory": {c: FAMILY[c] for c in CONFIRMATORY}}, indent=1))

"""Correct family assignments the catalogue reconciliation got wrong, in place. Safe to re-run."""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

# A module filed against layer_families.md: extraction belongs to infrastructure & industry.
MODULE_FAMILY = {"nrcan_900a": "infrastructure"}

# An adapter whose features describe a different subject than its module's family.
# Rule 3 puts glaciers in geology; a vegetation index is macrobiology even inside the MODIS bundle.
ADAPTER_FAMILY = {"natural_earth_10m": "geology", "modis_13q1": "macrobiology", "nrcan_900a": "infrastructure"}


def rewrite(name: str, fix) -> None:
    path = HERE / name
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = reader.fieldnames, [fix(r) or r for r in reader]
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def by_module(key: str):
    def fix(r):
        if r[key] in MODULE_FAMILY:
            r["family"] = MODULE_FAMILY[r[key]]
    return fix


def by_adapter(r):
    if r["adapter"] in ADAPTER_FAMILY:
        r["family"] = ADAPTER_FAMILY[r["adapter"]]


def main() -> None:
    rewrite("layer_inventory.csv", by_module("module"))
    rewrite("catalogue_reconciliation.csv", by_module("module_id"))
    rewrite("source_registry.csv", by_adapter)
    rewrite("feature_values_long.csv", by_adapter)


if __name__ == "__main__":
    main()

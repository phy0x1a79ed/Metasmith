"""Fold a single-source CAM re-run (poc.py wikimedia_commons) back into the lane's poc_values.csv and poc_status.csv."""
from pathlib import Path

import pandas as pd

POC = Path(__file__).resolve().parents[2] / "probes" / "CAM" / "poc"
SRC = "wikimedia_commons"

for kind in ("values", "status"):
    whole = pd.read_csv(POC / f"poc_{kind}.csv", dtype=str)
    part = pd.read_csv(POC / f"poc_{kind}.{SRC}.csv", dtype=str)
    out = pd.concat([whole[whole.source != SRC], part], ignore_index=True)
    out.to_csv(POC / f"poc_{kind}.csv", index=False)
    print(kind, len(whole), "->", len(out))

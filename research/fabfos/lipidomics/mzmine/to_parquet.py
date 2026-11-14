"""Convert per-injection MZmine outputs into partitioned Parquet: ions/, ms2/ and injections.parquet."""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

META_CSV = Path(__file__).resolve().parents[1] / "metadata.csv"

ION_COLS = {
    "id": "ion_id", "mz": "mz", "mz_range:min": "mz_min", "mz_range:max": "mz_max",
    "rt": "rt", "rt_range:min": "rt_min", "rt_range:max": "rt_max", "fwhm": "fwhm",
    "asymmetry_factor": "asymmetry", "tailing_factor": "tailing",
    "ion_mobility": "mobility", "ion_mobility_range:min": "mobility_min",
    "ion_mobility_range:max": "mobility_max", "ccs": "ccs", "charge": "charge",
    "height": "height", "area": "area", "isotopes": "isotopes", "fragment_scans": "n_ms2",
}


def read_ions(csv: Path) -> pd.DataFrame:
    raw = pd.read_csv(csv)
    per_file = {c.split(":", 2)[2]: c for c in raw.columns if c.startswith("datafile:")}
    df = pd.DataFrame({new: raw[per_file.get(old, old)] for old, new in ION_COLS.items()
                       if per_file.get(old, old) in raw.columns})
    df["ccs"] = df["ccs"].where(df["ccs"] > 0)
    df["charge"] = df["charge"].astype("Int8")
    df["n_ms2"] = df["n_ms2"].fillna(0).astype("int32")
    df["isotopes"] = df["isotopes"].astype("string")
    return df


def read_mgf(mgf: Path) -> pd.DataFrame:
    rows, head, peaks = [], {}, []
    for line in mgf.read_text().splitlines():
        if line == "BEGIN IONS":
            head, peaks = {}, []
        elif line == "END IONS":
            p = np.array(peaks, dtype=float).reshape(-1, 2)
            rows.append({
                "ion_id": int(head["FEATURE_ID"]),
                "precursor_mz": float(head["PEPMASS"]),
                "ccs": float(head["CCS"]) if "CCS" in head else np.nan,
                "collision_energy": head.get("COLLISION_ENERGY"),
                "n_merged": int(head.get("MERGED_ACROSS_N_SAMPLES", 1)),
                "mz": p[:, 0], "intensity": p[:, 1],
            })
        elif "=" in line:
            k, v = line.split("=", 1)
            head[k] = v
        elif line and line[0].isdigit():
            peaks.append(line.split()[:2])
    return pd.DataFrame(rows)


def write_part(df: pd.DataFrame, root: Path, polarity: str, injection: str):
    part = root / f"polarity={polarity}" / f"injection={injection}"
    part.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), part / "part-0.parquet")


def injection_key(filename: str) -> str:
    return re.sub(r"\.d$", "", filename).replace(" ", "_")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path, help="run_per_injection.sh output (holds POS/ and NEG/)")
    ap.add_argument("out", type=Path)
    a = ap.parse_args()

    meta = pd.read_csv(META_CSV)
    meta["injection"] = meta.filename.map(injection_key)
    meta["polarity"] = meta.polarity.str.upper()

    n = []
    for csv in sorted(a.run_dir.glob("*/*_full_feature_table.csv")):
        pol, inj = csv.parent.name, csv.name.removesuffix("_full_feature_table.csv")
        ions = read_ions(csv)
        write_part(ions, a.out / "ions", pol, inj)
        mgf = csv.with_name(f"{inj}_iimn_fbmn.mgf")
        ms2 = read_mgf(mgf) if mgf.exists() else pd.DataFrame()
        if len(ms2):
            write_part(ms2, a.out / "ms2", pol, inj)
        n.append({"injection": inj, "polarity": pol, "n_ions": len(ions), "n_ms2": len(ms2)})

    inj = pd.DataFrame(n).merge(meta.drop(columns="polarity"), on="injection", how="left", validate="1:1")
    missing = inj.filename.isna().sum()
    if missing:
        raise SystemExit(f"{missing} injections have no metadata row: {inj[inj.filename.isna()].injection.tolist()}")
    inj.to_parquet(a.out / "injections.parquet", index=False)
    print(inj.groupby("polarity")[["n_ions", "n_ms2"]].sum())


if __name__ == "__main__":
    main()

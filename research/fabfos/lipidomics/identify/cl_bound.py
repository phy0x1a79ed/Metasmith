"""What would cardiolipin look like here, and how loudly is it absent?

Cardiolipin is the lipid this dataset most wants and least has. It is the bacterial
membrane's curvature engine -- dimeric, four acyl chains on one small doubly
phosphorylated head, sorted to the poles and the septum, and the classic lipid arm
of vesiculation. So its absence has to be measured rather than assumed from the fact
that the facility's deconvoluted table contains no CL row.

Two things are measured, both in negative mode where CL ionises:

  1. MS1 intensity at the exact [M-H]- mass of every CL(60:0)..CL(75:4) species,
     integrated over the lipid elution window only. The void volume carries a broad
     baseline that a whole-run integration mistakes for signal.

  2. Whether any doubly-charged anion exists at all. CL is usually seen as [M-2H]2-,
     and the facility's adduct census lists no 2- species anywhere in 2180 features
     -- which is either a real absence or a deconvolution setting. Settled here by
     looking for carbon-13 partners at +0.502 (z=2) against +1.003 (z=1) among the
     abundant ions in the lipid window.

The bound is expressed against co-eluting PG and PE species measured in the same
scans, so "not detected" becomes a ratio rather than a word.

Run:  mamba run -n lipidomics python -m identify.cl_bound     (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyteomics import mzml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

MASS = {"C": 12.0, "H": 1.007825032, "O": 15.994914620, "P": 30.97376151,
        "N": 14.003074005}
PROTON = 1.007276467
C13 = 1.003354838

TOL_DA = 0.02
LIPID_RT = (3.0, 6.0)     # where the glycerophospholipids elute in this method
CL_CARBONS = range(60, 76)
CL_DB = range(0, 5)
# Pellet is where membrane lipid lives; negative mode is where CL ionises.
PELLET_NEG = ("Clone1_P_", "Clone2_P_", "EpCC1_P_", "Epi300_P_",
              "Clone1_Tol_P_", "Clone2_Tol_P_", "EpCC1_Tol_P_", "Epi300_Tol_P_")


def cl_neutral(total_c: int, total_db: int) -> float:
    """CL(T:D) = C(T+9) H(2T-2D+6) O17 P2 -- two phosphatidates on a bridging glycerol."""
    return ((total_c + 9) * MASS["C"] + (2 * total_c - 2 * total_db + 6) * MASS["H"]
            + 17 * MASS["O"] + 2 * MASS["P"])


def pg_neutral(total_c: int, total_db: int) -> float:
    """PG(T:D) = C(T+6) H(2T-2D+11) O10 P."""
    return ((total_c + 6) * MASS["C"] + (2 * total_c - 2 * total_db + 11) * MASS["H"]
            + 10 * MASS["O"] + MASS["P"])


def pe_neutral(total_c: int, total_db: int) -> float:
    """PE(T:D) = C(T+5) H(2T-2D+10) N O8 P."""
    return ((total_c + 5) * MASS["C"] + (2 * total_c - 2 * total_db + 10) * MASS["H"]
            + MASS["N"] + 8 * MASS["O"] + MASS["P"])


def targets() -> pd.DataFrame:
    rows = []
    for c in CL_CARBONS:
        for d in CL_DB:
            m = cl_neutral(c, d)
            rows.append(dict(kind="CL", species=f"CL({c}:{d})",
                             mz1=m - PROTON, mz2=(m - 2 * PROTON) / 2))
    # Reference lipids: the abundant E. coli species that must be seen if the
    # method works at all. 33:1 and 35:1 carry the cyclopropane chains.
    for c, d in ((32, 1), (33, 1), (34, 1), (35, 1), (36, 2)):
        for kind, fn in (("PG", pg_neutral), ("PE", pe_neutral)):
            m = fn(c, d)
            rows.append(dict(kind=kind, species=f"{kind}({c}:{d})",
                             mz1=m - PROTON, mz2=(m - 2 * PROTON) / 2))
    return pd.DataFrame(rows)


def _rt_min(spec) -> float | None:
    try:
        t = spec["scanList"]["scan"][0]["scan start time"]
    except (KeyError, IndexError):
        return None
    return float(t) / 60.0 if getattr(t, "unit_info", None) == "second" else float(t)


def _files() -> list[Path]:
    out = []
    for p in sorted(common.MZML_DIR["neg"].glob("*.mzML")):
        if p.name.startswith(PELLET_NEG):
            out.append(p)
    return out


def scan_file(path: Path, tgt: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Integrate MS1 at every target m/z, and test for doubly-charged anions."""
    mz1 = tgt.mz1.to_numpy()
    mz2 = tgt.mz2.to_numpy()
    sum1 = np.zeros(len(tgt))
    sum2 = np.zeros(len(tgt))
    charge = {"n_peaks": 0, "with_z1_partner": 0, "with_z2_partner": 0}
    n_scan = 0

    for spec in mzml.read(str(path), use_index=False):
        if spec.get("ms level") != 1:
            continue
        rt = _rt_min(spec)
        if rt is None or not (LIPID_RT[0] <= rt <= LIPID_RT[1]):
            continue
        mzs = spec.get("m/z array")
        ints = spec.get("intensity array")
        if mzs is None or len(mzs) == 0:
            continue
        n_scan += 1
        for arr, acc in ((mz1, sum1), (mz2, sum2)):
            lo = np.searchsorted(mzs, arr - TOL_DA)
            hi = np.searchsorted(mzs, arr + TOL_DA)
            for i in range(len(arr)):
                if hi[i] > lo[i]:
                    acc[i] += float(ints[lo[i]:hi[i]].sum())

        # Charge-state census on this scan's strongest ions in the CL 2- window.
        k = (mzs >= 600) & (mzs <= 820)
        if k.any():
            sm, si = mzs[k], ints[k]
            top = np.argsort(-si)[:20]
            for j in top:
                charge["n_peaks"] += 1
                for delta, key in ((C13, "with_z1_partner"), (C13 / 2, "with_z2_partner")):
                    a = np.searchsorted(sm, sm[j] + delta - 0.012)
                    b = np.searchsorted(sm, sm[j] + delta + 0.012)
                    if b > a and si[a:b].max() >= 0.05 * si[j]:
                        charge[key] += 1

    out = tgt.copy()
    out["sum_1minus"] = sum1
    out["sum_2minus"] = sum2
    out["n_ms1_scans"] = n_scan
    out["run"] = path.stem
    return out, charge


def run() -> pd.DataFrame:
    tgt = targets().sort_values("mz1").reset_index(drop=True)
    files = _files()
    print(f"negative-mode pellet runs: {len(files)}")
    print(f"targets: {int((tgt.kind == 'CL').sum())} CL species + "
          f"{int((tgt.kind != 'CL').sum())} reference PG/PE\n")

    frames, charges = [], []
    for i, p in enumerate(files, 1):
        df, ch = scan_file(p, tgt)
        frames.append(df)
        charges.append({"run": p.stem, **ch})
        cl = df[df.kind == "CL"].sum_1minus.max()
        ref = df[df.kind != "CL"].sum_1minus.max()
        print(f"  [{i:2d}/{len(files)}] {p.name[:46]:<46} "
              f"CL max {cl:.2e}   PG/PE max {ref:.2e}", flush=True)

    all_df = pd.concat(frames, ignore_index=True)
    ch_df = pd.DataFrame(charges)
    common.IDENT_DIR.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(common.IDENT_DIR / "cl_bound_per_run.csv", index=False)

    agg = (all_df.groupby(["kind", "species"])
           [["sum_1minus", "sum_2minus"]].mean().reset_index())
    cl = agg[agg.kind == "CL"]
    ref = agg[agg.kind != "CL"]

    print("\n=== reference lipids, [M-H]- MS1 integral over RT "
          f"{LIPID_RT[0]}-{LIPID_RT[1]} min (mean over runs)")
    for _, r in ref.sort_values("sum_1minus", ascending=False).iterrows():
        print(f"    {r.species:<10} {r.sum_1minus:.3e}")

    print("\n=== cardiolipin, same measurement")
    print(f"    max over all 80 CL species   {cl.sum_1minus.max():.3e}"
          f"   ({cl.loc[cl.sum_1minus.idxmax()].species})")
    print(f"    median over all CL species   {cl.sum_1minus.median():.3e}")
    print(f"    spread max/median            {cl.sum_1minus.max() / cl.sum_1minus.median():.2f}x"
          "   <- a real series would be far from flat")

    strongest_ref = ref.sum_1minus.max()
    print(f"\n=== BOUND: CL max / strongest reference lipid = "
          f"{cl.sum_1minus.max() / strongest_ref:.2e}")
    print(f"           CL median / strongest reference     = "
          f"{cl.sum_1minus.median() / strongest_ref:.2e}")

    print("\n=== charge-state census, m/z 600-820, lipid elution window")
    tot = ch_df.n_peaks.sum()
    z1 = ch_df.with_z1_partner.sum()
    z2 = ch_df.with_z2_partner.sum()
    print(f"    strongest-ion observations   {tot}")
    print(f"    with a +1.003 13C partner (z=1)  {z1}  ({100 * z1 / max(tot, 1):.1f}%)")
    print(f"    with a +0.502 13C partner (z=2)  {z2}  ({100 * z2 / max(tot, 1):.1f}%)")
    print("\n    A doubly-charged anion population would show up as a nonzero z=2 rate.")
    return all_df


if __name__ == "__main__":
    run()

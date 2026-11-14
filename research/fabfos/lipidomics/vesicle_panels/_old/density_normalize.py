"""T4 — aggregate per-FOV counts to replicates, join OD600, normalize.

Writes vesicle_density.csv beside this file: one row per
(field-of-view set, strain, toluene, replicate), carrying the raw density in
particles per 1000 µm² and that density divided by the culture's OD600.

Field-of-view sets
------------------
`nonempty` — the 11 blank fields dropped. Each rep-2 acquisition ends with a
blank frame (Series006 in every folder but two); they contain zero particles at
every threshold and are acquisitions of nothing, not fields with no vesicles.
This is the primary set.

`mosaic` — additionally drops the 4 non-empty fields that were rejected by eye
when the mosaic was built. That set was assembled to pick presentable tiles, and
three of the four are the highest-count fields in clone1/R2/no-tol, so dropping
them moves that condition a long way. Both sets are reported; which one is right
is a judgement about those four images, not about the code.

On the OD normalization
-----------------------
There is no OD record from the imaging day. The ODs used here come from the
lipidomics culture set — different cultures, measured 6 days post-challenge and
transcribed from a method document forwarded 2026-07-08, against imaging dated
2026-05-22. The OD table's own header already flags that its replicate index is
*assumed* to match the lipidomics replicate index; mapping it onward to the
imaging replicate index stacks a second assumption on that one. The normalized
column is therefore a cross-experiment estimate, and is labelled as such
everywhere it appears.
"""

import csv
from pathlib import Path

import numpy as np
import pandas as pd

import sys
# Archived under _old/: vesicle_common lives one level up, and this script's
# own tables and renders belong beside it here, not in the live directory
# where the current chain writes files under the same names.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
OLD = Path(__file__).resolve().parent

from vesicle_common import EXCLUDE, PANELS, STRAINS, TOL_LEVELS

OD_CSV = PANELS.parent / "lipids" / "od_values.csv"
FOV_CSV = OLD / "fov_measurements.csv"
OUT = OLD / "vesicle_density.csv"

# Imaging labels -> the culture and treatment names used in od_values.csv.
CULTURE = {"epi300": "EPI300", "pcc1": "EpCC1", "clone1": "Clone1", "clone2": "Clone2"}
TREATMENT = {"notol": "ctrl", "tol": "tol"}
OD_REP = {"r1": 1, "r2": 2}  # the OD table's rep 3 has no imaging counterpart


def read_commented_csv(path: Path) -> pd.DataFrame:
    with path.open() as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    from io import StringIO
    return pd.read_csv(StringIO("".join(lines)))


def main() -> int:
    fov = read_commented_csv(FOV_CSV)
    od = read_commented_csv(OD_CSV)

    fov["is_blank"] = fov["n_particles"] == 0
    fov["series_idx"] = fov["series"].str.removeprefix("Series").astype(int)
    fov["mosaic_excluded"] = [
        (r.exported_dir, r.series_idx) in EXCLUDE for r in fov.itertuples()
    ]

    n_blank = int(fov["is_blank"].sum())
    n_mosaic_only = int((fov["mosaic_excluded"] & ~fov["is_blank"]).sum())
    print(f"{len(fov)} fields of view: {n_blank} blank, "
          f"{n_mosaic_only} rejected by eye but non-empty, "
          f"{len(fov) - n_blank - n_mosaic_only} retained by both rules")
    for r in fov[fov["mosaic_excluded"] & ~fov["is_blank"]].itertuples():
        print(f"    non-empty but rejected: {r.exported_dir}/{r.series} "
              f"— {r.n_particles} particles")

    od_lookup = {
        (r.culture, r.treatment, int(r.rep)): float(r.od600) for r in od.itertuples()
    }

    rows = []
    for set_name, keep in (("nonempty", ~fov["is_blank"]),
                           ("mosaic", ~fov["mosaic_excluded"])):
        sub = fov[keep]
        for strain in STRAINS:
            for tol in TOL_LEVELS:
                for rep in ("r1", "r2"):
                    g = sub[(sub.strain == strain) & (sub.tol == tol) & (sub.rep == rep)]
                    if g.empty:
                        raise RuntimeError(f"no fields left for {set_name}/{strain}/{tol}/{rep}")
                    od600 = od_lookup[(CULTURE[strain], TREATMENT[tol], OD_REP[rep])]
                    dens = float(g["per_1000um2"].mean())
                    rows.append({
                        "fov_set": set_name,
                        "strain": strain,
                        "tol": tol,
                        "rep": rep,
                        "n_fov": len(g),
                        "mean_per_1000um2": round(dens, 4),
                        "sd_per_1000um2": round(float(g["per_1000um2"].std(ddof=1)), 4)
                                          if len(g) > 1 else "",
                        "mean_particles_per_fov": round(float(g["n_particles"].mean()), 1),
                        "mean_area_fraction": round(float(g["particle_area_fraction"].mean()), 6),
                        "median_diam_nm": round(float(g["median_diam_nm"].median()), 1),
                        "od_culture": CULTURE[strain],
                        "od_treatment": TREATMENT[tol],
                        "od_rep": OD_REP[rep],
                        "od600": od600,
                        "density_per_od": round(dens / od600, 4),
                    })

    with OUT.open("w", newline="") as fh:
        fh.write(HEADER)
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    df = pd.DataFrame(rows)
    for set_name in ("nonempty", "mosaic"):
        d = df[df.fov_set == set_name]
        print(f"\n=== {set_name} ===")
        for tol in TOL_LEVELS:
            t = d[d.tol == tol].groupby("strain")["density_per_od"].mean()
            order = " > ".join(t.sort_values(ascending=False).index)
            print(f"  {tol:6s} density/OD by strain: {order}")
            for strain in STRAINS:
                r = d[(d.tol == tol) & (d.strain == strain)]
                pts = ", ".join(f"{v:.2f}" for v in r["density_per_od"])
                print(f"      {strain:7s} mean {r['density_per_od'].mean():7.2f}  reps: {pts}")

    print(f"\nwrote {OUT}  ({len(rows)} rows)")
    return 0


HEADER = (
    "# Vesicle particle density for the 22 May 2026 GUV imaging, per strain x\n"
    "# toluene x biological replicate. Written by\n"
    "# research/fabfos/lipidomics/vesicle_panels/density_normalize.py from fov_measurements.csv and\n"
    "# research/fabfos/lipidomics/od_values.csv.\n"
    "# mean_per_1000um2 is the mean across fields of view of (particles / FOV area),\n"
    "# at a fixed absolute threshold of 10/255. density_per_od divides it by od600.\n"
    "# fov_set=nonempty drops the 11 blank acquisitions; fov_set=mosaic additionally\n"
    "# drops 4 non-empty fields that were rejected by eye for the mosaic.\n"
    "# CAVEAT: the OD600 values are NOT from the imaging day. They are the\n"
    "# lipidomics culture set (6 d post-challenge, transcribed from\n"
    "# SCADC_method_Omics.docx, fwd 2026-07-08); the imaging is 2026-05-22. That\n"
    "# table already assumes its rep index matches the lipidomics rep index; using\n"
    "# it here assumes further that it matches the *imaging* rep index. Treat\n"
    "# density_per_od as a cross-experiment estimate, not a measured ratio.\n"
    "# n=2 biological replicates throughout — no significance test is warranted.\n"
)


if __name__ == "__main__":
    raise SystemExit(main())

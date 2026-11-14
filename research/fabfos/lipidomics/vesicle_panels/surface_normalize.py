"""Aggregate per-field membrane area to replicates, join OD600, normalize.

Writes vesicle_surface_area.csv beside this file: one row per
(field-of-view set, population, strain, toluene, replicate), carrying membrane
area per 1000 µm² of field and that value divided by the culture's OD600. This is
the microscopy-side analogue of lipid abundance per OD, which is the quantity
that lets the imaging and the lipidomics in this scope be compared at all.

Populations
-----------
`resolved` — particles whose measured radius is at or above the 105 nm the optics
resolve. **Primary.** Everything below that is smaller than the point-spread
function and so cannot be a real object; on the bake-off comparison set that
sub-resolution population was spatially *anti*-clustered relative to the resolved
particles and half of it peaked at a single photon count, which is what a
detector floor looks like and what a population of real dim vesicles is not.

`all` — every detection, no size cut. Carried alongside so the size cut is
visible rather than silent. It runs about 60% higher in count and roughly 40 nm
lower in median radius; the difference is the photon floor.

Field-of-view sets
------------------
`nonempty` — the blank acquisitions dropped. Each rep-2 acquisition ends with a
frame that is identically zero; those are acquisitions of nothing, not fields
with no vesicles. This is the primary set.

`mosaic` — additionally drops the non-empty fields rejected by eye when the
mosaic was built. That set was assembled to pick presentable tiles, and most of
what it drops is the highest-count fields of clone1/R2/no-tol, so dropping them
moves that condition a long way. Both sets are reported; which one is right is a
judgement about those images, not about the code.

How the mean is taken
---------------------
Per-field densities are averaged across fields, NOT computed as summed area over
summed field area. Every field here is the same size, so the two agree to within
rounding — but they would not if a field were ever dropped mid-analysis, and the
figures plot the per-field mean, so that is what the table carries.

Against the floor
-----------------
Every row carries `over_control`, its **count** density divided by the sample-free
control's. The control is a real acquisition with no sample in it that still
yields ~76 particles per 1000 µm² (see control_floor.py). A condition at or below
1.0 has not been distinguished from a blank frame, and `above_floor` marks it.
This is not a formality: the sparsest fields in this dataset sit below the
control.

The comparison is on count and NOT on area, deliberately. The control was
acquired at zoom 0.75, where one pixel spans 240 nm and the smallest measurable
radius is 136 nm — above the samples' own median of 103 nm. Its per-particle
areas therefore run about eight times high, and an area ratio against it would be
measuring the difference in sampling rather than any difference in membrane. The
control's area density is still carried, under a column name that says so, because
leaving it out would invite someone to recompute it.

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
from io import StringIO
from pathlib import Path

import pandas as pd

from segmenters import PSF_RADIUS_NM
from vesicle_common import EXCLUDE, PANELS, RESULTS, STRAINS, TOL_LEVELS

OD_CSV = PANELS.parent / "lipids" / "od_values.csv"
FOV_CSV = RESULTS / "fov_measurements.csv"
CONTROL_CSV = RESULTS / "control_floor.csv"
OUT = RESULTS / "vesicle_surface_area.csv"

# Imaging labels -> the culture and treatment names used in od_values.csv.
CULTURE = {"epi300": "EPI300", "pcc1": "EpCC1", "clone1": "Clone1", "clone2": "Clone2"}
TREATMENT = {"notol": "ctrl", "tol": "tol"}
OD_REP = {"r1": 1, "r2": 2}  # the OD table's rep 3 has no imaging counterpart

# Which columns carry each population's numbers. The same names appear in
# fov_measurements.csv and control_floor.csv, which is what lets a condition be
# divided by the floor without a per-population special case.
POPULATIONS = {
    "resolved": dict(dens="resolved_per_1000um2",
                     surf="resolved_surface_um2_per_1000um2",
                     n="n_resolved", radius="resolved_median_radius_nm"),
    "all": dict(dens="per_1000um2", surf="surface_um2_per_1000um2",
                n="n_particles", radius="median_radius_nm"),
}


def read_commented_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"{path} missing — run particle_segment.py / control_floor.py first")
    with path.open() as fh:
        return pd.read_csv(StringIO("".join(ln for ln in fh if not ln.startswith("#"))))


def main() -> int:
    fov = read_commented_csv(FOV_CSV)
    od = read_commented_csv(OD_CSV)
    ctrl = read_commented_csv(CONTROL_CSV)

    backend = fov["backend"].iloc[0]
    if fov["backend"].nunique() != 1:
        raise RuntimeError("fov_measurements.csv mixes backends; regenerate it")
    if ctrl["backend"].iloc[0] != backend:
        raise RuntimeError(
            f"control measured with {ctrl['backend'].iloc[0]} but samples with "
            f"{backend} — the floor would not be comparable")

    # Series001 is the matched-illumination control; Series002 is at 15x the
    # laser power and is not a floor. See control_floor.py.
    floor = ctrl[ctrl["series"] == "Series001"].iloc[0]

    fov["is_blank"] = fov["n_particles"] == 0
    fov["series_idx"] = fov["series"].str.removeprefix("Series").astype(int)
    fov["mosaic_excluded"] = [
        (r.exported_dir, r.series_idx) in EXCLUDE for r in fov.itertuples()
    ]

    n_blank = int(fov["is_blank"].sum())
    n_mosaic_only = int((fov["mosaic_excluded"] & ~fov["is_blank"]).sum())
    print(f"backend={backend}; {len(fov)} fields of view: {n_blank} blank, "
          f"{n_mosaic_only} rejected by eye but non-empty, "
          f"{len(fov) - n_blank - n_mosaic_only} retained by both rules")
    print(f"control floor: {floor.per_1000um2:.1f} particles/1000µm² "
          f"({floor.resolved_per_1000um2:.1f} resolved), "
          f"{floor.surface_um2_per_1000um2:.3f} µm² membrane per 1000µm²")

    od_lookup = {(r.culture, r.treatment, int(r.rep)): float(r.od600)
                 for r in od.itertuples()}

    rows = []
    for set_name, keep in (("nonempty", ~fov["is_blank"]),
                           ("mosaic", ~fov["mosaic_excluded"])):
        sub = fov[keep]
        for pop, col in POPULATIONS.items():
            dens_col, surf_col, n_col = col["dens"], col["surf"], col["n"]
            floor_dens = float(floor[dens_col])
            floor_surf = float(floor[surf_col])
            for strain in STRAINS:
                for tol in TOL_LEVELS:
                    for rep in ("r1", "r2"):
                        g = sub[(sub.strain == strain) & (sub.tol == tol)
                                & (sub.rep == rep)]
                        if g.empty:
                            raise RuntimeError(
                                f"no fields left for {set_name}/{strain}/{tol}/{rep}")
                        od600 = od_lookup[(CULTURE[strain], TREATMENT[tol], OD_REP[rep])]
                        dens = float(g[dens_col].mean())
                        surf = float(g[surf_col].mean())
                        rows.append({
                            "fov_set": set_name,
                            "population": pop,
                            "strain": strain,
                            "tol": tol,
                            "rep": rep,
                            "n_fov": len(g),
                            "mean_particles_per_fov": round(float(g[n_col].mean()), 1),
                            "mean_per_1000um2": round(dens, 4),
                            "mean_surface_um2_per_1000um2": round(surf, 5),
                            "sd_surface_um2_per_1000um2": round(
                                float(g[surf_col].std(ddof=1)), 5) if len(g) > 1 else "",
                            "median_radius_nm": round(float(g[col["radius"]].median()), 1),
                            "od_culture": CULTURE[strain],
                            "od_treatment": TREATMENT[tol],
                            "od_rep": OD_REP[rep],
                            "od600": od600,
                            "surface_um2_per_1000um2_per_od": round(surf / od600, 5),
                            "particles_per_1000um2_per_od": round(dens / od600, 4),
                            # The floor comparison is on COUNT density, not on
                            # area. The control is undersampled at zoom 0.75 and
                            # nothing in it can measure below 136 nm in radius
                            # against the samples' median of 103, so its
                            # per-particle areas run ~8x high and an area ratio
                            # against it compares sampling, not membrane.
                            "control_per_1000um2": round(floor_dens, 4),
                            "over_control": round(dens / floor_dens, 3) if floor_dens else "",
                            "above_floor": bool(dens >= floor_dens) if floor_dens else "",
                            "control_surface_um2_per_1000um2_NOT_COMPARABLE":
                                round(floor_surf, 5),
                        })

    with OUT.open("w", newline="") as fh:
        fh.write(_header(backend, floor))
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    df = pd.DataFrame(rows)
    for set_name in ("nonempty", "mosaic"):
        for pop in POPULATIONS:
            d = df[(df.fov_set == set_name) & (df.population == pop)]
            print(f"\n=== {set_name} / {pop} — membrane µm² per 1000 µm², per OD600 ===")
            for tol in TOL_LEVELS:
                t = d[d.tol == tol].groupby("strain")["surface_um2_per_1000um2_per_od"].mean()
                print(f"  {tol:6s} ranking: "
                      f"{' > '.join(t.sort_values(ascending=False).index)}")
                for strain in STRAINS:
                    r = d[(d.tol == tol) & (d.strain == strain)]
                    pts = ", ".join(f"{v:.3f}" for v in r["surface_um2_per_1000um2_per_od"])
                    flag = "" if r["above_floor"].all() else "   <- AT OR BELOW CONTROL FLOOR"
                    print(f"      {strain:7s} mean {r['surface_um2_per_1000um2_per_od'].mean():7.3f}"
                          f"  reps: {pts}{flag}")

    below = df[~df["above_floor"].astype(bool)]
    if len(below):
        print(f"\n{len(below)} of {len(df)} rows are at or below the control floor:")
        for r in below.itertuples():
            print(f"    {r.fov_set:8s} {r.population:8s} {r.strain:7s} {r.tol:5s} "
                  f"{r.rep}  over_control={r.over_control}")

    print(f"\nwrote {OUT}  ({len(rows)} rows)")
    return 0


def _header(backend: str, floor) -> str:
    return (
        "# Vesicle MEMBRANE SURFACE AREA for the 22 May 2026 GUV imaging, per strain\n"
        "# x toluene x biological replicate. Written by\n"
        "# research/fabfos/lipidomics/vesicle_panels/surface_normalize.py from fov_measurements.csv,\n"
        "# control_floor.csv and research/fabfos/lipidomics/od_values.csv.\n"
        f"# Segmentation backend: {backend} (chosen at the bake-off gate; see bakeoff/).\n"
        "# mean_surface_um2_per_1000um2 is the mean across fields of (summed 4*pi*r^2 /\n"
        "# field area). surface_um2_per_1000um2_per_od divides that by od600.\n"
        f"# population=resolved keeps particles with radius >= {PSF_RADIUS_NM:.0f} nm, the\n"
        "# limit these optics resolve, and is PRIMARY. population=all applies no size\n"
        "# cut; the difference between them is a single-photon detection floor, which\n"
        "# on the bake-off set was spatially anti-clustered relative to real particles\n"
        "# and half of which peaked at one count.\n"
        "# fov_set=nonempty drops the blank acquisitions; fov_set=mosaic additionally\n"
        "# drops non-empty fields that were rejected by eye for the mosaic.\n"
        "# FLOOR: over_control divides each COUNT density by the sample-free control\n"
        f"# acquisition's {floor.per_1000um2:.1f} particles per 1000 µm² -- a real\n"
        "# acquisition with NO SAMPLE in it, at matched laser power, gain and pinhole,\n"
        "# which still yields thousands of detections. above_floor=False means that\n"
        "# condition has NOT been distinguished from a blank frame and must not be\n"
        "# reported as a measurement. The control is at zoom 0.75 and undersampled, so\n"
        "# these ratios are lower bounds -- see control_floor.csv.\n"
        "# The floor is on COUNT, not area: at 240 nm per pixel the control cannot\n"
        "# measure a radius below 136 nm, against the samples' median of 103 nm, so its\n"
        "# per-particle areas run ~8x high. An area ratio against it would compare\n"
        "# sampling, not membrane. Its area density is carried only under\n"
        "# control_surface_um2_per_1000um2_NOT_COMPARABLE.\n"
        "# CAVEAT: radius is an APPARENT spot radius convolved with the ~211 nm\n"
        "# point-spread function; no deconvolution is applied, so surface area is an\n"
        "# UPPER BOUND. Surface area is exactly 4x projected area by algebra, so it\n"
        "# stays close to a restatement of the count.\n"
        "# CAVEAT: the OD600 values are NOT from the imaging day. They are the\n"
        "# lipidomics culture set (6 d post-challenge, transcribed from\n"
        "# SCADC_method_Omics.docx, fwd 2026-07-08); the imaging is 2026-05-22. That\n"
        "# table already assumes its rep index matches the lipidomics rep index; using\n"
        "# it here assumes further that it matches the *imaging* rep index. Treat the\n"
        "# per-OD columns as a cross-experiment estimate, not a measured ratio.\n"
        "# n=2 biological replicates throughout — no significance test is warranted.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())

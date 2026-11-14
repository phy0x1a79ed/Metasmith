"""T3 — particle detection per field of view, with a threshold sensitivity sweep.

Emits three tables beside this file:

  particles.csv.gz     one row per detected particle at the primary threshold
  fov_measurements.csv one row per field of view (count, density, size, area frac)
  threshold_sweep.csv  count per field of view at every threshold tried

On the threshold rule
---------------------
These are sparse point-source images: the median pixel is 0, the MAD is 0, and
in most fields the 99th percentile is still 0. Two consequences drove the design.

First, "a fixed multiple of per-image background" is not computable — the
background *is* zero — so the sweep runs over absolute 8-bit levels instead.

Second, per-image Otsu is unstable here. On adjacent fields of the same sample
it returns thresholds an order of magnitude apart (8 and 74 on two Epi_1
fields), because Otsu splits a histogram that is ~99% a single zero bin and the
split lands wherever the sparse tail happens to fall. It is computed and
reported for comparison, but the primary count is a fixed absolute threshold so
that a count means the same thing in every image.

On particle size
----------------
At 0.0901 µm/px the pixel is far below the optical resolution limit: a 63×/1.40
objective resolves ~250 nm at best, about 2.8 px. Detected components have a
median area of 5-12 px, i.e. they are at the point-spread function's size. The
reported diameters are therefore an upper bound on apparent spot size, not
physical vesicle diameters, and differences below ~250 nm are not resolvable.
The distribution is still informative about aggregation: merged or clumped
vesicles show up as a long upper tail.
"""

import csv
import gzip
import math
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops_table

import sys
# Archived under _old/: vesicle_common lives one level up, and this script's
# own tables and renders belong beside it here, not in the live directory
# where the current chain writes files under the same names.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
OLD = Path(__file__).resolve().parent

from vesicle_common import EXCLUDE, GRID, PANELS, series_tifs

GEOM = PANELS / "fov_geometry.csv"

# Absolute 8-bit levels for the sensitivity sweep. Background is 0, so these are
# signal levels, not offsets above a floor.
SWEEP_LEVELS = [3, 5, 10, 20, 40, 80]

# The count reported as *the* count. Mid-sweep: high enough to clear the
# single-pixel noise that dominates at level 1-3, low enough to keep the dim
# puncta that make up most of the population.
PRIMARY_LEVEL = 10

# Otsu on an all-but-empty field will still return a threshold and manufacture
# detections out of noise; never let it fall below this.
OTSU_FLOOR = 3

# Minimum particle area, in µm² so the floor means the same physical thing at
# any zoom. 0.02 µm² is ~2.5 px here, i.e. it drops 1-2 px specks and keeps
# anything of PSF size or larger.
MIN_AREA_UM2 = 0.02

CONNECTIVITY = 2  # 8-connected: diagonal touching pixels are one particle


def load_geometry() -> dict[tuple[str, str], dict]:
    rows = {}
    with GEOM.open() as fh:
        r = csv.DictReader(line for line in fh if not line.startswith("#"))
        for row in r:
            rows[(row["exported_dir"], row["series"])] = row
    if not rows:
        raise RuntimeError(f"{GEOM} is empty — run lif_geometry.py first")
    return rows


def measure(arr: np.ndarray, thr: float, um_per_px: float, min_area_px: float):
    """Label everything at or above `thr`, drop sub-floor specks, measure."""
    lab = label(arr >= thr, connectivity=CONNECTIVITY)
    if lab.max() == 0:
        return {k: np.array([]) for k in
                ("area", "centroid-0", "centroid-1", "intensity_mean",
                 "intensity_max", "intensity_sum")}
    props = regionprops_table(
        lab, intensity_image=arr,
        properties=("area", "centroid", "intensity_mean", "intensity_max"),
        extra_properties=(_intensity_sum,),
    )
    props["intensity_sum"] = props.pop("_intensity_sum")
    keep = props["area"] >= min_area_px
    return {k: v[keep] for k, v in props.items()}


def _intensity_sum(mask, intensity):
    return float(intensity[mask].sum())


def main() -> int:
    geom = load_geometry()

    particle_rows = []
    fov_rows = []
    sweep_rows = []

    for strain, rep, tol, sub in GRID:
        for idx, tif in series_tifs(sub):
            series = f"Series{idx:03d}"
            g = geom.get((sub, series))
            if g is None:
                raise RuntimeError(f"no geometry row for {sub}/{series}")
            um_per_px = float(g["um_per_px_x"])
            px_area_um2 = um_per_px * float(g["um_per_px_y"])
            fov_area = float(g["fov_area_um2"])
            min_area_px = MIN_AREA_UM2 / px_area_um2
            excluded = (sub, idx) in EXCLUDE

            arr = np.array(Image.open(tif))

            otsu_raw = float(threshold_otsu(arr)) if arr.max() > arr.min() else float("nan")
            otsu_thr = max(math.ceil(otsu_raw), OTSU_FLOOR) if arr.max() > arr.min() else OTSU_FLOOR

            base = dict(strain=strain, rep=rep, tol=tol, exported_dir=sub,
                        series=series, excluded_by_mosaic=excluded)

            for level in SWEEP_LEVELS:
                m = measure(arr, level, um_per_px, min_area_px)
                n = len(m["area"])
                sweep_rows.append(dict(base, threshold_kind="absolute",
                                       threshold=level, n_particles=n,
                                       per_1000um2=round(n / fov_area * 1000, 4)))

            m_otsu = measure(arr, otsu_thr, um_per_px, min_area_px)
            n_otsu = len(m_otsu["area"])
            sweep_rows.append(dict(base, threshold_kind="otsu",
                                   threshold=otsu_thr, n_particles=n_otsu,
                                   per_1000um2=round(n_otsu / fov_area * 1000, 4)))

            # Primary threshold: the per-particle and per-FOV tables.
            m = measure(arr, PRIMARY_LEVEL, um_per_px, min_area_px)
            areas_um2 = m["area"] * px_area_um2
            diam_nm = 2.0 * np.sqrt(areas_um2 / math.pi) * 1000.0

            for i in range(len(areas_um2)):
                particle_rows.append(dict(
                    base,
                    area_px=int(m["area"][i]),
                    area_um2=round(float(areas_um2[i]), 5),
                    equiv_diam_nm=round(float(diam_nm[i]), 1),
                    centroid_y_px=round(float(m["centroid-0"][i]), 1),
                    centroid_x_px=round(float(m["centroid-1"][i]), 1),
                    intensity_mean=round(float(m["intensity_mean"][i]), 2),
                    intensity_max=int(m["intensity_max"][i]),
                    intensity_sum=int(m["intensity_sum"][i]),
                ))

            n = len(areas_um2)
            fov_rows.append(dict(
                base,
                fov_area_um2=fov_area,
                um_per_px=um_per_px,
                threshold=PRIMARY_LEVEL,
                n_particles=n,
                per_1000um2=round(n / fov_area * 1000, 4),
                particle_area_fraction=round(float(areas_um2.sum() / fov_area), 6),
                median_diam_nm=round(float(np.median(diam_nm)), 1) if n else "",
                p90_diam_nm=round(float(np.percentile(diam_nm, 90)), 1) if n else "",
                max_diam_nm=round(float(diam_nm.max()), 1) if n else "",
                total_particle_intensity=int(m["intensity_sum"].sum()) if n else 0,
                otsu_threshold=otsu_thr,
                n_particles_otsu=n_otsu,
            ))

        done = [r for r in fov_rows if r["exported_dir"] == sub]
        counts = [r["n_particles"] for r in done]
        print(f"{sub:28s} n_fov={len(done):2d}  "
              f"particles/FOV @{PRIMARY_LEVEL}: "
              f"{min(counts)}-{max(counts)} (median {int(np.median(counts))})")

    _write(OLD / "particles.csv.gz", particle_rows, PARTICLE_HEADER)
    _write(OLD / "fov_measurements.csv", fov_rows, FOV_HEADER)
    _write(OLD / "threshold_sweep.csv", sweep_rows, SWEEP_HEADER)

    print(f"\nparticles.csv.gz     {len(particle_rows)} rows")
    print(f"fov_measurements.csv {len(fov_rows)} rows")
    print(f"threshold_sweep.csv  {len(sweep_rows)} rows")
    return 0


PARTICLE_HEADER = (
    "# One row per detected particle at a fixed absolute threshold of "
    f"{PRIMARY_LEVEL}/255,\n"
    f"# minimum area {MIN_AREA_UM2} µm², 8-connected components. Written by\n"
    "# research/fabfos/lipidomics/vesicle_panels/particle_measure.py from the exported ch00 TIFFs of the\n"
    "# 22 May 2026 GUV imaging.\n"
    "# CAVEAT: at 0.0901 µm/px the pixel is well below the ~250 nm optical\n"
    "# resolution limit. equiv_diam_nm is apparent spot size convolved with the\n"
    "# point-spread function, NOT a physical vesicle diameter. Treat the upper\n"
    "# tail as evidence of clumping, not as a size measurement.\n"
    "# excluded_by_mosaic marks fields rejected by eye when the mosaic was built;\n"
    "# they are retained here so the effect of dropping them can be measured.\n"
)

FOV_HEADER = (
    "# One row per field of view. n_particles / per_1000um2 are at the fixed\n"
    f"# absolute threshold {PRIMARY_LEVEL}/255; n_particles_otsu is the same count at\n"
    "# that field's own Otsu threshold, for comparison. Written by\n"
    "# research/fabfos/lipidomics/vesicle_panels/particle_measure.py.\n"
    "# Otsu is unstable on these images — the histogram is ~99% a single zero bin,\n"
    "# so the split lands wherever the sparse tail falls, and adjacent fields of\n"
    "# one sample can differ tenfold. Prefer the fixed threshold.\n"
)

SWEEP_HEADER = (
    "# Particle count per field of view at every threshold tried: absolute 8-bit\n"
    "# levels, plus each field's own Otsu. Background in these images is exactly\n"
    "# zero (median 0, MAD 0), so thresholds are absolute signal levels rather\n"
    "# than multiples of a background. Written by\n"
    "# research/fabfos/lipidomics/vesicle_panels/particle_measure.py.\n"
    "# This table is what makes a between-strain ranking checkable: read it to see\n"
    "# whether an ordering holds across levels or only at one.\n"
)


def _write(path: Path, rows: list[dict], header: str) -> None:
    """Gzip anything named .gz — the per-particle table is 3.3 MB plain and
    457 KB compressed, and git keeps every version of it forever."""
    if not rows:
        raise RuntimeError(f"nothing to write to {path}")
    opener = (lambda: gzip.open(path, "wt", newline="")) if path.suffix == ".gz" \
        else (lambda: path.open("w", newline=""))
    with opener() as fh:
        fh.write(header)
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())

"""Measure the sample-free control, so the floor is a number and not an opinion.

The May 2026 session includes a `Backgroundlif` acquisition with no sample in it,
taken through the same objective at the same 561 nm laser power to three
significant figures, the same HyD gain, the same 1 AU pinhole and the same line
average as every sample. Only the zoom differs. It is *not* empty: about 19% of
its pixels carry roughly one photon count, and the segmenter turns that into
thousands of particles.

That number is the detection floor of this dataset, and every density reported
elsewhere has to be read against it. Writing it into its own table rather than
into fov_measurements.csv is deliberate — it is not a sample, it is at a
different zoom, and a consumer that forgot to filter it out would silently fold a
blank acquisition into a strain mean.

Two of the acquisition's two series are measured, and only the first is a
control:

* Series001, 561 nm at 0.101% — matched to the samples' 0.111% to three figures.
  This is the comparison.
* Series002, 561 nm at 1.489% — fifteen times the illumination, so a different
  exposure entirely. Reported for completeness and NOT usable as a floor.

The undersampling caveat
------------------------
The control was acquired at zoom 0.75, so one pixel spans 240 nm against the
samples' 90 nm. Two consequences, both of which matter when reading the table:
counts per unit area are comparable, but *sizes* are not — nothing there can
measure below ~135 nm in radius, which is already above the 105 nm resolution
limit, so the resolved-only floor is not filtered the way the samples' is. That
makes every sample-over-control ratio computed against it a LOWER BOUND on the
real separation, and makes the surface-area floor an OVER-estimate.
"""

import csv

import numpy as np

from segmenters import BACKENDS, PSF_RADIUS_NM, load_field, load_geometry, segment
from vesicle_common import BACKGROUND, PANELS, RESULTS, sample_um_per_px

OUT = RESULTS / "control_floor.csv"
BACKEND = "sep"


def main() -> int:
    geom = load_geometry()
    be = BACKENDS[BACKEND]
    sample_pitch = sample_um_per_px()
    rows = []

    for sub in BACKGROUND:
        from vesicle_common import series_tifs
        for idx, tif in series_tifs(sub):
            series = f"Series{idx:03d}"
            g = geom[(sub, series)]
            ux, uy = float(g["um_per_px_x"]), float(g["um_per_px_y"])
            fov_area = float(g["fov_area_um2"])
            arr = load_field(tif)
            s = segment(arr, ux, uy, backend=BACKEND)

            rad = np.array([r["radius_nm"] for r in s.rows] or [0.0])
            surf = np.array([r["surface_area_um2"] for r in s.rows] or [0.0])
            n = len(s.rows)
            res = rad >= PSF_RADIUS_NM
            rows.append(dict(
                exported_dir=sub, series=series, backend=BACKEND,
                knob_name=be.knob_name, knob=be.knob_default,
                um_per_px=round(ux, 6),
                undersampled_vs_samples=round(ux / sample_pitch, 3),
                fov_area_um2=round(fov_area, 1),
                nonzero_fraction=round(float(np.mean(arr > 0)), 4),
                n_particles=n,
                per_1000um2=round(n / fov_area * 1000, 4),
                n_resolved=int(res.sum()) if n else 0,
                resolved_per_1000um2=round(int(res.sum()) / fov_area * 1000, 4) if n else 0.0,
                surface_um2_per_1000um2=round(float(surf.sum()) / fov_area * 1000, 5) if n else 0.0,
                resolved_surface_um2_per_1000um2=round(
                    float(surf[res].sum()) / fov_area * 1000, 5) if n else 0.0,
                median_radius_nm=round(float(np.median(rad)), 1) if n else "",
                smallest_measurable_radius_nm=round(
                    float(np.sqrt(1.0 / np.pi) * ux * 1000), 1),
            ))
            print(f"  {sub}/{series}  {n} particles  "
                  f"{rows[-1]['per_1000um2']:.1f} /1000µm²  "
                  f"({rows[-1]['resolved_per_1000um2']:.1f} resolved)  "
                  f"nonzero {rows[-1]['nonzero_fraction']:.1%}")

    with OUT.open("w", newline="") as fh:
        fh.write(HEADER)
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT} ({len(rows)} rows)")
    return 0


HEADER = (
    "# Detection floor: the sample-free control acquisition of the 22 May 2026\n"
    "# session, segmented by exactly the same call as the samples. Written by\n"
    "# research/fabfos/lipidomics/vesicle_panels/control_floor.py.\n"
    "# Series001 is the comparison -- 561 nm at 0.101% against the samples' 0.111%,\n"
    "# same objective, gain, pinhole and line average. Series002 is at 1.489%,\n"
    "# fifteen times the illumination, and is NOT a usable floor.\n"
    "# The control contains no sample and is still not empty: ~19% of Series001's\n"
    "# pixels carry about one photon count. Every density elsewhere in this\n"
    "# directory must be read against these numbers.\n"
    "# CAVEAT -- undersampling. Acquired at zoom 0.75, so one pixel spans 240 nm\n"
    "# against the samples' 90 nm (undersampled_vs_samples = 2.67). Counts per unit\n"
    "# area are comparable; SIZES ARE NOT. Nothing here can measure below\n"
    "# smallest_measurable_radius_nm, which is already above the 105 nm resolution\n"
    "# limit -- so the resolved-only floor is not filtered the way the samples' is.\n"
    "# Consequently every sample-over-control ratio is a LOWER BOUND on the true\n"
    "# separation, and the surface-area floor is an OVER-estimate.\n"
)


if __name__ == "__main__":
    raise SystemExit(main())

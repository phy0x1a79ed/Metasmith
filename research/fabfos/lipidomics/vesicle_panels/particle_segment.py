"""Measure every field with the chosen backend, into the per-particle tables.

Segmentation itself lives in segmenters.py, behind one interface with three
interchangeable backends; bakeoff.py scores them against each other and the
choice is made there, by eye and by scorecard, not here. This module is only the
driver that runs the winner over all 105 fields and writes what the normalisation
step consumes:

    particles.csv.gz       one row per particle
    fov_measurements.csv   one row per field of view
    sensitivity_sweep.csv  the same fields at every threshold on the sweep

    python particle_segment.py [backend] [knob]

Do not run this before a backend has been chosen at the gate. Which one wrote a
table is recorded in the table, in a `backend` column and in the header, because
these three do not agree — on the comparison set they differ by 30% in particle
count and by 60 nm in median radius, so a table that does not say which produced
it cannot be compared with anything.

Why the sweep table exists
--------------------------
Every backend's detection threshold collapses to zero on the ~100 fields whose
background is exactly zero, so on those fields the sweep changes nothing at all
and that is correct — there is no noise there for a threshold to reject. Where it
does move the answer is the three hazy clon1_1 fields. The table is what makes a
between-strain ranking checkable: read it to see whether an ordering holds across
thresholds or only at one.
"""

import csv
import gzip
import sys
from pathlib import Path

import numpy as np

from segmenters import (
    BACKENDS, PSF_RADIUS_NM, load_field, load_geometry, segment,
)
from vesicle_common import EXCLUDE, GRID, PANELS, RESULTS, series_tifs


def main(backend: str, knob: float | None) -> int:
    if backend not in BACKENDS:
        raise SystemExit(f"unknown backend {backend!r}; have {list(BACKENDS)}")
    be = BACKENDS[backend]
    knob = be.knob_default if knob is None else knob
    geom = load_geometry()
    particle_rows, fov_rows, sweep_rows = [], [], []
    print(f"backend={backend}  {be.knob_name}={knob:g}")

    for strain, rep, tol, sub in GRID:
        for idx, tif in series_tifs(sub):
            series = f"Series{idx:03d}"
            g = geom.get((sub, series))
            if g is None:
                raise RuntimeError(f"no geometry row for {sub}/{series}")
            ux, uy = float(g["um_per_px_x"]), float(g["um_per_px_y"])
            fov_area = float(g["fov_area_um2"])
            base = dict(strain=strain, rep=rep, tol=tol, exported_dir=sub,
                        series=series, excluded_by_mosaic=(sub, idx) in EXCLUDE,
                        backend=backend)

            arr = load_field(tif)
            s = segment(arr, ux, uy, backend=backend, knob=knob)

            for k in be.knob_sweep:
                s2 = (s if k == knob
                      else segment(arr, ux, uy, backend=backend, knob=k))
                surf = sum(r["surface_area_um2"] for r in s2.rows)
                res_rows = [r for r in s2.rows if r["radius_nm"] >= PSF_RADIUS_NM]
                res_surf = sum(r["surface_area_um2"] for r in res_rows)
                sweep_rows.append(dict(
                    base, knob_name=be.knob_name, knob=k, n_particles=len(s2.rows),
                    n_resolved=len(res_rows),
                    per_1000um2=round(len(s2.rows) / fov_area * 1000, 4),
                    resolved_per_1000um2=round(len(res_rows) / fov_area * 1000, 4),
                    surface_um2_per_1000um2=round(surf / fov_area * 1000, 5),
                    resolved_surface_um2_per_1000um2=round(res_surf / fov_area * 1000, 5),
                ))

            for r in s.rows:
                particle_rows.append(dict(base, **r))

            n = len(s.rows)
            surf = np.array([r["surface_area_um2"] for r in s.rows] or [0.0])
            radii = np.array([r["radius_nm"] for r in s.rows] or [0.0])
            proj = np.array([r["area_um2"] for r in s.rows] or [0.0])
            # The resolved population is primary: everything below the PSF radius
            # is smaller than the optics can form an image of.
            keep = radii >= PSF_RADIUS_NM
            resolved = int(keep.sum()) if n else 0
            fov_rows.append(dict(
                base,
                fov_area_um2=fov_area, um_per_px=ux,
                n_particles=n, n_detections=s.n_features, n_resolved=resolved,
                per_1000um2=round(n / fov_area * 1000, 4),
                resolved_per_1000um2=round(resolved / fov_area * 1000, 4),
                projected_area_um2=round(float(proj.sum()), 5) if n else 0.0,
                surface_area_um2=round(float(surf.sum()), 5) if n else 0.0,
                surface_um2_per_1000um2=round(float(surf.sum()) / fov_area * 1000, 5) if n else 0.0,
                resolved_surface_area_um2=round(float(surf[keep].sum()), 5) if n else 0.0,
                resolved_surface_um2_per_1000um2=round(
                    float(surf[keep].sum()) / fov_area * 1000, 5) if n else 0.0,
                median_radius_nm=round(float(np.median(radii)), 1) if n else "",
                resolved_median_radius_nm=round(float(np.median(radii[keep])), 1)
                                          if resolved else "",
                p90_radius_nm=round(float(np.percentile(radii, 90)), 1) if n else "",
                max_radius_nm=round(float(radii.max()), 1) if n else "",
                frac_below_psf=round(1.0 - resolved / n, 4) if n else "",
                background_level=round(float(np.median(arr[arr > 0])) if (arr > 0).any() else 0.0, 2),
                nonzero_fraction=round(float(np.mean(arr > 0)), 4),
            ))

        done = [r for r in fov_rows if r["exported_dir"] == sub]
        counts = [r["n_particles"] for r in done]
        print(f"{sub:28s} n_fov={len(done):2d}  particles/FOV: "
              f"{min(counts)}-{max(counts)} (median {int(np.median(counts))})")

    n_res = sum(r["n_resolved"] for r in fov_rows)
    print(f"\n{len(particle_rows)} particles, of which {n_res} "
          f"({n_res / max(1, len(particle_rows)):.1%}) are at or above the "
          f"{PSF_RADIUS_NM:.0f} nm resolution limit")

    hdr = _headers(backend, be, knob)
    _write(RESULTS / "particles.csv.gz", particle_rows, hdr[0])
    _write(RESULTS / "fov_measurements.csv", fov_rows, hdr[1])
    _write(RESULTS / "sensitivity_sweep.csv", sweep_rows, hdr[2])
    return 0


def _headers(backend, be, knob):
    common = (
        f"# Written by research/fabfos/lipidomics/vesicle_panels/particle_segment.py from the exported\n"
        f"# ch00 TIFFs of the 22 May 2026 GUV imaging.\n"
        f"# BACKEND: {backend}, {be.knob_name}={knob:g}. The three backends in\n"
        f"# segmenters.py do NOT agree -- they differ by ~30% in count and ~60 nm in\n"
        f"# median radius -- so this table is only comparable with others from the\n"
        f"# same backend at the same threshold. See bakeoff/ for the comparison.\n"
    )
    caveat = (
        f"# CAVEAT: radius_nm is an APPARENT spot radius convolved with the ~211 nm\n"
        f"# point-spread function (63x/1.40 NA, 580 nm emission, 1.0 AU pinhole), NOT a\n"
        f"# physical vesicle radius. No deconvolution is applied -- pixels at face value\n"
        f"# -- so summed surface area is an UPPER BOUND. Particles with radius_nm below\n"
        f"# {PSF_RADIUS_NM:.0f} nm are smaller than the optics can resolve and are\n"
        f"# counted separately as n_resolved / frac_below_psf; on the bake-off set that\n"
        f"# population is spatially uniform rather than clustered with the resolved\n"
        f"# particles, which is what a single-photon floor looks like and what a\n"
        f"# population of real dim vesicles would not.\n"
    )
    return (
        common + caveat +
        "# One row per detected particle. surface_area_um2 = 4*pi*r^2, which is exactly\n"
        "# four times the projected area -- a sphere in projection shows a disk of its\n"
        "# own radius, so the spherical assumption contributes a constant factor only.\n"
        "# excluded_by_mosaic marks fields rejected by eye when the mosaic was built.\n"
        "# Remaining columns are backend-specific; see segmenters.py.\n",

        common + caveat +
        "# One row per field of view. surface_area_um2 is the summed 4*pi*r^2 over the\n"
        "# field's particles; surface_um2_per_1000um2 divides it by field area.\n"
        "# n_detections is the backend's raw detection count before sizing.\n",

        common +
        "# Count and summed surface area at every threshold on this backend's own\n"
        "# sweep. On the ~100 fields whose background is exactly zero the threshold\n"
        "# collapses to zero at every level and the numbers do not move, which is\n"
        "# correct: there is no noise there for a threshold to reject. The three hazy\n"
        "# clon1_1 fields are where this table has content.\n",
    )


def _write(path: Path, rows: list[dict], header: str) -> None:
    """Gzip anything named .gz — the per-particle table is megabytes plain, and
    git keeps every version of it forever."""
    if not rows:
        raise RuntimeError(f"nothing to write to {path}")
    opener = (lambda: gzip.open(path, "wt", newline="")) if path.suffix == ".gz" \
        else (lambda: path.open("w", newline=""))
    with opener() as fh:
        fh.write(header)
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.name:24s} {len(rows)} rows")


if __name__ == "__main__":
    raise SystemExit(main(
        sys.argv[1] if len(sys.argv) > 1 else
        sys.exit("usage: particle_segment.py <backend> [knob] — pick one at the "
                 "gate first; see bakeoff/index.html"),
        float(sys.argv[2]) if len(sys.argv) > 2 else None,
    ))

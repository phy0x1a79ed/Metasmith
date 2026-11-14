"""The segmentation gate: score three backends against each other, then stop.

Runs photutils, sep and the trackpy+half-max baseline over one shared,
deliberately adversarial set of fields, computes a scorecard, and renders one SVG
overlay per backend per field so the same field can be compared backend against
backend at zoom. Nothing downstream runs until a backend is chosen.

Two things are checked, in this order, because they fail differently:

**Synthetic** — Gaussian spots of known width and varying amplitude on a known
background. All three backends report a radius that is `sqrt(2 ln 2) * sigma` for
a Gaussian (half-max radius, FWHM/2 and half-light radius all coincide there), so
there is a single right answer and an adapter wired up wrongly shows as a wrong
number rather than a plausible one. Real data cannot do this: no amount of
staring at a micrograph tells you the true radius of anything in it.

**Real fields** — five tests, all computed rather than asserted, chosen so that
the estimator that failed the first gate would fail at least one:

1. *Radius flatness.* Median radius per peak-brightness quartile, as max/min.
   The rejected estimator scored 2.0 because it sized each spot by an
   iso-intensity contour on its flank, so radius tracked photon count rather than
   size. 1.0 is ideal. The single most diagnostic number here.
2. *Blank-field false positives.* Detections on acquisitions that contain
   nothing. Anything above zero is a false-positive rate.
3. *Hazy-field behaviour.* Detections on the clon1_1 haze fields against clean
   fields of comparable true density. A backend that circles grain shows up as a
   count that explodes only where there is a background.
4. *Overlap separation.* Objects recovered on the most crowded field, and how
   each backend reports the shared pixels — the two segmentation backends
   partition them, the baseline lets both particles claim them.
5. *Knob stability.* Count and summed surface area as each tool's own detection
   threshold is swept, so a backend that only works at one setting is visible.

One derived number is reported alongside: the fraction of particles measured
*smaller than the point-spread function*. Nothing imaged through this optic can
truly be smaller than ~105 nm in half-max radius, so those rows are single-photon
events and near-threshold noise being sized as vesicles. It is not a pass/fail
test — it is the number that says how much of each backend's catalogue is
physically meaningless.
"""

import csv
import html
import math
import warnings
from pathlib import Path

import numpy as np

from segmentation_overlay import build_svg
from segmenters import (
    BACKENDS, PSF_FWHM_PX, PSF_RADIUS_NM, load_field, load_geometry, segment,
)
from vesicle_common import (
    BACKGROUND, GRID, PANELS, RESULTS, REP_LABEL, STRAIN_LABEL, TOL_LABEL,
    sample_um_per_px, series_tifs,
)

warnings.filterwarnings("ignore")

OUT = RESULTS / "bakeoff"

# The cut is in NANOMETRES, not pixels. The control acquisition is at zoom 0.75
# and the samples at zoom 2, so a pixel means 0.240 µm in one and 0.090 µm in
# the other; a cut expressed in pixels would be a 2.7x looser cut on the control
# and would make the comparison against it meaningless.


# --- synthetic ---------------------------------------------------------------
SYNTH_SIGMA_PX = PSF_FWHM_PX / (2.0 * math.sqrt(2.0 * math.log(2.0)))
SYNTH_TRUE_R_PX = SYNTH_SIGMA_PX * math.sqrt(2.0 * math.log(2.0))   # = FWHM/2
SYNTH_AMPS = [3, 8, 25, 80, 250]        # peak counts, spanning the real range
SYNTH_PER_AMP = 6
SYNTH_SPACING = 24                      # px between planted spots
SYNTH_BACKGROUNDS = [0, 5]              # the clean fields, and the hazy ones
SYNTH_SEED = 0
MATCH_TOL_PX = 3.0


def synthetic_field(amps, bg, rng):
    """Gaussian spots of the PSF's own width on a flat background, Poisson-
    sampled and rounded, because that is what a photon-counting detector
    returns. `amps` are peak counts above background."""
    side = int(math.ceil(math.sqrt(len(amps))))
    s = (side + 1) * SYNTH_SPACING
    img = np.full((s, s), float(bg))
    yy, xx = np.mgrid[0:s, 0:s]
    truth = []
    for i, a in enumerate(amps):
        cx = SYNTH_SPACING * (i % side + 1)
        cy = SYNTH_SPACING * (i // side + 1)
        img += a * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * SYNTH_SIGMA_PX ** 2))
        truth.append((cx, cy, a))
    return np.round(rng.poisson(np.clip(img, 0, None)).astype(float)), truth


def _match(rows, truth):
    """Nearest detection within MATCH_TOL_PX of each planted spot, or None."""
    out = []
    for cx, cy, a in truth:
        best = None
        for r in rows:
            d = math.hypot(r["x_px"] - cx, r["y_px"] - cy)
            if d <= MATCH_TOL_PX and (best is None or d < best[0]):
                best = (d, r)
        out.append((a, best[1] if best else None))
    return out


def run_synthetic() -> list[dict]:
    um = sample_um_per_px()
    amps = [a for a in SYNTH_AMPS for _ in range(SYNTH_PER_AMP)]
    rows = []
    print(f"SYNTHETIC — {len(amps)} Gaussian spots of sigma {SYNTH_SIGMA_PX:.3f} px; "
          f"true radius {SYNTH_TRUE_R_PX:.3f} px = {SYNTH_TRUE_R_PX * um * 1000:.1f} nm")
    for bg in SYNTH_BACKGROUNDS:
        print(f"\n  background {bg} counts (Poisson)")
        print(f"    {'backend':10s} {'knob':>6s} {'found':>7s} {'spurious':>9s} "
              + " ".join(f"{'A=' + str(a):>7s}" for a in SYNTH_AMPS)
              + f" {'flat':>6s} {'bias':>7s}")
        for name, be in BACKENDS.items():
            for knob in be.knob_sweep:
                rng = np.random.default_rng(SYNTH_SEED)
                img, truth = synthetic_field(amps, bg, rng)
                seg = segment(img, um, um, backend=name, knob=knob)
                m = _match(seg.rows, truth)
                per = {}
                for a in SYNTH_AMPS:
                    rs = [r["radius_px"] for aa, r in m if aa == a and r is not None]
                    per[a] = float(np.median(rs)) if rs else float("nan")
                found = sum(1 for _, r in m if r is not None)
                got = [v for v in per.values() if np.isfinite(v)]
                flat = max(got) / min(got) if len(got) > 1 else float("nan")
                bias = (float(np.median([r["radius_px"] for _, r in m if r is not None]))
                        / SYNTH_TRUE_R_PX) if found else float("nan")
                rows.append(dict(
                    background=bg, backend=name, knob_name=be.knob_name, knob=knob,
                    n_planted=len(truth), n_recovered=found,
                    n_spurious=len(seg.rows) - found,
                    **{f"median_radius_px_A{a}": _r(per[a], 4) for a in SYNTH_AMPS},
                    flatness=_r(flat, 3), radius_bias=_r(bias, 3),
                ))
                if knob == be.knob_default:
                    cells = " ".join(f"{per[a]:7.3f}" if np.isfinite(per[a])
                                     else f"{'--':>7s}" for a in SYNTH_AMPS)
                    print(f"    {name:10s} {knob:6g} {found:3d}/{len(truth):<3d} "
                          f"{len(seg.rows) - found:9d} {cells} {flat:6.2f} {bias:7.2f}"
                          "   <- default")
    return rows


# --- the real-field comparison set -------------------------------------------

def pick_fields(geom) -> list[dict]:
    """A small adversarial set, not a representative one.

    Chosen to break a backend: the haze fields where a detector with no noise
    model circles grain, the crowded field where deblending has to work, the
    field with the largest object where a size estimator can saturate, and blank
    acquisitions that contain nothing at all. Selection uses a single fixed
    backend so the set does not depend on which backend is being judged.
    """
    print("scanning fields to choose the comparison set ...")
    scan = []
    for strain, rep, tol, sub in GRID:
        for idx, tif in series_tifs(sub):
            arr = load_field(tif)
            g = geom[(sub, f"Series{idx:03d}")]
            s = segment(arr, float(g["um_per_px_x"]), float(g["um_per_px_y"]),
                        backend="sep")
            scan.append(dict(
                strain=strain, rep=rep, tol=tol, sub=sub,
                series=f"Series{idx:03d}", tif=tif,
                um_per_px=float(g["um_per_px_x"]),
                label=f"{STRAIN_LABEL[strain]} {REP_LABEL[rep]} {TOL_LABEL[tol]}",
                n=len(s.rows), nonzero=float(np.mean(arr > 0)),
                max_r=max((r["radius_nm"] for r in s.rows), default=0.0),
                n_merged=sum(1 for r in s.rows if r.get("merged")),
            ))

    live = [x for x in scan if x["n"] > 0]
    hazy = sorted(scan, key=lambda x: -x["nonzero"])[:2]
    clean = [x for x in live if x["nonzero"] < 0.05]
    picks, seen = [], set()

    def add(rec, role):
        key = (rec["sub"], rec["series"])
        if key in seen:
            return
        seen.add(key)
        picks.append(dict(rec, role=role))

    for h in hazy:
        add(h, "hazy — diffuse background, where a noise model has to work")
    add(max(clean, key=lambda x: x["n"]), "dense — clean field, most particles")
    add(min(clean, key=lambda x: x["n"]), "sparse — clean field, fewest particles")
    add(max(live, key=lambda x: x["max_r"]), "largest — holds the biggest object")
    add(max(live, key=lambda x: x["n_merged"]), "crowded — most merged/overlapping")

    # Identically-zero fields. They prove the detector has no dark-count
    # population, which is worth confirming and is ALL they prove: a frame that
    # is uniformly zero carries no shot noise to trip over.
    for b in sorted((x for x in scan if x["n"] == 0), key=lambda x: x["sub"])[:2]:
        add(b, "empty — the frame is identically zero, so any detection is false")

    # The matched sample-free control, and the more informative of the two
    # blanks by far: same objective, same 561 nm laser power to three figures,
    # same HyD gain, same 1 AU pinhole, same line average. Only the zoom differs.
    # It is NOT empty, which is the point of including it.
    for sub in BACKGROUND:
        for idx, tif in series_tifs(sub)[:1]:
            g = geom[(sub, f"Series{idx:03d}")]
            add(dict(strain="-", rep="-", tol="-", sub=sub,
                     series=f"Series{idx:03d}", tif=tif,
                     um_per_px=float(g["um_per_px_x"]),
                     label="sample-free control (zoom 0.75)",
                     n=0, nonzero=float(np.mean(load_field(tif) > 0)),
                     max_r=0.0, n_merged=0),
                "control — no sample, matched laser and gain; detections here are false")

    print(f"  {len(scan)} fields scanned; comparison set = {len(picks)}")
    for p in picks:
        print(f"    {p['sub']}/{p['series']:9s} {p['role']}")
    return picks


# --- scorecard ---------------------------------------------------------------

def quartile_flatness(rows, resolved_only: bool = False) -> tuple[float, list[float]]:
    """Median radius per peak-brightness quartile, as max/min.

    Quartiles are on `peak_above_bg`, which every backend reports, so the bins
    mean the same thing for each. A size estimator that is really measuring
    photon count rather than size shows a ratio well above 1.

    `resolved_only` drops particles measured smaller than the PSF before
    binning, and the two versions answer different questions. Unrestricted, the
    faintest quartile of a permissive backend is mostly single-photon events
    sized at 30-60 nm, so the ratio measures *what the detector let in*.
    Restricted, every backend is scored on the same physically-possible
    population, so the ratio measures *the size estimator itself*. Both are
    reported because a backend can fail either way and the remedies differ.
    """
    if resolved_only:
        rows = [r for r in rows if r["radius_nm"] >= PSF_RADIUS_NM]
    if len(rows) < 20:
        return float("nan"), []
    peak = np.array([r["peak_above_bg"] for r in rows], dtype=float)
    rad = np.array([r["radius_nm"] for r in rows], dtype=float)
    edges = np.percentile(peak, [0, 25, 50, 75, 100])
    meds = []
    for i in range(4):
        lo, hi = edges[i], edges[i + 1]
        m = (peak >= lo) & (peak <= hi if i == 3 else peak < hi)
        if m.sum() >= 5:
            meds.append(float(np.median(rad[m])))
    if len(meds) < 2:
        return float("nan"), meds
    return max(meds) / min(meds), meds


def subpsf_character(rows, shape, rng) -> tuple[float, float]:
    """Are the sub-resolution detections dim vesicles, or single photons?

    Two numbers, both computed from the backend's own output. The first is how
    much more tightly the sub-PSF detections sit to the *resolved* ones than
    uniformly random points over the same field would: real dim vesicles are
    part of the same population and cluster with it, a detector-noise floor is
    spatially uniform and scores about 1.0 or below. The second is the fraction
    of them whose peak is a single count, which is what a lone photon looks like.

    This is the test that says whether the faint half of a permissive backend's
    catalogue is signal or floor, and no picture can settle it — at this scale a
    real dim vesicle and a stray photon are both one bright pixel.
    """
    from scipy.spatial import cKDTree

    rad = np.array([r["radius_nm"] for r in rows], dtype=float)
    peak = np.array([r["peak_above_bg"] for r in rows], dtype=float)
    xy = np.array([[r["x_px"], r["y_px"]] for r in rows], dtype=float)
    small = rad < PSF_RADIUS_NM
    if small.sum() < 20 or (~small).sum() < 20:
        return float("nan"), float(np.mean(peak[small] <= 1.01)) if small.any() else float("nan")
    tree = cKDTree(xy[~small])
    obs = np.median(tree.query(xy[small])[0])
    rnd = np.median(tree.query(rng.uniform(0, shape[0], size=(small.sum() * 5, 2)))[0])
    return (float(rnd / obs) if obs > 0 else float("nan"),
            float(np.mean(peak[small] <= 1.01)))


def run_scorecard(picks, geom) -> tuple[list[dict], list[dict]]:
    area = {(k[0], k[1]): float(v["fov_area_um2"]) for k, v in geom.items()}
    rng = np.random.default_rng(SYNTH_SEED)
    per_field, sweep = [], []
    for name, be in BACKENDS.items():
        print(f"\n{name}:")
        for p in picks:
            arr = load_field(p["tif"])
            fov = area[(p["sub"], p["series"])]
            seg = segment(arr, p["um_per_px"], p["um_per_px"], backend=name)
            rad = np.array([r["radius_nm"] for r in seg.rows], dtype=float)
            surf = np.array([r["surface_area_um2"] for r in seg.rows], dtype=float)
            resolved = rad >= PSF_RADIUS_NM
            flat, meds = quartile_flatness(seg.rows)
            flat_res, meds_res = quartile_flatness(seg.rows, resolved_only=True)
            clust, single = (subpsf_character(seg.rows, arr.shape, rng)
                             if seg.rows else (float("nan"), float("nan")))
            per_field.append(dict(
                backend=name, knob_name=be.knob_name, knob=be.knob_default,
                exported_dir=p["sub"], series=p["series"], role=p["role"].split(" — ")[0],
                condition=p["label"], nonzero_fraction=round(p["nonzero"], 4),
                fov_area_um2=round(fov, 1),
                n_particles=len(seg.rows), n_detections=seg.n_features,
                per_1000um2=_r(len(seg.rows) / fov * 1000, 3),
                # The same density counting only particles the optics could
                # actually resolve — see PSF_RADIUS_NM.
                n_resolved=int(resolved.sum()),
                resolved_per_1000um2=_r(int(resolved.sum()) / fov * 1000, 3),
                median_radius_nm=_r(np.median(rad) if len(rad) else float("nan"), 1),
                p90_radius_nm=_r(np.percentile(rad, 90) if len(rad) else float("nan"), 1),
                max_radius_nm=_r(rad.max() if len(rad) else float("nan"), 1),
                summed_surface_um2=_r(float(surf.sum()), 4),
                frac_below_psf=_r(float(np.mean(~resolved)) if len(rad) else 0.0, 4),
                quartile_flatness=_r(flat, 3),
                quartile_medians_nm="|".join(f"{m:.0f}" for m in meds),
                quartile_flatness_resolved=_r(flat_res, 3),
                quartile_medians_resolved_nm="|".join(f"{m:.0f}" for m in meds_res),
                subpsf_clustering=_r(clust, 3),
                subpsf_frac_single_count=_r(single, 3),
                n_flagged=sum(1 for r in seg.rows
                              if r.get("deblended") or r.get("merged")
                              or r.get("n_centers_in_region", 1) > 1),
                n_unsized=seg.diag.get("n_unsized", ""),
                bkg_median=_r(seg.diag.get("bkg_median", float("nan")), 4),
                rms_median=_r(seg.diag.get("rms_median", float("nan")), 4),
            ))
            print(f"  {p['role'].split(' — ')[0]:9s} {p['series']:9s} "
                  f"{len(seg.rows):6d} particles  "
                  f"{per_field[-1]['per_1000um2']:>8} /1000µm²  "
                  f"med {np.median(rad) if len(rad) else 0:6.1f} nm  "
                  f"flat {flat:5.2f}  sub-PSF {per_field[-1]['frac_below_psf']:.0%}")

            for knob in be.knob_sweep:
                s2 = segment(arr, p["um_per_px"], p["um_per_px"],
                             backend=name, knob=knob)
                sf = np.array([r["surface_area_um2"] for r in s2.rows], dtype=float)
                rr = np.array([r["radius_nm"] for r in s2.rows], dtype=float)
                sweep.append(dict(
                    backend=name, knob_name=be.knob_name, knob=knob,
                    exported_dir=p["sub"], series=p["series"],
                    role=p["role"].split(" — ")[0], fov_area_um2=round(fov, 1),
                    n_particles=len(s2.rows),
                    n_resolved=int((rr >= PSF_RADIUS_NM).sum()) if len(rr) else 0,
                    per_1000um2=_r(len(s2.rows) / fov * 1000, 3),
                    summed_surface_um2=_r(float(sf.sum()), 4),
                ))
    return per_field, sweep


def summarise(per_field, sweep) -> list[dict]:
    """One row per backend: the tests, each reduced to a number."""
    out = []
    for name, be in BACKENDS.items():
        f = [r for r in per_field if r["backend"] == name]
        by = lambda role: [r for r in f if r["role"] == role]  # noqa: E731
        sample = [r for r in f if r["role"] not in ("empty", "control")]
        empty, control = by("empty"), by("control")
        hazy, dense, crowd = by("hazy"), by("dense"), by("crowded")
        flats = [r["quartile_flatness"] for r in sample
                 if isinstance(r["quartile_flatness"], float)]
        flats_res = [r["quartile_flatness_resolved"] for r in sample
                     if isinstance(r["quartile_flatness_resolved"], float)]

        # Knob stability: how far the count on the sample fields moves across
        # the middle of each tool's own sweep, relative to its default.
        mid = be.knob_sweep[1:-1]
        by_knob = {k: sum(r["n_particles"] for r in sweep
                          if r["backend"] == name and r["knob"] == k
                          and r["role"] not in ("empty", "control"))
                   for k in mid}
        base = sum(r["n_particles"] for r in sample)
        span = ((max(by_knob.values()) - min(by_knob.values())) / base
                if base and by_knob else float("nan"))

        # Haze over-detection: particles per field where there IS a background,
        # against the densest clean field. A detector with no noise model runs
        # away here.
        haze_ratio = (np.mean([r["n_particles"] for r in hazy])
                      / max(1.0, np.mean([r["n_particles"] for r in dense]))) \
            if hazy and dense else float("nan")

        # Signal over the sample-free control, per unit area so the two zooms
        # can be compared, both for the whole catalogue and for the part the
        # optics could resolve. This is the test that asks whether a backend's
        # detections are distinguishable from a field with nothing in it.
        def dens(rows, key):
            return float(np.mean([r[key] or 0.0 for r in rows])) if rows else float("nan")

        c_all, c_res = dens(control, "per_1000um2"), dens(control, "resolved_per_1000um2")
        d_all, d_res = dens(dense, "per_1000um2"), dens(dense, "resolved_per_1000um2")

        out.append(dict(
            backend=name, knob_name=be.knob_name, knob_default=be.knob_default,
            t1_radius_flatness=_r(float(np.median(flats)) if flats else float("nan"), 3),
            t1_flatness_resolved=_r(float(np.median(flats_res)) if flats_res else float("nan"), 3),
            t1_worst_field=_r(max(flats) if flats else float("nan"), 3),
            t2_empty_detections=sum(r["n_particles"] for r in empty),
            t2_control_per_1000um2=_r(c_all, 2),
            t2_dense_over_control=_r(d_all / c_all if c_all else float("nan"), 2),
            t2_dense_over_control_resolved=_r(d_res / c_res if c_res else float("nan"), 2),
            t3_haze_vs_dense_ratio=_r(haze_ratio, 2),
            t3_haze_particles=sum(r["n_particles"] for r in hazy),
            t4_crowded_particles=sum(r["n_particles"] for r in crowd),
            t4_crowded_flagged=sum(r["n_flagged"] for r in crowd),
            t5_count_span_over_sweep=_r(span, 3),
            # Whether the sub-resolution half of the catalogue behaves like
            # vesicles or like a photon floor. Clustering near 1.0 or below plus
            # a high single-count fraction says floor.
            t6_subpsf_clustering=_r(_nanmed(sample, "subpsf_clustering"), 3),
            t6_subpsf_single_count=_r(_nanmed(sample, "subpsf_frac_single_count"), 3),
            frac_below_psf=_r(float(np.mean([r["frac_below_psf"] for r in sample])), 4),
            median_radius_nm=_r(float(np.median([r["median_radius_nm"] for r in sample
                                                 if isinstance(r["median_radius_nm"], float)])), 1),
            total_particles_sample_fields=sum(r["n_particles"] for r in sample),
        ))
    return out


# --- overlays ----------------------------------------------------------------

def render_overlays(picks) -> list[tuple]:
    index = []
    for p in picks:
        arr = load_field(p["tif"])
        for name in BACKENDS:
            seg = segment(arr, p["um_per_px"], p["um_per_px"], backend=name)
            role = p["role"].split(" — ")[0]
            caption = (f"{p['label']} — {p['sub']}/{p['series']} — {p['role']}")
            path = OUT / f"{role}_{p['series']}_{name}.svg"
            path.write_text(build_svg(arr, seg, p["um_per_px"], caption),
                            encoding="utf-8")
            index.append((role, p, name, seg, path))
            print(f"  {path.name:52s} {len(seg.rows):6d} particles  "
                  f"{path.stat().st_size // 1024} KB")
    return index


def write_index(index, card) -> None:
    fields, seen = [], set()
    for role, p, _, _, _ in index:
        key = (role, p["series"])
        if key not in seen:
            seen.add(key)
            fields.append((role, p))

    def cell(role, p, backend):
        for r, pp, n, seg, path in index:
            if r == role and pp["series"] == p["series"] and n == backend:
                rad = [x["radius_nm"] for x in seg.rows]
                return (f'<td><a href="{path.name}">{len(seg.rows)} particles</a><br>'
                        f'<small>median {np.median(rad):.0f} nm</small></td>'
                        if rad else f'<td><a href="{path.name}">0</a></td>')
        return "<td>—</td>"

    rows = "\n".join(
        f'<tr><td><b>{html.escape(role)}</b><br><small>{html.escape(p["label"])}<br>'
        f'{html.escape(p["series"])}</small></td>'
        + "".join(cell(role, p, b) for b in BACKENDS) + "</tr>"
        for role, p in fields
    )
    card_rows = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r.values()) + "</tr>"
        for r in card
    )
    card_head = "".join(f"<th>{html.escape(k)}</th>" for k in card[0])

    (OUT / "index.html").write_text(f"""<!doctype html>
<meta charset="utf-8"><title>segmentation bake-off</title>
<style>
 body{{font:14px/1.5 system-ui,sans-serif;margin:2rem;background:#111;color:#ddd}}
 table{{border-collapse:collapse;margin:1rem 0}}
 td,th{{padding:.4rem .7rem;border-bottom:1px solid #333;vertical-align:top}}
 a{{color:#4fd}} th{{text-align:left;color:#999}} p{{max-width:64em;color:#bbb}}
 small{{color:#888}} code{{color:#9fd}} h2{{margin-top:2rem;color:#eee}}
</style>
<h1>Segmentation bake-off</h1>
<p>Three backends over the same fields. Every circle is at the radius its backend
actually measured, from the same <code>segmenters.segment()</code> call the tables
would use. <b>Zoom in</b>: the background pixellates, the circles stay sharp.</p>
<p>What to check: circles on puncta and sized to the visible extent of the spot;
faint puncta circled as well as bright ones; nothing circled on grain in the
<b>hazy</b> rows; nothing at all circled in the <b>empty</b> rows; clumps carrying
several circles in the <b>crowded</b> row. And the <b>control</b> row, which is the
one that matters most — see below.</p>

<h2>Scorecard</h2>
<p><code>t1_radius_flatness</code> is the ratio of median radius between the
brightest and faintest quartile — 1.0 means size does not track brightness, and
the estimator rejected at the last gate scored 2.0.</p>
<p><code>t2_empty_detections</code> counts detections in fields that are
identically zero; anything but 0 is a bug. <code>t2_control_*</code> is the
serious one: the <b>sample-free control acquisition</b>, taken at the same
objective, the same 561 nm laser power to three figures, the same detector gain
and the same pinhole as every sample — only the zoom differs, so densities are
compared per 1000 µm². <code>t2_dense_over_control</code> is how many times more
particles the densest clean sample field yields than a field with no sample in
it, and <code>..._resolved</code> repeats it counting only particles at or above
the point-spread function's own radius.</p>
<p><code>t3</code> is particles per hazy field over particles per clean dense
field. <code>t5</code> is how far the count moves across the middle of each
tool's own threshold sweep. <code>frac_below_psf</code> is the fraction of
particles measured smaller than the point-spread function itself, which nothing
imaged through this optic can be.</p>
<p><code>t6_*</code> asks what that sub-resolution population actually is. Real
dim vesicles belong to the same population as the bright ones and cluster with
them, scoring well above 1; a detector noise floor is spatially uniform and
scores about 1 or below. <code>t6_subpsf_single_count</code> is the fraction of
them whose peak is one count — a lone photon. No picture can settle this: at
this scale a dim vesicle and a stray photon are both one bright pixel.</p>
<table><tr>{card_head}</tr>
{card_rows}
</table>

<h2>Overlays</h2>
<table><tr><th>field</th>{"".join(f"<th>{b}</th>" for b in BACKENDS)}</tr>
{rows}
</table>
""", encoding="utf-8")


# --- plumbing ----------------------------------------------------------------

def _nanmed(rows, key) -> float:
    """Median over the rows that carry a real value for `key`.

    `_r` writes "" where a field could not be computed, and a legitimate 0.0 is
    falsy — so the values have to be filtered by type, not by truthiness. That
    distinction matters here: trackpy's sub-PSF population contains no
    single-count detections at all, and a truthiness filter reports that real
    zero as a missing measurement.
    """
    vals = [r[key] for r in rows if isinstance(r[key], (int, float))]
    return float(np.median(vals)) if vals else float("nan")


def _r(v, nd):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return "" if not np.isfinite(f) else round(f, nd)


def _write(path: Path, rows: list[dict], header: str) -> None:
    if not rows:
        raise RuntimeError(f"nothing to write to {path}")
    with path.open("w", newline="") as fh:
        fh.write(header)
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.name:28s} {len(rows)} rows")


SYNTH_HEADER = (
    "# Adapter validation on planted Gaussian spots -- see bakeoff.py.\n"
    "# Spots have the width of the acquisition's own point-spread function and\n"
    "# amplitudes spanning the real range, Poisson-sampled and rounded to counts.\n"
    "# All three backends report sqrt(2 ln 2)*sigma for a Gaussian, so radius_bias\n"
    "# (measured / true) should be 1.0 for every backend and flatness should be 1.0.\n"
    "# This is the check that catches an adapter wired up wrongly; real data cannot\n"
    "# do it, because no micrograph tells you the true radius of anything in it.\n"
)

FIELD_HEADER = (
    "# One row per (backend, field) over the bake-off comparison set, at each\n"
    "# backend's default threshold. The set is adversarial, not representative:\n"
    "# hazy, dense, sparse, largest-object, crowded, and blank fields.\n"
    "# frac_below_psf is the fraction of particles measured smaller than the\n"
    "# point-spread function -- physically impossible, so it measures how much of\n"
    "# the catalogue is noise being sized. Written by bakeoff.py.\n"
)

SWEEP_HEADER = (
    "# Count and summed surface area against each backend's OWN detection\n"
    "# threshold, over the comparison set. Each tool is swept on the dial its\n"
    "# authors expose, so the knob column is NOT comparable between backends --\n"
    "# what is comparable is how much each backend's answer moves across it.\n"
    "# Written by bakeoff.py.\n"
)

CARD_HEADER = (
    "# The five bake-off tests, one row per backend. See bakeoff.py for what each\n"
    "# column measures and why. No backend is selected here: this table and the\n"
    "# overlays in bakeoff/index.html are the input to that decision.\n"
)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    geom = load_geometry()

    synth = run_synthetic()
    print()
    _write(OUT / "synthetic_validation.csv", synth, SYNTH_HEADER)

    print()
    picks = pick_fields(geom)

    per_field, sweep = run_scorecard(picks, geom)
    card = summarise(per_field, sweep)

    print("\nrendering overlays ...")
    index = render_overlays(picks)
    write_index(index, card)

    print()
    _write(OUT / "bakeoff_fields.csv", per_field, FIELD_HEADER)
    _write(OUT / "bakeoff_sweep.csv", sweep, SWEEP_HEADER)
    _write(OUT / "bakeoff_scorecard.csv", card, CARD_HEADER)

    print("\nSCORECARD")
    keys = ["backend", "t1_radius_flatness", "t1_flatness_resolved",
            "t2_empty_detections",
            "t2_control_per_1000um2", "t2_dense_over_control",
            "t2_dense_over_control_resolved", "t3_haze_vs_dense_ratio",
            "t4_crowded_particles", "t5_count_span_over_sweep",
            "t6_subpsf_clustering", "t6_subpsf_single_count",
            "frac_below_psf", "median_radius_nm", "total_particles_sample_fields"]
    print("  " + " ".join(f"{k.replace('_', ' '):>22s}"[-22:] for k in keys))
    for r in card:
        print("  " + " ".join(f"{str(r[k]):>22s}" for k in keys))
    print(f"\nopen {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

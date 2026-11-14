"""Vesicle detection and sizing: one interface, three interchangeable backends.

Detecting faint near-point sources against a variable background, separating the
ones that overlap, and measuring their size, is what astronomical source
extraction has done for thirty years. The first pass here hand-rolled all four of
those steps and got two of them wrong, so the segmentation is now settled by a
bake-off between established tools (see bakeoff.py) rather than by another
bespoke attempt.

The layer owns what must not vary between backends
--------------------------------------------------
`segment()` converts whatever radius a backend reports into microns using the
measured pixel pitch and derives area, surface area and volume from it. Every
backend therefore answers the same question in the same units, and the only thing
that differs between them is the call into their own library.

A sphere in projection shows a disk of its own radius, so `radius` is what a
backend measures in the image plane and `surface_area_um2 = 4*pi*r^2`. That makes
surface area exactly four times projected area — the spherical assumption
contributes a constant factor and nothing else.

`extra` columns are per-backend and are NOT filled in for backends that cannot
report them. A backend that has no notion of "this region is shared with a
neighbour" leaves the column absent rather than having the layer substitute a
plausible value, because a scorecard that compares invented numbers is worse than
one with a gap in it.

The size estimators, and why they are comparable
------------------------------------------------
All three report a radius that is `1.177 * sigma` for a Gaussian spot, so they
can be put side by side without a conversion factor:

* trackpy backend -- the radius of the connected region above *half that spot's
  own peak*. Half-max radius of a Gaussian is `sqrt(2 ln 2) * sigma`.
* photutils -- `SourceCatalog.fwhm / 2`, from the second moments of the intensity
  distribution inside the segment. `FWHM/2 = sqrt(2 ln 2) * sigma`.
* sep -- `sep.flux_radius` at 50%, the half-light radius. For a 2D Gaussian the
  enclosed fraction is `1 - exp(-r^2 / 2 sigma^2)`, so `r50 = sqrt(2 ln 2) *
  sigma` as well.

That coincidence is specific to 2D Gaussians and is exactly why the synthetic
check in bakeoff.py plants Gaussians: all three backends have the same right
answer on it, so an adapter wired up wrongly shows as a wrong number rather than
as a plausible one.

The zero-background problem
---------------------------
These are photon counts from a counting detector, and 100 of the 103 sample
fields have a background of exactly zero: no dark counts, no read noise, no
pedestal. Every threshold in this file is expressed as a multiple of the measured
local noise, which on those fields is zero -- so the threshold collapses to zero
and *every nonzero pixel is signal*, which is the correct answer for a noiseless
background and is what "take the pixels at face value" means here.

The failure mode this avoids is worth stating because the first attempt fell into
it: substituting a floor (`sqrt(bg + 1)`, or a minimum absolute threshold)
turns the noise test into a flat brightness cut on those 100 fields, and a flat
brightness cut discards small dim vesicles in preference to large bright ones --
biasing the very quantity being measured. Only the 3 hazy fields (all in
clon1_1, diffuse signal over ~90% of their pixels) have a background for a
significance threshold to bite on, and there it should bite.

What the radius is not
----------------------
An apparent spot radius, convolved with the ~211 nm point-spread function of the
acquisition (63x/1.40 NA, 580 nm emission, 1.0 Airy unit pinhole). It is NOT a
physical vesicle radius, and no deconvolution is applied. Most of this population
sits at or below that limit, so summed surface area is an UPPER BOUND.
"""

import csv
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from vesicle_common import PANELS, RESULTS

GEOM = RESULTS / "fov_geometry.csv"

# Lateral resolution of the acquisition: 63x/1.40 NA, 580 nm emission, 1.0 Airy
# unit pinhole. The FWHM is a fixed *physical* size; the pixel figure is only
# true at the sample zoom of 2 (0.0901 µm/px), and the background acquisition at
# zoom 0.75 undersamples this badly — 0.9 px per FWHM, well under Nyquist — so
# any comparison of sizes across the two zooms has to be made in nanometres.
PSF_FWHM_NM = 211.0
PSF_RADIUS_NM = PSF_FWHM_NM / 2.0
PSF_FWHM_PX = 2.3

# Both segmentation backends match-filter with a kernel of the PSF's width
# before thresholding, which is what makes a threshold of "n sigma" mean the
# same thing for a point source as for a pixel.

# A source must occupy at least this many connected pixels above the detection
# threshold. At 2.3 px FWHM a real spot covers ~4 px above its own half-max and
# more than that above a threshold set near the background, so this rejects
# single-pixel hits without touching anything resolved.
MIN_PIXELS = 5

# Background mesh. 64 px across a 1024 px field is 16x16 boxes -- fine enough to
# follow the haze gradients in clon1_1, coarse enough that a box is mostly
# background rather than vesicle even in the densest field.
BOX_PX = 64
FILTER_BOXES = 3


@dataclass
class Detection:
    """One source, in image units, as its backend measured it."""

    x_px: float
    y_px: float
    radius_px: float        # 1.177*sigma for a Gaussian, however the backend gets there
    peak_above_bg: float
    local_bg: float
    flux: float             # integrated brightness, each backend's own definition
    extra: dict = field(default_factory=dict)


@dataclass
class Segmentation:
    """A segmented field: the particle rows, plus what the backend could not do."""

    rows: list[dict] = field(default_factory=list)
    diag: dict = field(default_factory=dict)
    backend: str = ""
    knob: float = 0.0

    @property
    def n_features(self) -> int:
        return int(self.diag.get("n_features", len(self.rows)))


# --- backends ----------------------------------------------------------------

class Backend:
    """Detect and size the sources in one field.

    `find` returns (detections, diagnostics) for a field already cast to float32.
    `knob` is that backend's own detection threshold, in its own units, so the
    stability test sweeps each tool on the dial its authors expose rather than on
    a common one that would mean something different to each.
    """

    name: str
    knob_name: str
    knob_default: float
    knob_sweep: tuple[float, ...]
    extra_columns: tuple[str, ...] = ()

    def find(self, arr: np.ndarray, knob: float) -> tuple[list[Detection], dict]:
        raise NotImplementedError


class TrackpyHalfMax(Backend):
    """Crocker-Grier detection, then each spot sized by its own half-max contour.

    The baseline to beat: it is the first working version, already gated once and
    rejected once, and it is the only backend here that lets overlapping
    particles *share* pixels rather than partitioning them. Two features whose
    half-max regions merge both receive the merged region, so those pixels are
    counted twice and `n_centers_in_region` records it. That is deliberate --
    partitioning them (a watershed) makes each measure less than its true
    projected disk -- and it is a real difference from the two segmentation
    backends, which deblend into disjoint segments.

    Everything except the trackpy call is hand-rolled: the local background
    annulus, the Poisson significance test, the region growth cap. That is the
    reason for the bake-off, and the reason this is the baseline rather than the
    answer.
    """

    name = "trackpy"
    knob_name = "min_z"
    knob_default = 3.0
    knob_sweep = (0.0, 2.0, 3.0, 4.0, 5.0, 8.0)
    extra_columns = ("area_px", "poisson_z", "region_capped",
                     "n_centers_in_region", "tp_size", "tp_ecc")

    FEATURE_DIAMETER_PX = 5     # odd, and a little larger than the 2.3 px PSF
    SEPARATION_PX = 3           # two maxima closer than the PSF are one object
    # Half-max region grows no further than this from the centre, so one spot in
    # a bright clump cannot claim the whole clump. 10 px = ~900 nm; at this cap
    # the median radius is unchanged and 1.7% of features are truncated.
    REGION_CAP_PX = 10.0
    WINDOW_PX = 13              # must exceed the cap: the annulus is between them

    def __init__(self):
        w = self.WINDOW_PX
        yy, xx = np.mgrid[-w:w + 1, -w:w + 1]
        rr = np.hypot(xx, yy)
        self._rr = rr
        self._annulus = (rr > self.REGION_CAP_PX) & (rr <= w)
        self._cap = rr <= self.REGION_CAP_PX
        self._near = rr <= 1.5          # tolerance for the sub-pixel centroid
        self._edge = rr > self.REGION_CAP_PX - 1

    def find(self, arr, knob):
        import trackpy as tp
        from scipy import ndimage as ndi

        warnings.filterwarnings("ignore", category=UserWarning, module="trackpy")
        tp.quiet()

        # The dtype is pinned upstream in segment(), and that is not cosmetic:
        # tp.locate picks its own bandpass threshold from the input dtype (1/255
        # for integers), so handing it uint8 rather than float silently changes
        # the answer -- 26766 features against 8263 on one field here.
        f = tp.locate(arr, diameter=self.FEATURE_DIAMETER_PX, minmass=0,
                      separation=self.SEPARATION_PX, percentile=0,
                      preprocess=True, threshold=0)
        diag = dict(n_features=len(f), n_unsized=0, n_capped=0, n_shared=0,
                    n_below_z=0)
        if not len(f):
            return [], diag

        w = self.WINDOW_PX
        iy = np.round(f["y"].to_numpy()).astype(int)
        ix = np.round(f["x"].to_numpy()).astype(int)
        pad = np.pad(arr.astype(float), w)
        centres = np.zeros(arr.shape, dtype=bool)
        centres[np.clip(iy, 0, arr.shape[0] - 1), np.clip(ix, 0, arr.shape[1] - 1)] = True
        cpad = np.pad(centres, w)
        cols = {c: f[c].to_numpy() for c in f.columns}

        out = []
        for k in range(len(f)):
            y0, x0 = iy[k], ix[k]
            win = pad[y0:y0 + 2 * w + 1, x0:x0 + 2 * w + 1]
            bg = float(np.median(win[self._annulus]))
            peak = float(win[self._near].max()) - bg
            if peak <= 0:
                diag["n_unsized"] += 1
                continue
            # This spot's own region only: label the half-max mask and keep the
            # component under the centre, so a neighbour across a dark gap is
            # not absorbed.
            lab, _ = ndi.label(((win - bg) >= peak / 2.0) & self._cap)
            cid = lab[w, w]
            if cid == 0:
                diag["n_unsized"] += 1
                continue
            # Significance against this spot's OWN local background. No
            # background means no noise to clear, so the detection survives any
            # floor -- see the module docstring on the zero-background problem.
            z = peak / math.sqrt(bg) if bg > 0 else math.inf
            if z < knob:
                diag["n_below_z"] += 1
                continue
            region = lab == cid
            area_px = int(region.sum())
            capped = bool((region & self._edge).any())
            shared = int(cpad[y0:y0 + 2 * w + 1, x0:x0 + 2 * w + 1][region].sum())
            diag["n_capped"] += capped
            diag["n_shared"] += shared > 1
            out.append(Detection(
                x_px=float(cols["x"][k]), y_px=float(cols["y"][k]),
                radius_px=math.sqrt(area_px / math.pi),
                peak_above_bg=peak, local_bg=bg,
                flux=float(cols["mass"][k]),
                extra=dict(area_px=area_px,
                           poisson_z=round(z, 3) if math.isfinite(z) else "inf",
                           region_capped=capped, n_centers_in_region=shared,
                           tp_size=round(float(cols["size"][k]), 3),
                           tp_ecc=round(float(cols["ecc"][k]), 3)),
            ))
        return out, diag


class Photutils(Backend):
    """photutils: Background2D -> detect_sources -> deblend_sources -> SourceCatalog.

    Maps one-to-one onto the four steps the baseline hand-rolls, which is the
    point of using it. `Background2D` estimates the local background and its RMS
    on a mesh; `detect_sources` thresholds at n sigma of that RMS map;
    `deblend_sources` splits merged objects by multi-thresholding; `SourceCatalog`
    measures each one.

    Radius is `fwhm / 2`, from the second moments of the intensity distribution.
    The catalog also offers `equivalent_radius`, from the segment's pixel count,
    which is threshold-defined and so carries exactly the brightness bias that
    failed the first gate -- it is recorded as an extra column so the scorecard
    can show the difference rather than assert it.

    Detection runs on a PSF-matched convolution of the background-subtracted
    field, which is the documented pattern and is what makes "n sigma" the right
    unit for a point source. The catalog is built on the *unconvolved* data, so
    the measured widths are the spots' own and not the kernel's.
    """

    name = "photutils"
    knob_name = "nsigma"
    # photutils' own documented working range is 1.5-3 sigma. On the synthetic
    # check (bakeoff.py) this backend returns zero spurious sources anywhere in
    # that range and down to 1 sigma, so the default sits at the permissive end:
    # completeness is what costs it, not purity.
    knob_default = 1.5
    knob_sweep = (1.0, 1.5, 2.0, 3.0, 5.0, 8.0)
    extra_columns = ("area_px", "equivalent_radius_px", "semimajor_px",
                     "semiminor_px", "ellipticity", "deblended")

    DEBLEND_LEVELS = 32
    DEBLEND_CONTRAST = 0.001

    def find(self, arr, knob):
        from astropy.convolution import convolve
        from photutils.background import Background2D, MedianBackground
        from photutils.segmentation import (
            SourceCatalog, deblend_sources, detect_sources, make_2dgaussian_kernel,
        )

        bkg = Background2D(arr, box_size=BOX_PX, filter_size=FILTER_BOXES,
                           bkg_estimator=MedianBackground())
        back = bkg.background
        sub = arr - back
        kernel = make_2dgaussian_kernel(PSF_FWHM_PX, size=5)
        conv = convolve(sub, kernel)

        # Where the background is exactly zero its RMS is zero and this is zero,
        # so every pixel above the background is signal. Deliberate -- see the
        # module docstring.
        threshold = knob * bkg.background_rms
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            segm = detect_sources(conv, threshold, npixels=MIN_PIXELS)
            if segm is None:
                return [], dict(n_features=0, n_before_deblend=0, n_deblended=0,
                                bkg_median=float(np.median(back)),
                                rms_median=float(np.median(bkg.background_rms)))
            n_before = segm.n_labels
            deb = deblend_sources(conv, segm, npixels=MIN_PIXELS,
                                  nlevels=self.DEBLEND_LEVELS,
                                  contrast=self.DEBLEND_CONTRAST,
                                  progress_bar=False)
            cat = SourceCatalog(sub, deb)

        diag = dict(n_features=deb.n_labels, n_before_deblend=n_before,
                    n_deblended=deb.n_labels - n_before,
                    bkg_median=float(np.median(back)),
                    rms_median=float(np.median(bkg.background_rms)))

        # photutils 3.0 column names; several come back as pixel-unit
        # Quantities, hence _f().
        tbl = cat.to_table(columns=[
            "label", "x_centroid", "y_centroid", "fwhm", "equivalent_radius",
            "area", "max_value", "segment_flux", "semimajor_axis",
            "semiminor_axis", "ellipticity",
        ])
        # A source whose segment is too thin to support second moments returns a
        # NaN fwhm. It is dropped rather than backfilled from the area, which
        # would silently mix two different size estimators in one column.
        out, n_nan = [], 0
        for r in tbl:
            fwhm = _f(r["fwhm"])
            if not np.isfinite(fwhm) or fwhm <= 0:
                n_nan += 1
                continue
            x, y = _f(r["x_centroid"]), _f(r["y_centroid"])
            iy = int(np.clip(round(y), 0, arr.shape[0] - 1))
            ix = int(np.clip(round(x), 0, arr.shape[1] - 1))
            out.append(Detection(
                x_px=x, y_px=y,
                radius_px=fwhm / 2.0,
                peak_above_bg=_f(r["max_value"]),
                local_bg=float(back[iy, ix]),
                flux=_f(r["segment_flux"]),
                extra=dict(
                    area_px=int(_f(r["area"])),
                    equivalent_radius_px=round(_f(r["equivalent_radius"]), 4),
                    semimajor_px=round(_f(r["semimajor_axis"]), 4),
                    semiminor_px=round(_f(r["semiminor_axis"]), 4),
                    ellipticity=round(_f(r["ellipticity"]), 4),
                    deblended=bool(deb.n_labels > n_before),
                ),
            ))
        diag["n_unsized"] = n_nan
        return out, diag


class Sep(Backend):
    """sep: the Source Extractor algorithm, same ground with fewer knobs.

    `sep.Background` for the background and its RMS map, then `sep.extract` with
    SExtractor's multi-threshold deblender. Size is `sep.flux_radius` at 50% --
    the half-light radius, a standard brightness-independent size that needs no
    assembly from moments.

    Two operational notes. sep requires a native-byte-order C-contiguous array
    and raises otherwise, which `segment()` guarantees. And its threshold is
    `nsigma * err`: on the fields whose background RMS is exactly zero that is
    exactly zero, and sep will not extract at a zero threshold, so the RMS map
    carries a floor of one part in a thousand of a count. That is far below the
    one-count quantum of a photon-counting detector, so on those fields the
    threshold still admits every nonzero pixel -- it is a guard against a
    degenerate division, not a brightness floor.
    """

    name = "sep"
    knob_name = "nsigma"
    # SExtractor's own DETECT_THRESH default is 1.5, which is tuned for
    # Gaussian-noise CCD data. On the synthetic check (bakeoff.py) 1.5 admits
    # 119 spurious sources per field against a Poisson background of 5 counts,
    # while 3.0 admits 1 and still recovers 26 of 30 planted spots. Raised on
    # that evidence, not by preference.
    knob_default = 3.0
    knob_sweep = (1.0, 1.5, 2.0, 3.0, 5.0, 8.0)
    extra_columns = ("area_px", "semimajor_px", "semiminor_px", "theta_rad",
                     "flux_radius_flag", "sep_flag", "merged")

    RMS_FLOOR = 1e-3        # counts; see the class docstring
    DEBLEND_NTHRESH = 32
    DEBLEND_CONT = 0.0005
    # sep pre-allocates a fixed pool for the deblender and raises once it is
    # exhausted. Its default of 1024 is sized for astronomical fields with
    # hundreds of sources; a crowded field here carries several thousand, and at
    # a low threshold the whole field can merge into one blended tree.
    SUB_OBJECT_LIMIT = 16384

    def find(self, arr, knob):
        import sep

        sep.set_sub_object_limit(self.SUB_OBJECT_LIMIT)
        data = np.ascontiguousarray(arr, dtype=np.float32)
        bkg = sep.Background(data, bw=BOX_PX, bh=BOX_PX,
                             fw=FILTER_BOXES, fh=FILTER_BOXES)
        back = bkg.back()
        sub = np.ascontiguousarray(data - back)
        err = np.ascontiguousarray(
            np.maximum(bkg.rms(), self.RMS_FLOOR).astype(np.float32))

        kern = _gaussian_kernel(PSF_FWHM_PX, 5).astype(np.float32)
        try:
            objs = sep.extract(sub, thresh=knob, err=err, minarea=MIN_PIXELS,
                               filter_kernel=kern, filter_type="matched",
                               deblend_nthresh=self.DEBLEND_NTHRESH,
                               deblend_cont=self.DEBLEND_CONT, clean=False)
        except Exception as exc:                      # sep raises a bare Exception
            raise RuntimeError(
                f"sep.extract failed at {self.knob_name}={knob} on a "
                f"{arr.shape} field: {exc}. Raise SUB_OBJECT_LIMIT rather than "
                f"lowering deblend_nthresh — dropping the deblender is what makes "
                f"a crowded field read as one object.") from exc
        diag = dict(n_features=len(objs),
                    bkg_median=float(np.median(back)),
                    rms_median=float(np.median(bkg.rms())),
                    n_merged=int(np.sum((objs["flag"] & sep.OBJ_MERGED) != 0))
                    if len(objs) else 0)
        if not len(objs):
            diag["n_unsized"] = 0
            return [], diag

        # rmax = 6*semimajor is the SExtractor convention for the aperture the
        # half-light radius is measured inside.
        rmax = np.maximum(6.0 * objs["a"], 3.0)
        rad, fr_flag = sep.flux_radius(sub, objs["x"], objs["y"], rmax, 0.5,
                                       normflux=objs["flux"], subpix=5)

        out, n_bad = [], 0
        for i in range(len(objs)):
            r = float(rad[i])
            if not np.isfinite(r) or r <= 0:
                n_bad += 1
                continue
            iy = int(np.clip(round(float(objs["y"][i])), 0, arr.shape[0] - 1))
            ix = int(np.clip(round(float(objs["x"][i])), 0, arr.shape[1] - 1))
            out.append(Detection(
                x_px=float(objs["x"][i]), y_px=float(objs["y"][i]),
                radius_px=r,
                peak_above_bg=float(objs["peak"][i]),
                local_bg=float(back[iy, ix]),
                flux=float(objs["flux"][i]),
                extra=dict(
                    area_px=int(objs["npix"][i]),
                    semimajor_px=round(float(objs["a"][i]), 4),
                    semiminor_px=round(float(objs["b"][i]), 4),
                    theta_rad=round(float(objs["theta"][i]), 4),
                    flux_radius_flag=int(fr_flag[i]),
                    sep_flag=int(objs["flag"][i]),
                    merged=bool(objs["flag"][i] & sep.OBJ_MERGED),
                ),
            ))
        diag["n_unsized"] = n_bad
        return out, diag


def _f(v) -> float:
    """Strip astropy's pixel units. photutils 3.0 returns most morphological
    columns as unit-carrying Quantities, which float() refuses outright."""
    return float(getattr(v, "value", v))


def _gaussian_kernel(fwhm_px: float, size: int) -> np.ndarray:
    """Normalised 2D Gaussian, the same match filter both backends detect with."""
    sigma = fwhm_px / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    ax = np.arange(size, dtype=np.float64) - (size - 1) / 2.0
    g = np.exp(-(ax[:, None] ** 2 + ax[None, :] ** 2) / (2.0 * sigma ** 2))
    return g / g.sum()


BACKENDS: dict[str, Backend] = {b.name: b for b in (TrackpyHalfMax(), Photutils(), Sep())}
DEFAULT_BACKEND = "trackpy"


# --- the common layer --------------------------------------------------------

def segment(arr: np.ndarray, um_per_px_x: float, um_per_px_y: float,
            backend: str = DEFAULT_BACKEND, knob: float | None = None) -> Segmentation:
    """Detect and size one field, in microns.

    The dtype is pinned here, once, for every backend: trackpy changes its
    bandpass threshold with the input dtype and sep raises on a non-native byte
    order, and neither should depend on how the caller happened to load the TIFF.
    """
    be = BACKENDS[backend]
    if knob is None:
        knob = be.knob_default
    dets, diag = be.find(np.asarray(arr, dtype=np.float32), float(knob))

    # Pixels are square in this acquisition; the geometric mean is exact when
    # they are and is the right compromise for a circular radius when they are
    # not. The check is cheap and a 1% anisotropy would silently bias every size.
    if abs(um_per_px_x - um_per_px_y) > 1e-6 * um_per_px_x:
        raise ValueError(f"anisotropic pixels ({um_per_px_x}, {um_per_px_y}): a "
                         "single circular radius is not meaningful")
    px_um = math.sqrt(um_per_px_x * um_per_px_y)

    rows = []
    for d in dets:
        r_um = d.radius_px * px_um
        rows.append(dict(
            x_px=round(d.x_px, 2), y_px=round(d.y_px, 2),
            radius_px=round(d.radius_px, 4),
            radius_nm=round(r_um * 1000.0, 2),
            area_um2=round(math.pi * r_um * r_um, 6),
            # A sphere in projection shows a disk of its own radius, so the
            # surface is 4*pi*r^2 -- exactly four times the projected area.
            surface_area_um2=round(4.0 * math.pi * r_um * r_um, 6),
            volume_um3=round(4.0 / 3.0 * math.pi * r_um ** 3, 8),
            peak_above_bg=round(d.peak_above_bg, 3),
            local_bg=round(d.local_bg, 3),
            flux=round(d.flux, 3),
            **d.extra,
        ))
    return Segmentation(rows=rows, diag=diag, backend=backend, knob=float(knob))


def load_geometry() -> dict[tuple[str, str], dict]:
    rows = {}
    with GEOM.open() as fh:
        for row in csv.DictReader(line for line in fh if not line.startswith("#")):
            rows[(row["exported_dir"], row["series"])] = row
    if not rows:
        raise RuntimeError(f"{GEOM} is empty — run lif_geometry.py first")
    return rows


def load_field(tif: Path) -> np.ndarray:
    return np.array(Image.open(tif))

# GUV microscopy panels

Analysis of `data/fabfos/runs/scadc_microscopy/vesicle_imaging_May_22_2026` — four strains
(EPI300, pCC1, Clone1, Clone2) × ±toluene × 2 biological replicates, 105
acquired fields of view. Everything here runs in the `imaging` env
(`envs/imaging.yml`).

The quantity this chain produces is **vesicle membrane surface area per unit
biomass**, which is the microscopy-side analogue of lipid abundance per OD and
so the number that lets the imaging and the LC-MS/MS lipidomics in this scope be
compared. The superseded particle-*count* chain is in `_old/`.

## The chain

Run in order; each step reads the previous step's table.

    mamba run -n imaging python lif_geometry.py           # fov_geometry.csv
    mamba run -n imaging python bakeoff.py                # bakeoff/ — the backend decision
    mamba run -n imaging python control_floor.py          # control_floor.csv
    mamba run -n imaging python particle_segment.py sep   # particles.csv.gz, fov_measurements.csv, sensitivity_sweep.csv
    mamba run -n imaging python surface_normalize.py      # vesicle_surface_area.csv
    mamba run -n imaging python surface_panels.py         # the three figures

`vesicle_common.py` holds the condition grid, the bad-field exclusions, the
measured pixel pitch and the scale-bar rule, so the mosaic and the measurement
chain cannot disagree about which field is which or how long a bar is.
`segmenters.py` holds the segmentation itself.

`particle_segment.py` refuses to run without an explicit backend argument, and
records which one wrote each table in a `backend` column. That is not
bookkeeping: the three backends differ by ~30% in particle count and ~60 nm in
median radius, so a table that does not say which produced it cannot be compared
with anything.

## Geometry

From the Leica `.lif` originals via `readlif`, not from the exported TIFF tree,
and cross-checked against the exported `MetaData/*_Properties.xml`. All 105
acquired series were exported — nothing was curated away. The 103 sample fields
share one setting: 1024×1024 px, 0.0901 µm/px, 92.26 × 92.26 µm =
**8512.26 µm² per field**, HC PL APO CS2 63×/1.40 OIL at zoom 2. The two
`Backgroundlif` frames are zoom 0.75 and are not samples.

No script hardcodes a pixel pitch. Scale bars pick a whole number of pixels first
and derive the label from what that run actually measures, so the printed length
is what is painted — see `scale_bar()` in `vesicle_common.py` for why the reverse
is a silent error.

## Segmentation: why sep, and how it was chosen

Detecting faint near-point sources against a variable background, separating the
ones that overlap, and measuring their size is what astronomical source
extraction does. `segmenters.py` puts three established tools behind one
interface — **sep** (the SExtractor algorithm), **photutils**, and a
**trackpy + half-max** baseline — and `bakeoff.py` scores them on planted
Gaussian ground truth plus nine adversarial fields.

**sep won.** It is the flattest and most complete on ground truth with a
background (recovers 24 of 30 planted spots with 2 false ones, radius flat to
1.12 across a 80× amplitude range), seven times more stable across its own
detection threshold than the baseline, the best separated from a blank control,
and the best deblender on crowded fields. photutils is the more accurate sizer
(radius bias 1.00, and it never produced a single false detection at any
threshold) but loses the faintest third of the population.

**The baseline was disqualified,** and its failure is worth knowing because it
looks fine on real data: on real fields trackpy scores the *best* radius flatness
of the three, but only because its bandpass silently discards the faint
population, so its faint quartile is real particles while the others' is noise.
On planted ground truth with a background it fabricates 150 particles on a field
containing 30.

Ground truth is the part real data cannot supply: no micrograph tells you the
true radius of anything in it. All three backends report `√(2 ln 2)·σ` for a
Gaussian — half-max radius, FWHM/2 and half-light radius coincide there — so a
planted Gaussian has one right answer for all three, and an adapter wired up
wrongly shows as a wrong number rather than a plausible one.

Re-run `bakeoff.py` before changing backend or threshold. `bakeoff/index.html`
pages through the overlays: the raster pixellates as you zoom while the circles
stay sharp, which is what makes "is that circle the right size on a real vesicle"
answerable by eye.

## What the numbers can and cannot say

**There is a detection floor, and two conditions sit on it.** The session
includes a sample-free control acquired at matched laser power, gain, pinhole and
line average. It is *not* empty — ~19% of its pixels carry about one photon
count, and sep turns that into 67 resolved particles per 1000 µm². EPI300 in both
treatments and Clone2 +toluene are at or below that. Those bars are not
measurements. `over_control` and `above_floor` in `vesicle_surface_area.csv` carry
this per row, and the density figure draws the line.

The floor comparison is on **count**, not area, deliberately: the control is at
zoom 0.75 where one pixel spans 240 nm and nothing can measure below 136 nm in
radius, against the samples' median of 103 nm. Its per-particle areas therefore
run ~8× high, and an area ratio against it would be measuring the difference in
sampling. For the same reason every sample-over-control ratio here is a *lower*
bound on the real separation.

**Roughly half of all detections are smaller than the optics can resolve, and
they are not vesicles.** 46% of the 228k detections have an apparent radius at or
above the 106 nm half-width of the point-spread function; the rest cannot be real
objects. Two computed tests say what they are instead: they sit *further* from
the resolved particles than uniformly random points do (0.89–0.94×, where real
dim vesicles would cluster with the bright ones), and half of them peak at a
single photon count. `population=resolved` — radius ≥ 106 nm — is therefore the
**primary** population everywhere. `population=all` is carried alongside so the
cut is visible rather than silent; it runs ~60% higher in count and ~40 nm lower
in median radius, and that difference is the photon floor, not smaller vesicles.

**Size is apparent size.** No deconvolution is applied — pixels at face value, as
specified. `radius_nm` is a half-light radius convolved with the ~211 nm PSF
(63×/1.40 NA, 580 nm emission, 1.0 Airy unit pinhole), not a physical vesicle
radius, so summed surface area is an **upper bound**. Most of this population sits
at or just above that limit; the upper tail is the part worth reading, and it is
where Clone1 separates from the others.

**Surface area is exactly four times projected area.** Taking a radius from a
projected area and computing a sphere's surface gives 4A by algebra, so the
spherical assumption contributes a constant factor and nothing else. Membrane
area per OD remains the right unit for comparing against lipid abundance per OD,
but it stays close to a restatement of the count — what makes it differ is
particle size, which is why the size distribution is a figure and not a footnote.

**Ranking stability.** The threshold is a multiple of the measured local noise,
and on the ~100 fields whose background is exactly zero that is zero at every
setting — so the sweep does nothing there, correctly. The three hazy `clon1_1`
fields are the only place the dial moves anything, and the between-strain ranking
does not change anywhere on the sweep. See `vesicle_threshold_sweep.png`.

**OD normalization is cross-experiment.** There is no OD record from the imaging
day. The per-OD columns divide by `research/fabfos/lipidomics/od_values.csv`, which is the
*lipidomics* culture set measured 6 days post-challenge (imaging is 2026-05-22;
the ODs were forwarded 2026-07-08). That table already assumes its replicate
index matches the lipidomics replicate index; using it here assumes further that
it matches the imaging replicate index. pCC1 +toluene is the value to distrust
most: its OD (0.099, 0.103) is the lowest in the table, so normalizing divides by
a very small number.

**n = 2.** Every mean is two biological replicates, and the figures always plot
both points. No significance test is warranted and none is computed.

## Blank frames and the mosaic exclusions

11 of the 103 sample fields are identically zero. Each rep-2 acquisition ends
with one (Series006 in every folder but two) — they are acquisitions of nothing,
and are dropped from all statistics. They also confirm the detector has no
dark-count population, and that is *all* they confirm: a uniformly zero frame
carries no shot noise to trip over, which is why the sample-free control above
does the real work.

`EXCLUDE` in `vesicle_common.py` lists 15 fields rejected by eye when the mosaic
was built; 11 are those blanks. The other four are not empty, and three of them
are the highest-count fields in Clone1/R2/no-toluene. `vesicle_surface_area.csv`
therefore carries both sets: `fov_set=nonempty` drops only the blanks (primary,
used by the figures), `fov_set=mosaic` drops all 15. Only Clone1/no-toluene moves
between them, and it moves a long way — 320 → 75 µm² per 1000 µm² per OD, enough
to change its rank. Which set is right is a judgement about those four images,
not about the code.

## Committed tables vs rendered output

The CSVs are committed — they are what preserves the result. The `.png`, `.html`
and `.svg` renders are gitignored and **not DVC-pinned**, so they have no backup
and exist only until someone reruns the generators. `bakeoff/` holds ~11 MB of
overlays under that rule; its three scorecard CSVs are committed.

Exporting the headline result into the acquisition's own `results/` directory —
what `_old/results_export.py` did — has not been redone for surface area. That
destination is inside a DVC chunk, so it is preserved only by `dvc add
data/fabfos/runs/scadc_microscopy` and committing the changed pin, and it is materialised as
read-only hardlinks once pinned, which is why that script unlinks each target
before writing.

## `_old/`

The superseded count-based chain, its tables and its renders. It thresholded at a
fixed absolute 10/255 and took each connected component's pixel count as its
area, which is adequate for a count and wrong for a size: the pixel count above a
global cut is an iso-intensity contour partway up the spot's flank, so the cut
lands high on a dim spot and low on a bright one. Measured on one field, that
estimator returned median radii of 102, 125, 152 and 203 nm from faintest
brightness quartile to brightest — a 2× swing driven by photon count rather than
size — and discarded 53% of all photons in the image.

Its scale-bar and pixel-pitch errors are fixed in place, so the archived renders
can be regenerated correctly, but nothing there should be used for a new number.
The strain ranking agrees with the current chain at Spearman 0.86; the one large
divergence is Clone1/no-toluene, for the field-set reason above.

`panel_4x4*.py`, `raw_all.py` and `sum_intensity_bar.py` also live there. The
mosaics remain the right figure for showing what the fields look like and still
run. `sum_intensity_bar.py` is superseded for quantification: summed pixel
intensity conflates particle count with particle brightness with autofluorescent
debris, reports arbitrary units, and is not normalized to biomass.

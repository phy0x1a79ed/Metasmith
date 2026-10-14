# Session Debrief — Open Geospatial Dossier

Statement of record: what the project is, what was decided, what was established, what was
produced, and what happens next. Decisions only; no deliberation.

---

## 1. The project

A **query-only open geospatial dossier service**. Input: a polygon and a time. Output: everything
publicly and freely available about that piece of land — imagery across spectral bands, terrain,
derived physical measurements, infrastructure, boundaries, demographics, connectivity, subsurface,
biology — each item tagged with source, resolution, date, licence and provenance.

The product does not analyse, model or recommend. Its value is **curation**: knowing what exists,
being able to reach it, and presenting it coherently with gaps declared.

No committed application. Candidate uses: agriculture; assessing mines and heavy-industry
footprints; forest cover over time. Domain segmentation deliberately deferred.

---

## 2. Decisions

| Area | Decision |
|---|---|
| Cost tier | Free and open sources only. No brokers, no commercial imagery. |
| Resolution | Highest freely available, per layer. No uniform target. |
| AOI geometry | **Polygon** (bounding box is the degenerate case). |
| AOI size | Farm-plot scale as the design target, ~0.1 ha – ~10 km². Continental polygons valid eventually; not planned for now. |
| Time | Single point time; return nearest available observation per layer. Intervals and periodic queries are a later build-up. |
| Licence handling | **Tier it, don't decide it.** Every layer tagged; the query constrains the acceptable licence set. |
| Geographic coverage | No baseline. Return whatever exists for that place. |
| Absence | **Absence is layer-specific, not place-specific.** A query returns a different *subset* of layers by location, not simply more or less data. |
| Declared absence | Mandatory and first-class. Three states per layer: found / searched-and-unavailable (with reason) / not-attempted (with reason). No silent omissions. |
| Output v1 | Materialise eagerly. |
| Output later | Two-stage: return a menu, user selects, then materialise. |
| Primary architecture | **Layer × source matrix.** Layers are semantic slots; sources are providers; cells hold candidate fills. |
| Cell precedence | **Return all fills, ranked; choose none.** Ranking by fill type, resolution, time offset, licence. |
| Fill types | **Three, always labelled: `observed` / `inferred` / `analogue`.** |
| Inference in scope | Yes — as a labelled *source*, never as an analysis step, and never silently substituted for an observation. |
| Extensibility | One plugin module per source. The registry of modules is the asset. |
| Type topology | **Three types only:** `geospatial_query` → N modules → `gis_layer` → aggregator → **`aoi_dossier`**. |
| Query representation | Plain YAML/JSON payload, parsed by each module. **Not** encoded in the type system. |
| Matrix representation | Metadata in the payload, **not** property strings in the type graph. |
| Orchestration | The aggregator requires the layers and decides which modules to run. |
| Execution shape | One query fans out to N independent modules in parallel; each returns data-or-nothing. |
| Metasmith coupling | Unresolved by design — to be settled by measured latency and concurrency from the probe. |

---

## 3. Established findings

**The query layer is a solved standard.** STAC already expresses polygon + time + collection +
metadata filters, with mature client tooling. Build the registry and the vocabulary, not a query
engine.

**Correction level is a fork, not a step.** Orthorectification and atmospheric correction are
already applied in Level-2 products. The project consumes L2; it does not process from raw.

**"Free and open" fragments into incompatible licence tiers** — permissive (Sentinel, Landsat,
Overture, geoBoundaries, AlphaEarth), share-alike (OpenStreetMap, OpenCelliD), noncommercial
(Ookla), and restricted (GADM, WDPA, IHME). Of 316 catalogued modules, 235 are permissive and 231
require no credentials.

**Coverage asymmetry is structural.** Available layers depend on jurisdiction and on acceptable
licence. The response is inherently variable-shaped, which is why the system must be a registry
with per-module coverage probes rather than a fixed pipeline.

**Two originally-requested layers are much harder than they look.** Property lines: ~70–75% of
people worldwide have no formally registered land rights; where cadastre exists it is
per-jurisdiction, and the unifying commercial products are paid. France and Spain publish genuinely
open national cadastres and are the realistic starting points. Cell coverage: no option is
simultaneously measured, global and permissively licensed — tower points are share-alike, modelled
coverage is a tower-buffer approximation, and the only measured product is noncommercial.

**No cross-domain aggregator exists.** Single-source bounding-box extractors are abundant and every
domain has libraries. Nothing runs all of them for one AOI and returns a single provenance-tagged
dossier with declared gaps. The gap is integration and curation, not invention — which is both the
opportunity and the warning: there is no technical moat, only the registry.

### AlphaEarth

**The decodable set is enumerable from the model's training-target table, not chosen arbitrarily.**
Inputs at inference are Sentinel-2 L1C, Landsat 8/9 L1C and Sentinel-1 GRD. Everything else is
target-only and therefore genuinely imputed: ALOS PALSAR L-band, Copernicus GLO-30 elevation, GEDI
canopy height metrics, ERA5-Land climate, GRACE water storage, NLCD land cover, and Wikipedia and
GBIF text embeddings.

**Decoders exist in the model but not in the public release.** They are timecode-conditioned and
spatially continuous — the paper's own example is dense superresolved GEDI lidar profiles from
sparse footprints. The public artifact is the 64-dimension annual embedding only.

**Predictive rule for which layers AlphaEarth can fill:** a layer is well-imputable to the degree
it resembles a decode target. Confirmed by the fact that the best-regressing variables in
independent work — temperature and elevation at R² ≈ 0.97 — are exactly ERA5-Land and GLO-30.

**The boundary is principled.** AlphaEarth can fill cells whose value is a physical property of the
land surface causally expressed in reflectance or backscatter. It cannot fill cells whose value is
a legal or administrative fact. Infrastructure geometry is visible and detectable; its attributes
are not.

**Mandatory caveats:** the public product is annual, so no per-date imputation; ERA5-Land and GRACE
are decoded from ~11 km to 10 m, a ~1000× disaggregation that is not a measurement; inferred values
are not independent of the observed layers they derive from, so they must never be used to validate
them; NLCD is US-only, so global land-cover decoding carries US semantics.

**Similarity search works and is nearly free** — embeddings are unit-length, so similarity is a dot
product — but it is a *reverse* query needing a prebuilt index, and is therefore a separate product
mode rather than part of the dossier.

### Analogue fills

A third fill type, and the project's most distinctive technical idea. A large class of layers
exists only as sparse point samples and is therefore absent for almost every AOI. Using AlphaEarth
embeddings as a shared environmental coordinate system, a **donor index** (each point observation
joined to the embedding at its coordinate and year) allows retrieval of environmentally-matched
donors for AOIs with no local sample, returned with similarity score, donor distance, donor count
and uncertainty.

Embedding distance is preferred to geographic distance because it is distance-agnostic and encodes
the covariates that drive these variables. A donor-only index is computationally trivial — ~10⁵
samples × 64 dimensions is tens of megabytes and a query is one matrix multiply.

**"Closest" is a per-layer choice and the metric must follow the layer's causal structure:**
environmentally determined layers suit embedding metrics, with an ARD-kernel Gaussian process the
most defensible default because it learns per-dimension length-scales and returns calibrated
uncertainty; point-source determined layers (PFAS, industrial contaminants) are driven by proximity
to a facility, so embedding similarity is close to the wrong metric; institutionally determined
layers must have analogue fills **disabled outright**; and augmenting the embedding with covariates
it cannot see (soil pH and texture, lithology, sample depth) is likely a substantial gain for soil
biology in particular.

**Constraints:** evaluation must hold out whole spatial blocks; the baselines to beat are
geographic-nearest and covariate-nearest; sampling bias caps achievable quality, and where no good
analogue exists the correct output is a quantified low similarity score rather than a confident
borrowed value; functional profiles transfer better than taxonomic composition; and the embedding
is annual, 10 m and surface-weighted while a soil core is a point at depth on a date.

**This reframes AlphaEarth's role** from "one more raster" to the **join key** — the shared space
in which sparse observations from unrelated sources become comparable and transferable.

---

## 4. Verified endpoints

Four endpoints were called, not recalled:

| Module | Confirmed |
|---|---|
| `macrostrat` | `lat`/`lng` → geologic units. At 52.10 N 5.25 E: 2 units, lithology "sedimentary rocks", "Cenozoic sedimentary rocks", 0–66 Ma. The best coordinate→geology API available. |
| `eq_catalog` (USGS FDSN) | Bounding box + start time + minimum magnitude, GeoJSON out. 342 events in a ±1.5° Dutch box since 1980 at M≥1.5; largest M5.4 near Kessenich, Belgium at 21.2 km depth. |
| `mgnify` | `latitude_gte`/`longitude_gte` (underscores) filter correctly. 337 samples in a ±0.6° Dutch box. Global pools: 29,823 terrestrial-soil; 30,862 terrestrial; 29,152 plant-associated; 87,553 environmental. |
| `ena_geo` | `query=geo_box1(lat1,lon1,lat2,lon2)`. The gateway to any geolocated INSDC sequencing sample, not only microbiome. |

**A 200 is not verification.** MGnify returns HTTP 200 and well-formed JSON for unknown query
parameters, silently ignoring the filter and serving the unfiltered catalogue: hyphenated
`latitude-gte` returned 435,812 records, exactly matching a deliberately nonsense parameter, while
`latitude_gte` returned 14,979. The hyphenated response looked plausible — every record simply had
a null latitude and came from unrelated biomes. **Every filter must be tested against a
nonsense-parameter control; the pass criterion is a differential count.**

Metadata quality in record-level sources is uneven: one ENA sample inside the Dutch box is labelled
as United Kingdom. Trust the coordinate; flag the conflict.

---

## 5. Deliverables

| File | Contents |
|---|---|
| `geospatial-dossier-seed.md` | Project context document: decisions with rationale, domain findings, matrix architecture, analogue-fill design, AlphaEarth decode table, verified endpoints, deferred questions, probe spec, and a ~200-term glossary. |
| `geolocatable_data_registry.md` | Master registry: 316 candidate modules across 35 groups in 3 batches, with layers, resolution, temporal coverage, licence, access route, auth and priority. |
| `candidate_modules_all.csv` | The same registry, machine-readable — the probe's input and the registry's seed. |
| `candidate_modules.md` / `.csv` | Batch 1 alone (119 modules, core EO). |
| `candidate_modules_batch2.csv` | Batch 2 alone (99 modules, atypical modalities). |
| `candidate_modules_batch3.csv` | Batch 3 alone (98 modules, record-level geolocated data). |
| `session-debrief.md` | This document. |

### Registry composition

| Batch | Modules | Scope |
|---|---|---|
| 1 | 119 | Core EO, climate, terrain, land cover, vector basemap |
| 2 | 99 | Atypical physics and modality: geophysics, deformation, marine, deep time, ground-level, activity streams, industry registries |
| 3 | 98 | Record-level geolocated data: geology maps, sequences, health, contamination, economics, knowledge |

30 modules at priority 1; 72 at 2; 118 at 3; 96 at 4. 235 of 316 permissively licensed; 231 need no
credentials.

### Priority-1 modules

`sentinel2_l2a` · `landsat_c2l2` · `sentinel1_grd` · `modis_bio` · `copernicus_dem` ·
`terrain_derived` · `soilgrids` · `era5` · `esa_worldcover` · `hansen_gfc` · `jrc_gsw` · `ghsl` ·
`worldpop` · `overture` · `osm_overpass` · `geoboundaries` · `alphaearth` · `egms` ·
`gem_trackers` · `cmems` · `gebco` · `macrostrat` · `mgnify` · `ena_geo` · `ihme_lbd` ·
`pfas_ucmr` · `wqp` · `nwis` · `census_micro` · `wikidata_geo`

### Notable registry findings

- **`modis_bio` and `cgls` have the best effort-to-value ratio** — one adapter each yields many
  biophysical layers (LST, vegetation indices, LAI/FAPAR, evapotranspiration, productivity).
- **Landsat is the only free global source of 30 m surface temperature.** Sentinel-2 has no thermal
  band.
- **`ghsl` provides global building height**; Google Open Buildings 2.5D Temporal provides building
  height as a time series across the Global South.
- **`egms` is the first continental open InSAR deformation service** — ~3 mm/yr detection, directly
  applicable to mining subsidence. It measures motion rather than reflectance.
- **Airborne gamma-ray spectrometry** maps potassium, uranium and thorium in the top few
  centimetres — spectral, but in a band region unrelated to optical EO, and a mining staple.
  Australia, Canada and the US publish openly.
- **Declassified satellite imagery extends change detection four decades before Landsat MSS** —
  CORONA at 1.8–2.7 m from 1960, KH-9 panoramic at 0.6–1.2 m, public domain, with stereo pairs
  supporting historical DEMs.
- **Global Energy Monitor is an asset-level heavy-industry registry** — 25 trackers, 200+ countries,
  CC-BY — directly serving the mining and heavy-industry use case.
- **Mapillary provides ground-level imagery**, orthogonal in viewpoint to every nadir source, with
  object detections usable as a free vector layer.
- **`wikidata_geo` is the broadest single semantic layer** — millions of coordinate-bearing entities
  under CC0, SPARQL-queryable.
- **On hyperspectral:** the honest answer is EMIT (285 bands, free, partial targeted coverage) and
  EnMAP/PRISMA (free with registration, sparsely tasked). There is no free global hyperspectral
  layer — a genuine gap, not an oversight.
- **US regulatory and statistical data is exceptionally deep** — Water Quality Portal, NWIS, EPA
  FRS/TRI/ECHO, UCMR5 measured PFAS, census block-level demographics, LODES origin-destination
  commuting flows, HMDA lending.

---

## 6. Deferred, with reasoning recorded

- Domain/application segmentation.
- Continental-scale AOIs (valid eventually; avoid foreclosing them).
- Time intervals and periodic queries.
- Metasmith coupling — to be settled by probe measurements.
- Per-layer analogue metrics — the project's genuine research component.
- Which layers may never use analogue fills — needs writing down before the mechanism is built.
- The layer vocabulary's granularity — now the primary matrix axis; settle it from real fills.
- Output alignment semantics (common grid versus native resolutions).
- Caching.
- Similarity search as a second product mode.

---

## 7. Next step

**Breadth probe across five contrasting polygons**, producing one layer × source matrix each:

1. Dutch farmland — likely the global maximum for open data richness.
2. Iowa cropland — NAIP, 3DEP lidar, county parcels, CDL crop history.
3. An open-pit mine — tests the mining use case in a data-moderate jurisdiction.
4. An Amazon plot — tests forest-change layers in a data-sparse jurisdiction.
5. Mid-Pacific ocean — **not** a null case; should return a rich marine dossier and an empty
   terrestrial one, testing that layer families switch by location.

Input is `candidate_modules_all.csv`, starting with the 30 priority-1 modules. For each module ×
AOI record: existence, resolution, nearest date to query time, licence, access method and endpoint,
payload size, retrieval wall-clock time, and any blocker. Failures and absences are recorded as
carefully as successes — they populate the declared-absence logic.

**Pass criterion: a differential count against a nonsense-parameter control, never an HTTP 200.**

Secondary objectives: resolve whether the AlphaEarth bucket is public or requester-pays (sources
conflict), and collect the per-module latency and concurrency figures that decide the Metasmith
coupling question.

**Deliverables:** a machine-readable layer × source matrix per AOI, and a written assessment of how
severe coverage asymmetry actually is, which modules are worth the integration effort, and whether
the fan-out is latency-bound enough to rule out a heavyweight task scheduler.

---

## 8. Accuracy status of the registry

Group, source, layers and licence tier are reliable. Exact endpoints, collection ids and precise
licence terms are **probe targets** except for the four verified modules in §4. Rows whose notes
field says VERIFY are known-uncertain. The registry was assembled from general knowledge of the
open-geodata ecosystem, not derived systematically from any literature — geology and geophysics
were the thinnest areas in the first pass and were expanded deliberately in batches 2 and 3.
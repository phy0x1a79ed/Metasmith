# Pilot POC — AOI list to feature set per AOI

**Question asked:** what fraction of catalogued sources is actually reachable, and does the
AOI -> feature-set pipeline work end to end on a comprehensive source set?

## Headline

| Measure | Sister sessions (triage) | This POC |
|---|---|---|
| Sources reachable | 57 / 149 probed = **38%** | 71 / 76 adapters returning data = **93%** |
| Semantic slots with a reachable source | 52 / 103 = **50.5%** | 53 / 56 implemented slots; 88/103 verified reachable = **85%** |
| Fetches returning features | not measured | 795 / 869 attempted = **91%** |
| Features per AOI | none produced | **544–596** (814 distinct across 15 AOIs) |

The triage's 38% was never a property of the data ecosystem. **61% of its failures were this
sandbox's network allowlist**, not the sources: 57 of 92 non-reachable candidates failed with a
proxy 403 or refused CONNECT tunnel. Once the blocked hosts were granted, re-probed or routed
around, the same sources answered.

## What moved the number

1. **Re-probing stale blocks** (+13 slots). The triage was days old; the allowlist had moved under
   it. 18 of 95 recorded-blocked hostnames answered on re-probe, including ECCC GeoMet (104
   collections), the StatCan ESRI services, `ftp.maps.canada.ca` and the JRC GHSL mirror.
2. **Catalogue mirrors** (+5 unique slots). One allowlisted STAC catalogue replaces dozens of
   per-agency portals: 249 collections enumerated across Planetary Computer, the NRCan datacube,
   NASA CMR and NOAA NCEI, of which 27 were verified by real reads with controls.
3. **Static published archives** (+9 unique slots). For asset-level and point data a sharded bulk
   archive beats per-AOI API calls — 40 candidates verified across 19 slots, with `/vsicurl` range
   reads proving a 116 MB Zenodo GeoPackage is usable without downloading it.
4. **General-purpose vector/semantic sources** (+3 unique slots). Wikidata SPARQL fills 9 slots
   with one adapter; Overture Maps GeoParquet replaced Geofabrik extracts after measurement showed
   the needed OSM shapefiles total 6.8 GB and omit power, pipeline and address layers entirely.

Overpass is **not** a dependable leg here: measured over 84 attempts it answered 19% of the time
per attempt (62% per query with retries, median 1.68 s). Overture carries those slots instead.

## Reachability by family

Loss was never uniform. The institutional families fail on the allowlist; the physical families
fail, when they fail, for real reasons.

| Family | Slots filled (triage) | Share of failures that were network, not source |
|---|---|---|
| Spectral | 6/8 | 100% |
| Water bodies | 5/7 | 50% |
| Macrobiology | 7/11 | 57% |
| Geology | 7/12 | 33% |
| Hazards | 9/17 | 56% |
| Infrastructure | 6/14 | 64% |
| Public health & microbiology | 3/8 | **90%** |
| Climate | 2/6 | 20% |
| Socio-economic | 5/15 | **76%** |

Climate is the one family that is genuinely hard rather than blocked — CDS registration walls and
Zarr/NetCDF access patterns, not 403s.

## Pipeline performance

- 1 110 fetches (15 AOIs × 74 adapters) in **191 s** wall at 8 threads; 101 s of serial fetch per AOI.
- Median fetch 0.40 s; the distribution is long-tailed — large static archives dominate first use,
  then cache (GHS-POP first touch 32.9 s, median 8.6 s once the tile handle is open).
- Total adapter cache footprint ~190 MB across all lanes.
- Feature matrix 15 × 662, 62% dense. The sparsity is **structural, not failure**: 271 of 1 110
  cells are country- or province-scoped adapters correctly declining out-of-coverage AOIs.

## Defect found and fixed

The shared raster reader masked every zero-valued pixel on sources that declare no nodata — a
boundless+masked read treats the fill value as nodata. Hansen tree cover read **50.6%** instead of
the true **22.2%** over one AOI, and all-dry surface-water windows raised "all pixels nodata"
instead of returning zero. The reader now clips the window to the raster footprint and masks only
*declared* nodata. Any earlier figure from `jrc_gsw` or `hgb` is suspect; the final run is not.

## Embeddings — the analogue-fill join key

The first run filled this slot for 5 of 15 AOIs. Diagnosis: not a pipeline fault. Clay v0 publishes
**1 170 MGRS tiles of ~57 000 land tiles (2.1%)**, measured by listing the bucket; the 10 misses
were `LookupError: no Clay embedding tile for MGRS <id>`. Since embeddings are the shared coordinate
system the analogue-fill design depends on, partial coverage is worse than none — the imputation
would silently vanish exactly where sparse layers are missing.

Two routes were pursued in parallel.

**A keyless AlphaEarth mirror exists.** Google's Satellite Embedding V1 (AlphaEarth Foundations) —
the archive the seed session's design already assumed — is mirrored as plain-HTTPS COGs at
`data.source.coop/tge-labs/aef`: 64-dim, unit-length, 10 m, annual 2017-2025, CC-BY-4.0, no
credentials. Earth Engine's OAuth route is not the only one. Measured coverage over 6 000
area-weighted random global land points using the publisher's index polygons: **100.00% of 5 535
non-Antarctic points**, 83.4% of 465 Antarctic points, 98.72% overall; 12/12 remote spot locations
returned valid unit-norm embeddings on real reads. Two traps had to be handled: the COGs are
bottom-up and the publisher's corrective sidecar VRTs hard-code a `/vsis3` source needing AWS
credentials (so the adapter derives the north-up affine itself, validated at r=+0.985 against ESA
WorldCover water fraction on a Lake Ontario transect), and values are int8-quantised requiring
`(v/127.5)²·sign(v)`, after which every valid pixel has L2 = 1.000 exactly — reused as a validity test.

**A deterministic fallback was built** in case no archive was globally complete: a 30-dimensional
spectral-temporal signature from four seasonal Sentinel-2 scenes (per-band temporal quantiles, index
medians and amplitudes, within-AOI texture). It is not a learned embedding, carries no SAR, climate
or text targets, and is labelled as such. It reaches 15/15 because Sentinel-2 does.

**Both were validated as join keys**, which coverage alone does not establish. Cosine similarity
across the 15 AOIs, comparing AOI pairs of the same class against different classes, plus the four
pairs that are the same place at two scales (HVC mine, oil sands, Toronto, and the adjacent
Windsor/Detroit pair):

| Source | AOIs filled | dim | within-class | between-class | separation | same-place mutual 1-NN |
|---|---|---|---|---|---|---|
| **AlphaEarth v1** | **15/15** | 64 | +0.637 | +0.361 | **+0.276** | 3/4 |
| S2 signature (whitened) | 15/15 | 30 | +0.270 | +0.167 | +0.103 | 3/4 |
| Clay v0 | 5/15 | — | — | — | — | — |

The fallback also demonstrated why normalisation choice matters: unit-normalising raw positive
reflectance features gave within-class 0.9453 vs between-class 0.9450 — **separation +0.0002, no
usable signal**, because every vector points along the shared mean-brightness direction. Z-scoring
against reference statistics from 28 Sentinel-2 boxes spread across North America (baked into the
module) lifted separation to +0.103. AlphaEarth needs no such correction.

All three sources are retained in the slot, ranked, per the project's "return all fills, choose
none" rule — so the 10 Clay v0 misses still appear as declared `unavailable` rows rather than being
deleted, which is why the embeddings family reads 78% in the coverage figure while the slot itself
is filled for every AOI.

**Caveats:** the AlphaEarth mirror is explicitly unsupported by Google; coverage figures are
point-sampled (n=6 000, ±0.3 pp) rather than exhaustive over all 34 149 tiles; Antarctic interior
coverage is partial; and Major TOM embeddings on Hugging Face were never measured because that host
is off-allowlist, so their row in `embedding_candidates.csv` is an unverified claim, not a finding.

## What still does not work

| Slot | Source | Why |
|---|---|---|
| `ground_level_imagery` | Mapillary, KartaView | Both token-gated; no keyless route exists. No key embedded. |
| `crop_type_ca` | AAFC Annual Crop Inventory | Host reachable but `/atlas/rest` returns 404 on both AAFC domains; the triage recorded this source as reachable **without persisting the endpoint URL** — a reproducibility gap in the triage schema. |
| `infrastructure_osm` | Overpass | 19% success through this proxy; superseded by Overture. |
| `census_demography` (US income/age) | Census ACS | Hard API-key wall. TIGERweb decennial counts used instead. |
| `property_assessment` | Quebec/Montreal open data | Host not granted; adapter records the block. |

## Caveats that travel with the numbers

- Admin-aggregate features (CDC state/county, PHAC province, StatCan census subdivision) are
  jurisdiction statistics joined to the AOI, not AOI measurements. They are labelled
  `res_m='admin:<level>'`.
- US emissions report TRI/CAA/RCRA reporter **counts**, not tonnages: EPA Envirofacts is off-host
  and its geometry filter provably does not filter. Canadian NPRI does carry release masses.
- LODES commute flows are within-state only, which understates the Detroit/Windsor border AOIs.
- `field_boundaries` is US-only; `embeddings` covers 5/15 AOIs; `gamma_radiometrics` 3/15 (survey
  gaps); `glaciers` is a 1:10M generalised extent, provisional below ~10 km.
- The mid-Pacific control box is not empty — it clips the atoll Vairaatea (30 road segments, 41
  buildings), so Overture differentials are measured against a non-zero baseline.
- Raster features are decimated samples capped at 320 px per side, not full-resolution zonal stats.

## The portability point

Every number above is bounded by **this sandbox**, not by the product. The pipeline uses no
credentials, no connectors and no vendor SDK — `requests`, `rasterio`, `pystac_client`, `geopandas`
against public HTTPS. The 16 host grants this session needed are an artifact of the sandbox
allowlist; on an ordinary machine there is no allowlist and those hosts simply resolve. Mid-session
the sandbox was rebuilt and silently dropped its grants, which re-broke 119 fetches — a useful
demonstration that `unavailable` must be a first-class declared state rather than an error, because
reachability is environmental and changes under you.

## Next steps

1. Promote the five failing adapters: find the AAFC endpoint (or drop the source and record it),
   decide whether `ground_level_imagery` is worth a token.
2. Resolution honesty: replace decimated sampling with full-resolution zonal statistics for the
   slots where it matters (land cover fractions, crop type), keeping decimation for stress AOIs.
3. Implement the `inferred` fill type behind the same declared-absence contract, starting with the
   AlphaEarth decode targets the seed session enumerated.
4. Cost model: the per-AOI serial cost is 101 s against a 15 s/sample budget from the scaling
   session. Parallelism already covers it (12.7 s/AOI wall at 8 threads), but a 10k-AOI run needs
   the static-archive adapters sharded by province/state rather than cached per process.

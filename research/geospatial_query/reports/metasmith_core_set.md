# Metasmith core layer set — scale decision

Scope: fixing the layer set that metasmith integrates by default, judged by what happens
when the pipeline is run over thousands of AOIs across North America rather than the 12
test AOIs. Built from the optimize session's artifacts (`core_set_north_america.csv`,
`pathfinder_calibration.csv`, `core_set_validation.csv`, `disk_network_model.csv`) plus one
new direct measurement of the NRCan S3 endpoint described in §2.

---

## 1. The ~15 s figure is a per-read number, not a per-sample number

The optimize session's two statements are both about a single COG window read, which is why
they look contradictory:

- **14.1 s** was one read — a 4 km² window of 1 m HRDEM pulled out of an 898 GB national COG.
  It moved 33.9 MB at 2.4 MB/s. The same layer over a 0.65 km² farm AOI took **1.59 s**.
- "Latency is not the constraint" is true at the level of one read: the median across 139
  probe reads was **0.92 s**, p95 **4.0 s**.

Neither is the cost of a sample. A dossier is **23 fetches** — 20 raster windows plus three
point queries — so per AOI, run serially:

| | |
|---|---|
| per-AOI wall-clock, serial | **33.6 s** |
| of which fixed per-read overhead | **29.6 s (88%)** |
| of which actual byte transfer | 3.9 s |
| bytes fetched | **217 MB** |
| bytes retained after clipping | **4.7 MB** (46× block amplification) |

So the honest restatement is: a sample costs ~34 s serial, roughly double the number quoted,
and almost all of it is per-request overhead rather than data movement. That overhead is
embarrassingly parallel, which is why it stops mattering — see §2.

A read-time model fitted to the 139 validated probe reads separates the two hosts cleanly:

| host | fixed cost per read | per-connection throughput | n |
|---|---|---|---|
| NRCan datacube (AWS S3, ca-central-1) | 0.56 s | 10.4 MB/s | 112 |
| Planetary Computer (Azure) | 2.18 s | 128 MB/s | 27 |

Planetary Computer is latency-dominated (STAC search + SAS signing); NRCan is
throughput-dominated.

---

## 2. What actually binds at scale — measured

I re-probed the NRCan endpoint directly rather than inferring it. Against the MRDEM-30 DTM
(**83.85 GB**, `Accept-Ranges: bytes`, 206 on every range request), reading 1 MiB ranges:

| concurrent requests | median request | aggregate throughput |
|---|---|---|
| 1 | 0.139 s | 4.6 MB/s |
| 8 | 0.165 s | 30.0 MB/s |
| 32 | 0.600 s | 47.8 MB/s |
| 64 | 1.102 s | **55.7 MB/s** |
| 128 | 1.999 s | 56.1 MB/s |

Two results:

1. **A warm pooled connection serves a 1 MiB range in 0.139 s.** The 0.56 s fixed cost in the
   fitted model is therefore mostly STAC search, token handling and COG header/overview reads —
   per-AOI work that is in principle hoistable out of the loop, not an irreducible network cost.
2. **Aggregate egress saturates at ~56 MB/s around 64 workers.** Doubling to 128 workers
   doubles per-request latency and adds nothing. This is the ceiling that governs the build.

At that ceiling the arithmetic is simple and unflattering to the per-read optimisations:
**every build of ≥1000 AOIs is bandwidth-bound, not latency-bound.** Tuning request overhead
buys nothing until the pipeline runs on a fatter link.

---

## 3. How the methods stack up across thousands of AOIs

64 workers throughout. "As-probed" uses the fitted per-read overheads; "tuned" assumes STAC
items, COG headers and SAS tokens are cached across AOIs so each read costs the measured
0.139 s floor.

**Wall-clock, hours, on the measured 56 MB/s link:**

| strategy | MB/AOI | s/AOI | 1k | 5k | 10k | 50k |
|---|---|---|---|---|---|---|
| A. as-probed, full stack | 201 | 26.9 | 0.99 | 4.97 | **9.94** | 49.7 |
| B. as-probed, AlphaEarth opt-out | 53 | 23.6 | 0.26 | 1.31 | **2.63** | 13.2 |
| C. tuned, full stack | 201 | 8.6 | 0.99 | 4.97 | 9.94 | 49.7 |
| D. tuned, AlphaEarth opt-out | 53 | 7.3 | 0.26 | 1.31 | 2.63 | 13.2 |
| E. tuned + cache-once small archives | 51 | 6.8 | 0.31 | 1.31 | 2.57 | 12.6 |

A→C and B→D are identical: on this link the pipe is full either way. The only lever that moves
wall-clock is **bytes per AOI**.

**On an in-region VM (1.25 GB/s), the binding constraint flips to latency** and the tuning
earns its keep — 10k AOIs: 1.17 h as-probed vs **0.29 h** tuned-and-opted-out.

Volumes, for planning:

| | 1k AOIs | 5k | 10k |
|---|---|---|---|
| transferred, full stack | 0.22 TB | 1.08 TB | 2.17 TB |
| transferred, AlphaEarth opt-out | 0.07 TB | 0.35 TB | 0.69 TB |
| **retained on disk after clipping** | 4.7 GB | 23 GB | **47 GB** |

Data egress itself is free — both NRCan's buckets and Planetary Computer serve public data
without requester-pays — so the cost is wall-clock and compute, not transfer fees.

---

## 4. The one decision that matters: AlphaEarth

AlphaEarth's 64-band embedding is **148 MB of the 217 MB per-AOI payload — 68%** — and it is
flat across AOI size because 64 bands at 10 m hit the COG block floor regardless. Including it
by default multiplies the 10k-AOI build from 2.6 h to 9.9 h and from 0.69 TB to 2.17 TB.

It is also the least-settled layer in the set: `reachable = no`, zero confirmed pixel reads
across the 12 test AOIs, and the public-vs-requester-pays bucket question still open after two
probe waves.

**Recommendation: AlphaEarth is opt-in, not default.** It earns its cost only on builds that
actually use analogue fills, where it is the join key. Everything else in the core set fits in
a 2.6-hour overnight run at 10k AOIs.

---

## 5. Cache-once versus stream-per-AOI

The intuition that thousands of AOIs justifies downloading the national archives is wrong for
almost every layer. Both streaming and caching are limited by the same pipe, so the crossover
is a pure byte ratio: `archive_size / per_query_bytes`.

| layer | archive | per-AOI fetch | crossover | verdict at 1k–10k AOIs |
|---|---|---|---|---|
| ghsl_built_s | 49 MB | 0.10 MB | 489 | **cache** |
| nrcan_insar | 11.6 GB | 2.31 MB | 5,012 | **cache** |
| aafc_aci | 1.13 GB | 0.10 MB | 11,300 | cache (archive is trivial) |
| mrdem_30 | 83.9 GB | 2.85 MB | 29,421 | stream |
| nrcan_landcover | 2.11 GB | 0.07 MB | 30,143 | stream (but 2 GB — cache anyway) |
| rcm_ard | 104 GB | 1.65 MB | 62,879 | stream |
| hrdem_1m | 404 GB/tile | 3.77 MB | 107,064 | stream — and it cannot be cached whole |
| cwi_wetland | 5.40 GB | 0.02 MB | 270,000 | stream (but 5 GB — cache anyway) |

Operating rule for metasmith: **cache any archive under ~15 GB unconditionally** (the disk is
noise and it removes per-AOI network entirely), **stream everything above it** until the build
exceeds ~30k AOIs. Sentinel-2, Landsat and the other Planetary Computer collections are
petabyte-scale and are never candidates for caching.

The cache-once constructor tier is separate and unambiguous: Maus mine polygons (23.5 MB),
TIGER boundaries (84 MB), CanSIS soils (53 MB), StatCan tables (all < 5 MB). Fetch once, hold
locally, never touch the network per AOI.

---

## 6. Final core set

The full table with per-layer evidence is in `layer_decision_table.csv`. Summary:

**Stream per AOI — pixel-confirmed, in the default stack (9 rasters + 3 point APIs)**
`mrdem_30` (10/12 AOIs) · `sentinel2_l2a` (12/13) · `landsat_c2l2_st` (13/13) ·
`nrcan_landcover` (9/12) · `nrcan_surface_water` (9/12) · `nrcan_flood_susc` (9/12) ·
`nrcan_veg_params` (9/12) · `nrcan_snow` (7/12) · `rcm_ard` (9/12) · plus the three verified
point APIs (Macrostrat, USGS FDSN, MGnify).

**Cache-once, no per-AOI network (small archives + constructors)**
`nrcan_insar` · `ghsl_built_s` · `aafc_aci` · `cansis_slc` · `maus_v2` mine polygons ·
`tiger_boundaries` · `cchs_health_region` · StatCan tabular. Combined footprint ~12 GB.

**Conditional — present, but not everywhere**
`hrdem_1m` (6/12 AOIs; absent at Saskatoon, Taber, Highland Valley — i.e. exactly the prairie
farm and BC-interior mine cases) and `cwi_wetland` (5/12). Request opportunistically, record
absence, never block a dossier on them. MRDEM-30 is the universal DEM.

**Opt-in**
`alphaearth` — see §4.

**Blocked on integration, not on coverage — must be resolved before the set is final**
Five Planetary Computer layers failed at every AOI for reasons that are not data absence:

- `esa_worldcover`, `io_lulc`, `sentinel1_rtc` — HTTP **409** from Azure blob storage, i.e. the
  container requires a SAS token from the PC token endpoint and the adapter was not signing.
- `cop_dem_glo30`, `gnatsgo` — **CURL CONNECT tunnel failed, 403**, i.e. the sandbox network
  allowlist, not the provider.

Both are one-line fixes in the adapter/environment. Until they pass a pixel read these five
layers are *unverified*, not *absent* — and `usda_cdl` returning no-item at all 13 AOIs is the
known footprint-vs-presence artefact from the optimize session, not a coverage fact.

**Deferred**: the 12 `portal-manual` slots and provincial parcel fabric, unchanged from the
previous session's recommendation.

---

## 7. Engineering consequences

1. **Run the build in ca-central-1, next to the NRCan buckets.** This is the single highest-value
   change: it removes the 56 MB/s ceiling that currently makes every strategy identical, and
   only then does per-read tuning convert into wall-clock.
2. **Cap concurrency at 64.** Measured: 128 workers doubles per-request latency for no
   throughput gain, and it is impolite to a public bucket.
3. **Hoist per-collection metadata out of the per-AOI loop.** STAC item geometry and COG headers
   for single-national-COG collections (MRDEM, land cover, wetland, RCM) are static; fetching
   them once instead of per AOI is what takes the per-read cost from 0.56 s toward the measured
   0.139 s floor. Worth ~20 s/AOI, but only on a fast link.
4. **No heavyweight scheduler.** The workload is a flat fan-out of independent, latency-tolerant
   reads with a hard bandwidth ceiling; a connection-pooled thread pool with a token bucket is
   sufficient.
5. **Store clips, not fetches.** 10k AOIs is 2.17 TB over the wire but **47 GB** on disk.
6. **Batch AOIs by block where they cluster.** A 512-px block of a 30 m layer is 15.4 km across,
   so co-located AOIs (a mining district, an agricultural region) share block fetches. The gain
   depends on the spatial distribution of the actual AOI list and has not been quantified here.

---

## 8. Caveats

- The 56 MB/s ceiling and the 0.139 s request floor were measured from this sandbox against one
  endpoint (NRCan S3, ca-central-1). The Planetary Computer link was not re-probed; its fitted
  overhead comes from 27 reads in the previous session.
- Per-AOI byte figures are derived from TIFF block geometry with measured compression ratios,
  not counted on the wire — the previous session's caveat carries forward.
- The per-AOI model covers the 20 raster layers in `disk_network_model.csv` plus three point
  queries. Vector and archive layers are assumed cached and contribute no per-AOI network.
- Coverage counts are over 12–13 test AOIs. They establish that a layer is present somewhere and
  absent somewhere, not a national coverage fraction.
- Nothing here re-tests the 48 sources that were still network-blocked after two probe waves.

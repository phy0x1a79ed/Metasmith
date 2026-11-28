# geospatial_query discussion stack

Goal: build the MVP POC promised to Koonkie and run it on their test AOIs.
Decisions: docs/geospatial_query/DECISIONS.md

Email content stays out of this repo, journals and commits. Koonkie's AOI KML is data under no NDA and is DVC-tracked (aoi-handling). Source: the KML Koonkie sent on 2026-11-12.

## Current
deliverable: send Tomer the 0.26.3 dataset (mmap_canada_mining pin aa39d2f4), both dictionaries, the driver on `release` and metasmith 0.26.3. The message draft waits for the user's review.

## Waiting on the user
- census-db: StatCan 2021 dissemination-block files sit behind a Cloudflare challenge; census runs on dissemination areas until the block files are staged (2021_92-151_X.zip, ldb_000b21a_e.zip).
- rvdss-regions: outside QC/ON/BC PHAC publishes only SARS-CoV-2 at province level; add region-level virus rows?

## Preferences
- 2026-11-17: discuss before building; drafts go to the user before anything is sent
- 2026-11-19: pipeline ingests one AOI table and writes one table per source; metasmith scatter-gather DAG; dataset id mmap_canada_mining
- 2026-11-27: feature definitions come from the original sources, quoted with a URL, or stay blank; never written by us
- 2026-11-27: the driver takes a Nextflow config and params; Tomer writes his own config, ours ships only as an example

## Stack
- deliverable: send Tomer the 0.26.3 dataset, dictionaries, driver and release
- probed-features: adapters for the 152 probed features
- query-time: build Query.time after the fixes; selects time-indexed editions per source (decision source-pinning)
- postgis-loader: whether the tool ships a PostGIS loader
- packaging: standalone open-source CLI vs metasmith workflow
- country-coverage: parked unless Tomer raises it again
- claude-plan: follow up with Hallam (not build work)

## Workers
none

## Closed
- osm (2026-11-27)
- fixes-plan (2026-11-27): plan 03-dictionary-fixes.md, metasmith 0.26.3
- class-column (2026-11-27)
- feature-renames (2026-11-27)
- source-pinning (2026-11-27)
- ghsl-urban (2026-11-27)
- rvdss-aggregate (2026-11-27)
- phac-wastewater (2026-11-27)
- census-multi-csd (2026-11-27)
- reply-tomer (2026-11-17)
- aoi-handling (2026-11-19)
- mvp-build (2026-11-19)

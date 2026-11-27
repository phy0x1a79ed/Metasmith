# geospatial_query discussion stack

Goal: build the MVP POC promised to Koonkie and run it on their test AOIs.
Decisions: docs/geospatial_query/DECISIONS.md

Email content stays out of this repo, journals and commits. Koonkie's AOI KML is data under no NDA and is DVC-tracked (aoi-handling). Source: the KML Koonkie sent on 2026-11-12.

## Current
deliverable: ready to send Tomer. mmap_canada_mining is in the driver's CSV layout and DVC-pinned, the driver runs on metasmith 0.26.1 (3-AOI run matched the dataset, 2026-11-26), nothing has gone to Tomer yet

## Waiting on the user
none

## Preferences
- 2026-11-17: discuss before building; drafts go to the user before anything is sent
- 2026-11-19: pipeline ingests one AOI table and writes one table per source; metasmith scatter-gather DAG; dataset id mmap_canada_mining

## Stack
- deliverable: send Tomer the dataset, the driver on feat/dev and metasmith 0.26.1 (convert, do not rerun)
- probed-features: adapters for the 152 probed features
- query-time: build Query.time after the MVP
- postgis-loader: whether the tool ships a PostGIS loader
- packaging: standalone open-source CLI vs metasmith workflow
- osm: get OpenStreetMap working (Tomer asked)
- country-coverage: parked unless Tomer raises it again
- claude-plan: follow up with Hallam (not build work)

## Workers
none

## Closed
- reply-tomer (2026-11-17)
- aoi-handling (2026-11-19)
- mvp-build (2026-11-19)

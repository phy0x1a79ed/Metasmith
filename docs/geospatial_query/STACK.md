# geospatial_query discussion stack

Goal: build the MVP POC promised to Koonkie and run it on their test AOIs.
Decisions: docs/geospatial_query/DECISIONS.md

Email content stays out of this repo, journals and commits. Koonkie's AOI KML is data under no NDA and is DVC-tracked (aoi-handling). Source: the KML Koonkie sent on 2026-11-12.

## Current
mvp-build: plan at docs/geospatial_query/PLAN.md, awaiting approval

## Waiting on the user
- mvp-build: approve PLAN.md, dataset id, per-AOI files vs pooled only

## Preferences
- 2026-11-17: discuss before building; drafts go to the user before anything is sent

## Stack
- mvp-build: plan covers mvp-scope, aoi-size, query-time, output-shape and env
- probed-features: adapters for the 152 probed features
- query-time: build Query.time after the MVP
- postgis-loader: whether the tool ships a PostGIS loader
- packaging: standalone open-source CLI vs metasmith workflow
- deliverable: what goes back to Tomer after the run
- osm: get OpenStreetMap working (Tomer asked)
- country-coverage: parked unless Tomer raises it again
- claude-plan: follow up with Hallam (not build work)

## Workers
none

## Closed
- reply-tomer (2026-11-17)
- aoi-handling (2026-11-19)

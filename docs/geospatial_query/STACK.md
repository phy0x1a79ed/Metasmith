# geospatial_query discussion stack

Goal: build the MVP POC promised to Koonkie and run it on their test AOIs.
Decisions: docs/geospatial_query/DECISIONS.md

Confidentiality: email content and Koonkie's AOI file stay out of this repo, journals and commits. Source: the KML Koonkie sent on 2026-11-12.

## Current
aoi-handling

## Waiting on the user
- aoi-handling: where the AOI file and results live

## Preferences
- 2026-11-17: discuss before building; drafts go to the user before anything is sent

## Stack
- aoi-handling: keep Koonkie's AOIs and outputs out of git
- mvp-scope: which adapters the MVP runs (74 POC adapters vs the 152 probed features too)
- aoi-size: largest test AOIs are far bigger than the POC's 0.5-630 km2 range
- query-time: which moment a run asks each source for
- output-shape: long table in the Observation spec shape; file format; PostGIS loader or not
- env: one pinned environment that runs every adapter
- packaging: standalone open-source CLI vs metasmith workflow
- deliverable: what goes back to Tomer after the run
- osm: get OpenStreetMap working (Tomer asked)
- country-coverage: parked unless Tomer raises it again
- claude-plan: follow up with Hallam (not build work)

## Workers
none

## Closed
- reply-tomer (2026-11-17)

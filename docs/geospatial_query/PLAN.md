# MVP POC plan: AOIs in, feature dataset out

## Purpose & Contents

This file is the build plan for the geospatial query MVP promised to Koonkie. It holds the issues, goals, acceptance criteria and tasks of that build. Decisions from the discussion live in `DECISIONS.md`. Open topics live in `STACK.md`.

## Context

Koonkie accepted the plan: build an MVP POC, hand back a dataset for their AOIs, then turn it into an open-source tool they run on their own AOIs. Tomer sent a KML of known Canadian mining sites as the test set. The POC adapters already exist and pass on 15 test AOIs. This build turns them into one runnable pipeline and publishes the run on Koonkie's AOIs as a DVC-tracked dataset in the engcyc layout.

## What you said

> The objective is to build the MVP POC that the email mentions. And of course, to run it on his AOIs.

> it is data and im not under non disclosure. dvc track it?

> have a look at cyanoverse style and engcyc data project folder structures. I want the same layout for these AOIs

## Issues

- I1. No single environment runs every adapter. `geoquery` lacks pyarrow, `msm` lacks rasterio, and `pipeline.py` needs a local `projdata` folder.
- I2. The POC reads only GeoJSON with five fixed properties. Koonkie's AOIs arrive as KML.
- I3. The POC writes flat CSVs into its working folder, not a dataset tree with provenance and gaps.
- I4. The POC output does not use the approved Observation spec shape.
- I5. The largest Koonkie AOI is about 4,000 km², six times the largest AOI the POC was tested on.

## High-level goals

- G1. Have one pipeline that turns any list of AOIs into a feature dataset.
- G2. Hand Koonkie a dataset for their mining AOIs.
- G3. Lay that dataset out like the engcyc and Cyanoverse datasets, versioned with DVC.

## Acceptance criteria

- One command takes a KML or GeoJSON path and a dataset id, and writes the full dataset tree under `data/geospatial_query/<dataset>/`.
- The command runs from a clean shell in one pinned conda env with no manual PROJ setup.
- Each of the 11 Koonkie AOIs × each POC adapter resolves to `found`, `unavailable` or `not-attempted`. `_logs/gaps.tsv` lists every pair that is not `found`, with its reason.
- `integrated/observations_long.parquet` has one row per value with the spec columns: `aoi`, `source`, `observation_type`, `time`, `feature`, `family`, `value`, `SI_unit`.
- `_logs/ledger.tsv` has one row per published file with `bytes` and `sha256`.
- The dataset is DVC-tracked and pushed. Its `.dvc` file is committed on `geospatial_query/dev`.

## Tasks

- T1. Pin one conda env that runs every adapter (G1)
- T2. Import Koonkie's AOIs and DVC-track them (G2, G3)
- T3. Write the publisher that turns a run into the dataset tree (G1, G3)
- T4. Compact
- T5. Run the pipeline on Koonkie's AOIs and fix the failures that large AOIs cause (G2)
- T6. Publish, DVC-track and push the dataset (G2, G3)
- T7. Compact
- T8. Simplify
- T9. Draft the doc updates
- T10. Debrief

## Approach by task

### T1. Pin one conda env that runs every adapter

Add `envs/geoquery.yml` with rasterio, pyproj, pystac-client, shapely, requests, numpy, pandas, pyarrow and fiona for KML. Point PROJ at the env's own data and drop the `./projdata` override in `pipeline.py`. Rerun the 15 test AOIs as the baseline and compare against the October re-pull (719 adapter features ok).

Removes: the `./projdata` path logic in `pipeline.py` and the pyarrow workaround in `reports/recheck/adapters/go.sh`.

Gotchas: `mamba run` drops stdin, so call the env's python directly. Planetary Computer SAS tokens 429 under the 8-thread pool.

### T2. Import Koonkie's AOIs and DVC-track them

Convert the KML to `aois/aois.geojson` with the five properties the POC needs. Keep the original KML beside it. Write `aois.tsv` at the dataset root as the analogue of engcyc's `samples.tsv`: `aoi_id`, `source_name` (the KML name), `province`, `area_km2`, `bbox`. Stems follow the engcyc rule: letters, digits and `_` only, such as `aoi_01`.

Removes: none, new input path.

Gotchas: KML names carry en dashes and slashes. Two AOIs share a province. Pull the KML from the 2026-11-12 message in the Tomer thread.

### T3. Write the publisher that turns a run into the dataset tree

Map the POC records onto the engcyc grammar. The AOI is the stem, the feature family is the subject, and the adapter is the product.

- `<dataset>/README.md`, generated: sources, versions, run date, column notes.
- `<dataset>/aois.tsv` and `<dataset>/aois/`.
- `<dataset>/<family>/<adapter>/<aoi>.tsv`: one per-AOI product file, the values one adapter returned.
- `<dataset>/<family>/<family>_features.parquet`: the pooled table for that subject, at the subject root.
- `<dataset>/integrated/observations_long.parquet`, `features_wide.parquet` (AOI × feature) and `coverage.tsv` (AOI × adapter state).
- `<dataset>/_logs/ledger.tsv`, `gaps.tsv` and `runs/<run>.tar.gz` (the raw run log and records).

Map POC states to engcyc gap reasons: `unavailable` becomes `failed` with the verbatim reason, and `not-attempted` becomes `not_applicable`. Fold `build_outputs.py` into the publisher.

Removes: `build_outputs.py` and its four flat CSV deliverables.

Gotchas: never publish a zero-byte file. A failed adapter leaves no product file, only a gaps row. `observation_type` comes from the registry in `reports/source_registry.csv`, not from the adapters.

### T4. Compact

Handoff: the env file, the AOI import and the publisher are committed. The baseline run on the 15 test AOIs is in the run log. Continue with T5.

### T5. Run the pipeline on Koonkie's AOIs and fix the failures that large AOIs cause

Run all POC adapters over the 11 AOIs. Compare each adapter's failure rate against the 15-AOI baseline. Fix failures that come from AOI size: vector API page limits, request timeouts and raster windows. A failure the source causes stays a gap.

Removes: none expected.

Gotchas: the run takes about 3 minutes at 8 threads. Rerun only the failing adapters while fixing. Do not loosen the mid-Pacific control check to make a source pass.

### T6. Publish, DVC-track and push the dataset

Run the publisher into `data/geospatial_query/mmap_canada_mining/`. Track it with the `dvc` tool. Push it. Commit the `.dvc` file.

Removes: none.

Gotchas: `data/` is the shared data view of the metasmith project. Track only this dataset folder.

### T7. Compact

Handoff: dataset published and pushed. Continue with T8.

### T8. Simplify

Run the `simplify` skill over the pipeline entry, the publisher and the AOI import.

### T9. Draft the doc updates

Rewrite `poc/README.md` for the new command, env and output tree. Remove its stale `requirements.txt` instruction.

### T10. Debrief

Run the `debrief` skill in `metasmith/geospatial_query/dev`.

## Still unsure about

- The dataset id: `mmap_canada_mining`, after the KML name. Confirm or rename.
- Per-AOI product files: they follow the engcyc grammar but make about 800 small files. The other choice is pooled tables only.

## Callouts

- The MVP asks each source for its default moment, usually the latest data or a climatology. The `Query.time` field of the spec is not built.
- The 152 probed features without adapters and OpenStreetMap stay out of the MVP. Both remain on the stack.
- Packaging as an open-source tool for Koonkie comes after the MVP.

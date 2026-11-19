# MVP POC plan: AOIs in, one table per source out, planned by metasmith

## Context

Koonkie accepted the plan: build an MVP POC, hand back a dataset for their AOIs, then turn it into an open-source tool they run themselves. Tomer sent a KML of 11 known Canadian mining sites as the test set. The POC adapters exist and pass on 15 test AOIs, but they run from a flat Python script. The approved design page (panel 4) says the pipeline is a scatter-gather across sources that metasmith plans and compiles to Nextflow. This build makes that DAG real, runs it on Koonkie's AOIs and publishes the result as a DVC-tracked dataset in the engcyc layout. Discussion state is in `docs/geospatial_query/STACK.md` and `DECISIONS.md` on `geospatial_query/dev`. Approved 2026-11-19.

## What you said

> The objective is to build the MVP POC that the email mentions. And of course, to run it on his AOIs.

> it is data and im not under non disclosure. dvc track it?

> have a look at cyanoverse style and engcyc data project folder structures. I want the same layout for these AOIs

> the pipeline should ingest 1 table of AOIs and produce tables per source

> can I see the metasmith DAG as part of the plan? mock of transforms?

## Issues

- I1. No single environment or container runs every adapter. `geoquery` lacks pyarrow, `msm` lacks rasterio, and `pipeline.py` needs a local `projdata` folder.
- I2. The POC reads only GeoJSON with five fixed properties and a `tier` filter. Koonkie's AOIs arrive as KML.
- I3. No metasmith types or transforms exist for the geospatial pipeline. Panel 4 of the design page draws a DAG that nothing implements.
- I4. The POC writes flat CSVs into its working folder, not one table per source in a dataset tree with provenance and gaps.
- I5. The POC output lacks the approved spec's `SI_unit` and does not use its column names.
- I6. The largest Koonkie AOI is about 4,000 km², six times the largest AOI the POC was tested on.

## High-level goals

- G1. Have one pipeline that turns one table of AOIs into one table per source.
- G2. Have metasmith plan and run that pipeline, as the design page promised.
- G3. Hand Koonkie a dataset for their mining AOIs.
- G4. Lay that dataset out like the engcyc and Cyanoverse datasets, versioned with DVC.

## Acceptance criteria

- A planning-only driver prints and renders the DAG below: one `normalise_aois`, one `fetch_source` per source, one `aggregate`.
- One driver command takes one AOI table (KML or GeoJSON) and a dataset id. It plans, runs and publishes into `data/geospatial_query/mmap_canada_mining/`.
- The tree holds one table per source that found data, each covering every AOI it found.
- Each of the 11 AOIs × each source resolves to `found`, `unavailable` or `not-attempted`. `_logs/gaps.tsv` lists every pair that is not `found`, with its reason.
- `integrated/observations_long.parquet` has one row per value with `aoi`, `source`, `observation_type`, `time`, `feature`, `family`, `value`, `SI_unit`, plus `licence` and `native_res_m`. Every row has `observation_type`. A blank `SI_unit` occurs only for unitless or categorical features.
- `_logs/ledger.tsv` has one row per published file with `bytes` and `sha256`. No published file has zero bytes.
- The 15 test AOIs, run through the DAG, reach the October re-pull result: 719 adapter features ok.
- The dataset is DVC-tracked and pushed to chinook. Its `.dvc` file is committed on `geospatial_query/dev`.

## The metasmith DAG

The DAG is a scatter-gather across sources. It lives in a small metasmith library inside the scope at `research/geospatial_query/msm/`, with its own `data_types/geoquery.yml`, `transforms/geoquery/` and `resources/containers/geoquery.oci`. Keeping it in the scope keeps it ready to open-source as Koonkie's tool.

Given inputs:

- `geoquery::aoi_table`: the one AOI table, KML or GeoJSON.
- `geoquery::source`: one value per source, such as `{"adapter": "esa_worldcover"}`. The driver adds one for each of the 75 POC sources from `reports/source_registry.csv`.
- `containers::geoquery.oci`: one image built from `envs/geoquery.yml` with the POC adapter code inside.

### Planned DAG

Square brackets are given inputs, parentheses are transforms, and angle brackets are targets. `fetch_source` runs once per source. The diagram collapses the 75 runs by feature family, with the source count and examples on each line.

```
                      [aoi_table]  KML or GeoJSON, one row per AOI
                           |
                    (normalise_aois)          x1
                           |
                         aois  ------------------------------+
                           |                                 |
 [source] x75 ---> (fetch_source)  scatter, group_by=source  |
                           |                                 |
   infrastructure     17   epa_echo, overture_buildings, osm_overpass ...
   socio-economic     14   statcan_csd_2016, ghs_pop_r2023a, bc_tantalis_crown ...
   macrobiology       10   esa_worldcover, nrcan_landcover, hansen_gfc_v1_13 ...
   public health       8   phac_wastewater, mgnify, statcan_odhf ...
   geology             8   mrdem_30, gsc_surficial_1880a, macrostrat ...
   hazards             8   eccc_npri, usgs_fdsn, eccc_naps ...
   spectral            5   sentinel2_l2a, landsat_c2l2_st, sentinel1_rtc ...
   climate             2   era5_open_meteo, noaa_nsidc_sic_cdr
   latent              2   alphaearth_v1_annual, clay_v0_embeddings
   water bodies        1   jrc_gsw
                           |
                    <source_table> x75   one table per source, rows = AOI x feature
                           |
                      (aggregate)             x1, gathers all 75
                           |
     +---------------+-----+---------+-----------+
     |               |               |           |
<observations_long> <features_wide> <coverage>  <gaps>
```

Every transform also requires `[containers::geoquery.oci]`. The diagram leaves that edge out.

### Mock transforms

Each transform is one file under `msm/transforms/geoquery/`, in the shape of `metasmith-libraries/transforms/amplicon/blast_map_asvs.py`. Each protocol calls one entry point of the POC package inside the container.

```python
# normalise_aois.py — one AOI table in, normalised AOIs out
from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("containers::geoquery.oci"))
table = model.AddRequirement(lib.GetType("geoquery::aoi_table"))
aois  = model.AddProduct(lib.GetType("geoquery::aois"))

def protocol(context: ExecutionContext):
    i, o = context.Input(table), context.Output(aois)
    context.ExecWithContainer(image=image,
        cmd=f"python -m geoquery.normalise --in {i.container} --out {o.container}")
    return ExecutionResult(manifest=[{aois: o.local}], success=o.local.exists())

TransformInstance(protocol=protocol, model=model, group_by=table,
                  resources=Resources(cpus=1, memory=Size.GB(1), duration=Duration(minutes=5)))
```

```python
# fetch_source.py — one source over every AOI, one table out (the scatter)
from metasmith.python_api import *

lib    = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model  = Transform()
image  = model.AddRequirement(lib.GetType("containers::geoquery.oci"))
aois   = model.AddRequirement(lib.GetType("geoquery::aois"))
source = model.AddRequirement(lib.GetType("geoquery::source"))      # value: {"adapter": "esa_worldcover"}
table  = model.AddProduct(lib.GetType("geoquery::source_table"))

def protocol(context: ExecutionContext):
    a, s, o = context.Input(aois), context.Input(source), context.Output(table)
    context.ExecWithContainer(image=image,
        cmd=f"python -m geoquery.fetch --aois {a.container} --source {s.container} --out {o.container}")
    # a table of gap rows is still a success: absence is declared, never silent
    return ExecutionResult(manifest=[{table: o.local}], success=o.local.exists())

TransformInstance(protocol=protocol, model=model, group_by=source,
                  resources=Resources(cpus=1, memory=Size.GB(2), duration=Duration(minutes=20)))
```

```python
# aggregate.py — every source table in, integrated tables out (the gather)
from metasmith.python_api import *

lib      = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model    = Transform()
image    = model.AddRequirement(lib.GetType("containers::geoquery.oci"))
aois     = model.AddRequirement(lib.GetType("geoquery::aois"))
tables   = model.AddRequirement(lib.GetType("geoquery::source_table"))   # all 75, grouped under aois
long_    = model.AddProduct(lib.GetType("geoquery::observations_long"))
wide     = model.AddProduct(lib.GetType("geoquery::features_wide"))
coverage = model.AddProduct(lib.GetType("geoquery::coverage"))
gaps     = model.AddProduct(lib.GetType("geoquery::gaps"))

def protocol(context: ExecutionContext):
    ins  = " ".join(str(t.container) for t in context.InputGroup(tables))
    outs = {p: context.Output(p) for p in (long_, wide, coverage, gaps)}
    context.ExecWithContainer(image=image,
        cmd=f"python -m geoquery.aggregate --tables {ins} --out-dir {outs[long_].container.parent}")
    return ExecutionResult(manifest=[{p: o.local for p, o in outs.items()}],
                           success=all(o.local.exists() for o in outs.values()))

TransformInstance(protocol=protocol, model=model, group_by=aois,
                  resources=Resources(cpus=2, memory=Size.GB(4), duration=Duration(minutes=15)))
```

`context.InputGroup` stands for whatever call the metasmith API uses to hand a transform every instance of a grouped input. T3 confirms the real call against the binner aggregator in the metagenomics library.

### Types

`msm/data_types/geoquery.yml` declares `aoi_table` (KML or GeoJSON), `aois` (normalised GeoJSON), `source` (JSON value), `source_table` (TSV), `observations_long` and `features_wide` (parquet), `coverage` and `gaps` (TSV). `msm/data_types/containers.yml` declares `geoquery.oci`.

### Source table columns

One row per AOI × feature found, plus one status row per AOI with no feature: `aoi`, `source`, `observation_type`, `time`, `feature`, `family`, `value`, `value_num`, `SI_unit`, `licence`, `native_res_m`, `status`, `reason`.

Publishing stays outside the DAG. The driver copies the targets into the engcyc layout:

- `<dataset>/README.md`, generated: sources, run date, image, column notes, table list from the tree.
- `<dataset>/aois.tsv` and `<dataset>/aois/`: the AOI table as ingested and as normalised.
- `<dataset>/<family>/<source>.tsv`: each `source_table`, at the root of its feature family.
- `<dataset>/integrated/observations_long.parquet`, `features_wide.parquet` and `coverage.tsv`.
- `<dataset>/_logs/ledger.tsv`, `gaps.tsv` and `runs/<run>.tar.gz` (the metasmith run logs).

## Tasks

- T1. Pin one conda env and build one container image that runs every adapter (G1, G2)
- T2. Turn the POC into a package with fetch, normalise and aggregate entry points (G1)
- T3. Write the metasmith types and transforms, and render the DAG from a planning-only driver (G2)
- T4. Commit a checkpoint
- T5. Compact
- T6. Run the DAG on the 15 test AOIs, then on Koonkie's AOIs, and fix the failures that large AOIs cause (G2, G3)
- T7. Publish, DVC-track and push the dataset (G3, G4)
- T8. Compact
- T9. Simplify
- T10. Draft the doc updates
- T11. Debrief

## Approach by task

### T1. Pin one conda env and build one container image that runs every adapter

Add `envs/geoquery.yml` with rasterio, pyproj, pystac-client, shapely, requests, numpy, pandas, pyarrow and fiona (for KML). Point PROJ at the env's own data. Build `geoquery` as a Docker image from the env and the POC package. Write its URI to `msm/resources/containers/geoquery.oci` and its type to `msm/data_types/containers.yml`.

Removes: the `./projdata` path logic at the top of `poc/pipeline.py`, and the gitignored-pyarrow workaround in `reports/recheck/adapters/go.sh`.

Gotchas: try a local image tag first. Pushing to quay failed for Cyanoverse on missing auth, so fall back to ghcr if the runtime needs a registry. `mamba run` drops stdin, so call the env's python by path. The container needs outbound HTTPS to every source host.

### T2. Turn the POC into a package with fetch, normalise and aggregate entry points

Move the adapter modules under `poc/geoquery/` as one package. Add three entry points that the transforms call: `normalise` (KML or GeoJSON in, normalised GeoJSON out), `fetch` (one adapter over every AOI, one table out) and `aggregate` (every source table in, integrated tables out). `fetch` reuses `run_one` and the `ADAPTERS` registry from `pipeline.py` and the lane modules. Add `reports/feature_units.csv`, seeded by rules on feature-name suffixes and filled by hand for the rest.

Removes: `poc/run_all.py` and `poc/build_outputs.py`. Their roles move to the DAG and the driver.

Gotchas: KML names carry en dashes and slashes. Drop the `tier` filter in `load_aois` for files that carry no tier. Mixed-type `value` breaks a parquet column, so store `value` as a string with a numeric `value_num` beside it. Dedup on (slot, source) as `run_all.py` does today. Pull the KML with `productivity download_attachments` from the 2026-11-12 message in the Tomer thread.

### T3. Write the metasmith types and transforms, and render the DAG from a planning-only driver

Write `msm/data_types/geoquery.yml` with the types named in *The metasmith DAG*. Write the three transforms under `msm/transforms/geoquery/` in the shape of `blast_map_asvs.py`. Build the library metadata with `msm build`. Write `msm/main/plan.py` in the shape of `metasmith-libraries/main/diamond_uniref50_from_assembly.py`: it adds the AOI table and the 75 source values, generates the workflow and stops. Render the DAG to SVG with `metasmith.models.dag_draw`, as `figures/design/build.py` does for panel 4.

Removes: none. The hand-drawn panel 4 DAG in `build.py` can later read this one instead.

Gotchas: confirm early that the planner fans `fetch_source` out over 75 `source` values and gathers all 75 tables into one `aggregate`. The binner aggregator in the metagenomics workflow is the precedent. Every type a transform names must exist in `geoquery.yml` or the build fails.

### T4. Commit a checkpoint

Commit the env, image files, package, `msm/` library, unit table and the rendered DAG on `geospatial_query/dev`. Push to capella.

### T5. Compact

Handoff: T1–T4 committed. The rendered DAG is in `msm/`. The KML sits in a temp dir from `download_attachments`. Continue with T6.

### T6. Run the DAG on the 15 test AOIs, then on Koonkie's AOIs, and fix the failures that large AOIs cause

Extend the driver to stage and run the workflow. Run it on `examples/test_aois.geojson` and compare against the October re-pull in `reports/recheck/`. Then run it on the 11 Koonkie AOIs. Compare each source's failure rate against the 15-AOI baseline. Fix failures that come from AOI size: vector API page limits, request timeouts and raster windows. A failure the source causes stays a gap.

Removes: none expected.

Gotchas: the flat POC took about 3 minutes for 15 AOIs at 8 threads. 75 container runs add start-up time, so expect 10–20 minutes. Rerun only the failing sources while fixing. Do not loosen the mid-Pacific control check to make a source pass. Raster reads cap at `MAXPIX` = 320 px a side, so a 100 km AOI reads at about 300 m per pixel. Record that in the README rather than raise the cap. Planetary Computer SAS tokens 429 under concurrent runs.

### T7. Publish, DVC-track and push the dataset

Run the driver's publish step into `data/geospatial_query/mmap_canada_mining/`. Track the dataset folder with `dvc add`. Push it with the `dvc` tool. Commit the `.dvc` file on `geospatial_query/dev`.

Removes: none.

Gotchas: `data/` is the shared data view of the metasmith project. Track only this dataset folder. Check `dvc scope_status` before and after. A source with no found AOI gets no table, only gaps rows.

### T8. Compact

Handoff: dataset published, pushed and committed. Record the found and gap counts. Continue with T9.

### T9. Simplify

Run the `simplify` skill over the package entry points, the `msm/` transforms and the driver.

### T10. Draft the doc updates

Rewrite `poc/README.md` for the driver command, the image and the output tree. Remove its stale `requirements.txt` instruction and its flat-CSV output table. Point at the engcyc `LAYOUT.md` for the grammar rather than restate it.

### T11. Debrief

Run the `debrief` skill in `metasmith/geospatial_query/dev`. Close the `mvp-build` topic in `DECISIONS.md` and `STACK.md`.

## Callouts

- The MVP asks each source for its default moment, usually the latest data or a climatology. The spec's `Query.time` is not built. It stays on the stack.
- The 152 probed features without adapters and OpenStreetMap stay out of the MVP and on the stack.
- Packaging as an open-source tool for Koonkie, and what goes back to Tomer, come after the MVP. The `msm/` library and the image are the start of that tool.

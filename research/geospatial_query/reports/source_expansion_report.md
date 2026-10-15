# Source expansion brief

## Purpose & Contents

This brief is the starting point for the sessions that expand the geospatial query's sources. Read it before you add a source, change the spec or re-probe a candidate. It holds:

- links to every input: the design artifact, the POC, the probe tables, the science project
- what an observation is, its observation type, and where its quality metadata comes from
- which probed features returned a real value at the test AOIs
- the off-nadir field of every imagery source probed
- the named gaps, each with its probe outcome and its best candidate
- how well a picture can be placed from its pixels alone
- the open decisions and the traps that cost time before

It does not repeat the probe rows, the catalogue or the POC code. Follow the links for those.

## Links

| What | Where |
|---|---|
| Design artifact (spec, features, DAG) | https://claude.ai/artifact/Nj52Qha3utLQH7RVkssZJb (private) |
| Artifact source | [`figures/design/build.py`](../figures/design/build.py) builds `index.html` from [`template.html`](../figures/design/template.html) and the tables below |
| POC adapters (Python, one function per source) | [`poc/`](../poc/), entry point [`poc/run_all.py`](../poc/run_all.py), shared code [`poc/pipeline.py`](../poc/pipeline.py) |
| POC write-up | [`poc_report.md`](poc_report.md) |
| Design decisions from the science project | [`session-debrief.md`](session-debrief.md), [`metasmith_core_set.md`](metasmith_core_set.md) |
| Family definitions and rules | [`layer_families.md`](layer_families.md) |
| Original catalogue, 316 modules | [`geolocatable_data_registry.md`](geolocatable_data_registry.md), as a table in [`layer_inventory.csv`](layer_inventory.csv) |
| Outcome per catalogue module | [`catalogue_reconciliation.csv`](catalogue_reconciliation.csv), totals in [`funnel_counts.json`](funnel_counts.json) |
| Per-adapter status and observation type | [`source_registry.csv`](source_registry.csv) |
| Every POC feature value (15 AOIs) | [`feature_values_long.csv`](feature_values_long.csv) |
| Triage probes | [`triage_results_merged.csv`](triage_results_merged.csv), [`layer_slots_triaged.csv`](layer_slots_triaged.csv) |
| Gap probes, one row per candidate | [`gap_source_probes.csv`](gap_source_probes.csv), built by [`merge_probes.py`](merge_probes.py) from the lane tables |
| Off-nadir field per imagery source | [`off_nadir_fields.csv`](off_nadir_fields.csv), built by the same script |
| Probe lanes: script, table, findings | [`probes/<lane>/`](probes/). A: satellite QC and tasked imagery. B: airborne, drone, hyperspectral. C: zoning, water, climate. D: ground-level cameras. E: picture to location. F: query ideas |
| Validated probe features, one row per feature with a value | [`probed_features.csv`](probed_features.csv), built by [`probed_features.py`](probed_features.py) from `probes/<lane>/poc/`. Lanes SAT, AIR, HYP, REC, CAM each hold `poc.py`, `poc_values.csv` and `poc_status.csv` |
| Fresh re-pull of every listed feature | [`recheck/adapters/`](recheck/) re-runs the POC adapters through `go.sh`. [`recheck/lanes/`](recheck/) re-runs the five probe lanes. Each `recheck_status.csv` holds one row per feature |
| Angles for the 45 POC scene records | [`probes/A/scene_qc_backfill.csv`](probes/A/scene_qc_backfill.csv) |
| Test AOIs | [`../examples/test_aois.geojson`](../examples/test_aois.geojson) |
| Fixes after a fresh copy from the science project | [`apply_family_fixes.py`](apply_family_fixes.py) moves three family assignments. [`apply_observation_type.py`](apply_observation_type.py) adds the `observation_type` column. Re-run both |
| Science project | Claude Science `proj_8be587fb267f`, conversation `ea94976a-52cc-40e1-9649-39706ecd4d0e`. Files live under `~/.claude-science/orgs/0e7f7957-d72e-4f89-b89e-32275f97b806/artifacts/proj_8be587fb267f/<uuid>/v<hash>_<name>`. Take the newest by mtime |

**CAUTION** Lane A's `cache/` (263 MB) and lane E's `models/` (43 GB), `images/` and `orig/` are gitignored. Run lane A's `crawl_*.py` before its `probe.py` on a fresh checkout. Lane E's `probe.py` rebuilds its table from the committed predictions. `probe.py --rerun` needs the models.

## Where the sources stand

The catalogue held 317 modules in scope. 11 national modules were added, which gives 328. 70 were probed, 57 got an adapter and 53 return data. 4 adapters fail (mapillary, kartaview, osm_overpass, aafc_aci). 4 modules were dropped. 252 were never probed. 97 triage candidates match no catalogue module.

The user considers the catalogue already worked through. Do not treat its leftovers as the expansion plan. The gaps below are the plan.

`source_registry.csv` carries an `observation_type` per adapter. The registry holds 9 `overture_*` adapters. Water (6 features) and climate (12 features) were the thinnest families before this round of probes.

## What an observation is

An observation is a group of features produced together. This matches OGC/ISO 19156 Observations & Measurements ([OGC](https://www.ogc.org/standard/om/)) and SOSA/SSN ([W3C](https://www.w3.org/TR/vocab-ssn/)): one act of sensing, by one procedure, of one place, at one time, with a result quality.

An observation only groups features. It carries its source, its observation type and its time. Everything else is a feature.

The observation type says how the data was collected: satellite, aerial (aircraft and drone), surface vehicle, fixed sensor (station, gauge or camera), crowdsourced, field sample, survey or blended. A modelled or derived product takes the type of its inputs. A land cover map is satellite and Daymet is fixed sensor. A product built from inputs of several types is blended: CHIRPS, TerraClimate, ERA5. A physical sample measured in a lab, such as water quality or wastewater, is field sample. A record determined administratively or drawn by professional cartographers, such as zoning or a geologic map, is survey.

A time is a moment plus an accuracy, read as plus or minus. A scene is its acquisition time, accurate to seconds. A composite is its midpoint, with half its span as the accuracy: July 2023 is 16 July plus or minus 15.5 days. A query time uses the same shape as a search window.

Quality metrics are features in the family of the data they qualify. Scene angles and cloud cover go to spectral. Lidar quality level goes to geology. Station distance goes to climate or water bodies. A zoning snapshot date goes to socio-economic. A camera's heading goes to the family of its photos. A query filters them like any other feature. Only their reading differs. Which quality features an observation carries depends on how it was made:

| Made by | Examples | Quality features |
|---|---|---|
| one acquisition | one scene, granule, point cloud, photo | off-nadir or incidence, sun angles, cloud cover (tile and AOI), camera heading and pitch |
| a composite | modis_13q1 (16-day), s2_signature_v1, esa_worldcover, era5, Daymet | scene or reading count, clear-pixel share, distance to the station |
| a compiled record snapshot | overture_*, eccc_npri, zoning, statcan_* | snapshot date, join level (point, block, county, province), record count |

The spec panel in the design artifact is the source of truth for the fields. About 70 POC features (`*_n_px`, `*_src_km`, `*_year`, `s2sig_n_scenes`, `ovt_control_*` and others) are quality features under the same rule.

The POC keeps one record per AOI × adapter, with no angles. Only 45 records carry a real STAC scene id (15 AOIs × Sentinel-2, Landsat, Sentinel-1). `scene_qc_backfill.csv` holds their angles, sun position and AOI cloud.

## Off-nadir

Off-nadir varies little for Sentinel-2 and Landsat. It becomes a useful filter for tasked imagery (S4), hyperspectral (S3) and airborne surveys (S1). The table lists the imagery sources that expose a view angle. `off_nadir_fields.csv` has the full fields and notes.

| Source | Gap | Angle | Field | Where it lives | Sample |
|---|---|---|---|---|---|
| Sentinel-2 L2A | Q1 | view zenith | mean of 13 `ZENITH_ANGLE` in `Mean_Viewing_Incidence_Angle_List` | `granule-metadata` asset (MTD_TL.xml) | 2.8–10.3° over 15 scenes |
| Sentinel-2 L1C (Earth Search) | S5 | view zenith | same, in `metadata.xml` | `granule_metadata` asset | 4.5° |
| Landsat C2 L2 and L1 | Q1, S5 | off-nadir | `view:off_nadir` | item property | 0 on every scene |
| Sentinel-1 RTC | Q1 | incidence | `geolocationGrid/incidenceAngle` | GRD sidecar `annotation/iw-vv.xml`. The RTC item has none | 33.3–44.3° |
| HLS L30, S30 | Q1 | view zenith | `VZA` band. Scene mean `MEAN_VIEW_ZENITH_ANGLE` | per-pixel asset. The mean is in the CMR record | 1.9° pixel, 3.17° mean |
| ICEYE | S4 | off-nadir, incidence | `view:off_nadir`, `view:incidence_angle` | item property | 20.7°, 22.7° |
| Capella | S4 | incidence, look | `view:incidence_angle`, `capella:look_angle` (off-nadir equivalent) | item property | 36.8°, 33.5° |
| Umbra | S4 | incidence | `view:incidence_angle` | item property | 27.7° |
| Satellogic EarthView | S4 | off-nadir | `view:off_nadir` | item property in `{item}_metadata.json` | 18.8° |
| Maxar Open Data | S4 | off-nadir | `view:off_nadir` | item property | 41.2° |
| SkyFi | S4 | off-nadir | `offNadirAngle`. Filter `maxOffNadirAngle` | archive search response (needs an account) | schema only |
| Planet Tanager | S3 | off-nadir | `view:off_nadir` | item property | 0.2–30.5° over 153 scenes |
| EnMAP | S3 | off-nadir | `enmap:acrossOffNadirAngle`, `enmap:alongOffNadirAngle` | item property | signed degrees |
| DESIS | S3 | incidence | `desis:sceneIncidenceAngle` | item property | |
| 3DEP lidar COPC | S1 | scan angle | `ScanAngleRank` | per-point dimension. The derived rasters have none | |
| UAVSAR | S1 | incidence | `.inc` raster | per-pixel file beside each scene (Earthdata login) | |

None: NAIP, HRDEM, NAPL, WESM, NOAA Digital Coast, OpenTopography, OpenAerialMap, EMIT, PACE, NICFI, Planet Open Canada. GeoNadir carries the drone gimbal pitch in each image's EXIF, through `/api/metadata/`.

The ground-level counterpart of off-nadir is camera pitch and heading. Panoramax carries `pers:pitch` and `view:azimuth`. Wikimedia, DriveBC and PhenoCam carry a heading only. Panoramax pitch is 0 on every Toronto core item and non-zero (−16 to +13°) on 202 of 999 items in the Toronto stress extent. It filters some surveys only.

## Validated probe features

A probed feature enters the artifact only when a POC read a real value at one or more of the 15 test AOIs. Five sonnet lanes ran the POCs on 2026-10-14. A fresh re-run the same day read all of them again, and all 719 adapter features too. 152 features from 43 sources pass. 34 features fail:

- **Pixels behind a login:** EMIT and PACE (Earthdata), EnMAP and DESIS (DLR SSO), Landsat L1 (EROS), AVIRIS-NG (Earthdata). Their scene QC features pass.
- **No reader in the env:** Sentinel-2 L1C (JPEG2000), Tanager reflectance (HDF5), 3DEP scan angle (LAZ).
- **No test AOI in coverage:** Maxar Open Data, NEON AOP, UAVSAR, Geograph, BC ALR, EU Urban Atlas, Vancouver and Calgary zoning. Each answers its positive control.
- **Null at every AOI:** DESIS geometric accuracy (-1 sentinel), Zoning Atlas minimum lot size.

**CAUTION** Some values are not physical units. Umbra and ICEYE backscatter are amplitude DN, Satellogic reflectance is TOA DN, and GeoNadir colour is a dataset-wide mean. Each row's description says so.

## Gaps against the original brief

The user's original brief asked for: an AOI as a lat/lon box plus periodic time plus spectral band, cloud cover, off-nadir angle, multispectral and hyperspectral, satellite vs plane vs lidar vs drone, paid brokers (SkyFi) and government agencies (NASA), correction steps (orthorectified, atmospheric), and knowledge representation for GIS and land-use records.

Each gap name says what is missing. A source gap (S) lacks data. A query gap (Q) lacks a field in the query or the result. R1 goes the other way: from a picture to a place. Hits count the 15 AOIs in `test_aois.geojson`, each against a control outside coverage. Every candidate was probed live on 2026-10-13 and 2026-10-14.

| Id | Gap | Old id | Outcome | Best candidate |
|---|---|---|---|---|
| Q1 | No QC metrics per observation (off-nadir, sun angle, AOI cloud) | G1 | closed for the 45 scene records | Planetary Computer item plus sidecar XML (see Off-nadir) |
| Q2 | Query cannot pick bands or indices | G2 | works, 15/15 | `eo:bands` common name plus `spyndex` |
| Q3 | Query cannot ask for periodic time | G3 | works, 15/15 | one range search, binned client-side |
| Q4 | Query cannot filter on QC | G4 | works, 15/15 | CQL2-JSON on Planetary Computer, AOI cloud after the read |
| Q5 | Result holds no pointer to the data itself | G9 | works, 15/15 | unsigned href, signed at read time |
| S1 | No airborne lidar or aerial imagery | G5 | sources found, US and Canada | 3DEP COPC with WESM quality level (US), HRDEM (Canada) |
| S2 | No drone imagery | G5 | thin, 1/15 | OpenAerialMap through the HOT STAC |
| S3 | No hyperspectral imagery | G6 | sources found | EnMAP 15/15, EMIT 11/15 |
| S4 | No high-resolution tasked imagery (open commercial and brokers) | G7 | open samples only, brokers need an account | ICEYE, Umbra, Capella, Satellogic |
| S5 | No uncorrected (L1) imagery | G8 | closed, 15/15 | Earth Search Sentinel-2 L1C, LandsatLook C2 L1 |
| S6 | No zoning or land-use records | G10 | partial, 2/15 at best | National Zoning Atlas (US, terms), city open data (Canada) |
| S7 | Too few water features | new | closed | ECCC hydrometric 13/15, HydroRIVERS 13/15 |
| S8 | Too few climate features | new | closed, 15/15 | GHCN-Daily, Daymet, TerraClimate, CHIRPS v3 |
| S9 | No ground-level camera imagery: vehicle-mounted, fixed or geotagged photos | new | geotagged photos everywhere, street-level thin | iNaturalist 15/15, GBIF 14/15, Wikimedia 7/15, Panoramax 3/15 |
| R1 | Nothing places a picture that has no coordinates | new | coarse only, no street-level fix | EXIF, then StreetCLIP plus PLONK, then VPR |

### Q1. No QC metrics per observation

- **Outcome:** all 45 POC scene records resolve. Each has its off-nadir or incidence, processing level, and (for optical) sun position, tile cloud and AOI cloud.
- **AOI cloud:** derive it from `SCL` (Sentinel-2) or `qa_pixel` (Landsat). It often disagrees with tile cloud. Landsat at Bingham reads 0.48 % on the scene and 31 % over the AOI. A Sentinel-2 scene at farm_sk_quarter reads 8.99 % on the tile and 64.7 % over the AOI.
- **Next:** refactor the POC adapters to return these as spectral QC features.

### Q2. Query cannot pick bands or indices

- **Outcome:** one spec (bands red, nir, swir16; indices NDVI, NDWI, NBR) resolves on Sentinel-2 and Landsat, on Planetary Computer and Earth Search. NDVI at farm_sk_quarter in July 2023: 0.5458 on both S2 catalogues, 0.5419 on Landsat.
- **Spec:** none. Bands and indices apply only to imagery. An imagery adapter names each band or index as a feature.
- **CAUTION** Landsat names NIR `nir08`. Fall back to wavelength (760–900 nm). `rededge` is ambiguous on Sentinel-2 (B05, B06, B07, B8A).

### Q3. Query cannot ask for periodic time

- **Outcome:** one range search binned client-side picks the same best-cloud item as a per-period fan-out in 24/24 months. Planetary Computer needs 15 requests over 15 AOIs, against 360 for a monthly fan-out.
- **Spec:** `time` is a list of moments, each with an accuracy. Expand a periodic request into one moment per period before the query. "Every July" is 16 July plus or minus 15.5 days, once per year.

### Q4. Query cannot filter on QC

- **Outcome:** filters change counts as expected on Planetary Computer. Sentinel-2 2023 at farm_sk_quarter: 129 items, 36 under 10 % cloud.
- **Spec:** a filter on a QC feature, such as `off_nadir_deg <= 15`. Send a filter the catalogue knows to the server. Apply the rest, AOI cloud among them, after the read.
- **CAUTION** the sun property differs per catalogue: `s2:mean_solar_zenith` on Planetary Computer, `view:sun_elevation` on Earth Search. Keep a property map per collection.

### Q5. Result holds no pointer to the data itself

- **Outcome:** a range GET returns 206 on Planetary Computer for S2 and Landsat at 15/15 AOIs. Earth Search Landsat assets are requester-pays `s3://`.
- **Spec:** none. Most sources have no file to point at. An imagery adapter that needs one stores the unsigned href. The SAS token lasts about 44 min.

### S1, S2. No airborne lidar, aerial or drone imagery

- **US lidar:** Planetary Computer `3dep-lidar-copc`, 3/15, angle per point. USGS WESM (layer 8 of `index.nationalmap.gov` `3DEPElevationIndex`) gives the quality level per work unit and hits 4/15. NAIP hits 4/15.
- **Canada lidar:** HRDEM has valid 1 m pixels at 8/15. It is absent at both prairie farms.
- **Elsewhere:** OpenTopography needs `include_federated=true` and is the only catalogue that hits Montreal. NOAA Digital Coast hits 2/15 lidar, 4/15 imagery. NEON AOP and UAVSAR hit 0/15.
- **Drone:** OpenAerialMap through `api.imagery.hotosm.org/stac`, filtered on `oam:platform_type=uav`, hits only the Toronto stress AOI (2 scenes, about 3 cm). GeoNadir answers without auth but is undocumented. EarthExplorer UAS needs a USGS account. DroneDB has no search API.

### S3. No hyperspectral imagery

- **Outcome:** EnMAP L2A on the DLR STAC hits 15/15 with off-nadir in the item. EMIT hits 11/15 through CMR. Tanager hits 3/15, DESIS 2/15, AVIRIS-NG 2/15, NEON 0/15. PACE OCI is global ocean colour.
- **Walls:** EnMAP and DESIS assets need DLR SSO. EMIT downloads need Earthdata. PRISMA is portal only.

### S4. No high-resolution tasked imagery

- **Open commercial:** ICEYE 3/15, Umbra 2/15, Capella 2/15, Satellogic 1/15 (Bingham, July–December 2022 only), Maxar 0/15. All carry an angle in the item. NICFI is tropics only. Planet Open Canada hits 1/15 (Fort McKay) with no angle.
- **Brokers:** SkyFi, UP42 and Sentinel Hub return 401 on search and quote. SkyFi's OpenAPI spec shows a quote returns `offNadirAngle`, `cloudCoveragePercent`, `captureTimestamp` and `priceForOneSquareKm`.
- **Decision needed:** add a commercial licence tier, and decide whether quote-only adapters are in scope.

### S5. No uncorrected (L1) imagery

- **Outcome:** Earth Search `sentinel-2-l1c` and LandsatLook `landsat-c2l1` each hit 15/15. Planetary Computer has no L1C. LandsatLook pixels redirect to the EROS login.

### S6. No zoning or land-use records

- **US:** the National Zoning Atlas hits 2/15 (Detroit, Bingham) with district code, housing treatment, parking, height cap and minimum lot. **CAUTION** its terms bar download without written permission. PAD-US hits 1/15 and is protected land, not zoning. Regrid is paid.
- **Canada:** Toronto open data hits 2/15. Vancouver and Calgary work but sit outside the test AOIs. BC ALR polygons touch the bounding box of 3 AOIs and intersect none. Each city needs its own adapter.
- **EU:** Urban Atlas works on a Paris control and covers no test AOI.

### S7. Too few water features

- **Outcome:** ECCC hydrometric (`api.weather.gc.ca`) 13/15 within 25 km. HydroRIVERS 13/15, one schema for both countries, a 66 MB download. USGS Water Data 5/15. NHDPlus HR 8/15. NHN 9/15 or more.

### S8. Too few climate features

- **Outcome:** GHCN-Daily, Daymet, TerraClimate and CHIRPS v3.0 each hit 15/15. CHIRPS v3.0 covers 60S–60N. v2.0 covers 50S–50N and misses 5 AOIs. ECCC daily climate hits 13/15.

### S9. No ground-level camera imagery

- **Vehicle-mounted:** Panoramax hits 3/15 (Toronto core, Toronto stress, Montreal), needs no key and has the best per-image QC: `view:azimuth`, `pers:pitch`, `quality:horizontal_accuracy`. Mapillary fails because the POC adapter sends no `access_token` (error 190). A free token fixes it. KartaView returns `"Restricted access!"` inside HTTP 200. Bee Maps and Street View need a key.
- **Fixed cameras:** DriveBC has 2 cameras in the BC AOIs. PhenoCam has a site within 30 km of 4/15. Both carry a cardinal heading. Windy, 511 Ontario and 511 Alberta need a key. AMOS is gone.
- **Geotagged photos:** iNaturalist 15/15, GBIF 14/15, Wikimedia Commons 7/15 within 1 km. Flickr needs a key. Geograph is UK only.
- **Datasets:** OSV-5M (5.1M Mapillary images, CC-BY-SA-4.0) downloads without login. BDD100K, nuScenes and YFCC100M need a form or are unreachable.

## Picture to location (R1)

Lane E scored open tools on 50 CC-licensed photos with known coordinates and stripped EXIF: 30 near the AOIs, 20 worldwide. [`probes/E/findings.md`](probes/E/findings.md) has every model, the caveats on the test set and the services that refused.

| Tool | Median error | Within 25 km | Right country |
|---|---|---|---|
| StreetCLIP over a flat 7402-city list | 803 km | 24 % | 68 % |
| Plurality vote of 6 models | 712 km | 16 % | 60 % |
| PLONK_OSV_5M | 878 km | 0 % | 48 % |
| G3 alignment checkpoint | 1108 km | 12 % | 50 % |
| GeoCLIP | 1250 km | 8 % | 48 % |
| OSV-5M baseline | 2808 km | 6 % | 28 % |

- StreetCLIP's label list holds the AOI cities, so its 25 km score is optimistic.
- PLONK sample density is the best confidence signal (AUROC 0.86 for error under 200 km). OSV-5M and PLONK still return a point for a blank image.
- Visual place recognition (DINOv2 retrieval, then LightGlue) against Panoramax found a reference within 1 km for 6/7 photos when handed the area. Only 1/7 passed geometric verification. From a model's guess, 0 verified.
- PIGEON withholds its weights. GeoSpy and Picarta need an account.

The pipeline to build:

1. Read EXIF GPS and accept it. 24 of 50 originals carry it.
2. Otherwise run StreetCLIP over a regional city list, plus PLONK_YFCC and PLONK_OSV_5M. Report a place and a radius from the PLONK density, not a point.
3. Where street-level references exist near the guess, run retrieval then LightGlue. Accept at 40 or more inliers.

## Traps

- MGnify returns HTTP 200 for an unknown query parameter and serves the unfiltered catalogue. Test every filter against a control: a differential count, not a 200.
- **CAUTION** Earth Search ignores CQL2-JSON filters and returns HTTP 200 with the unfiltered count. Use its `query` extension.
- Earth Search Sentinel-2 declares a reflectance offset of -0.1 that it already applied (`earthsearch:boa_offset_applied=true`). Planetary Computer S2 declares none. Apply 1e-4 and -0.1 when `s2:processing_baseline` ≥ 04.00.
- Planetary Computer returns reprocessed duplicates: 199 items, 142 distinct datetimes at one AOI. Dedupe before binning.
- `eo:cloud_cover` is per tile. Use it only as a prefilter.
- Planetary Computer blob reads need a SAS token. Unsigned reads return HTTP 409 and look like an absent layer.
- The open SAR STAC roots are incomplete. Umbra links only 2024–2025 (list the bucket: 7,561 items). ICEYE links 589 of 663. Capella has 9,999 per-product items.
- Planetary Computer 3DEP dates are year-granular: 2018-01-01 for a survey flown in April 2017.
- A bbox STAC search overstates HRDEM coverage (11/15 against 8/15 valid). Read the COG.
- TerraClimate's THREDDS subset returns packed integers. Apply scale 0.1. The ocean control returns the fill value with HTTP 200.
- ECCC climate station `LATITUDE` and `LONGITUDE` are integers × 1e7. Use the geometry.
- NCEI search `totalCount` is the whole dataset, not the bbox count. Its bbox order is north, west, south, east.
- KartaView returns its error inside an HTTP 200 envelope.
- Count hits over the AOI extent, not a box at the centroid. A 2 km box at the centre of the 25 km Toronto stress polygon holds no Panoramax items. Its extent holds 1000. GBIF, DriveBC and PhenoCam were counted around the centroid and may undercount the stress AOIs.
- Wikimedia returns 429 under load. Without a backoff a 429 reads as 0 hits.
- A STAC search by bbox in Canada returns nothing for US-only collections (NAIP, 3DEP). That is coverage, not failure.
- usgs.gov returns 403 to scripts. Use the API hosts (`index.nationalmap.gov`, `api.waterdata.usgs.gov`).
- **CAUTION** No env runs the whole POC. `geoquery` lacks pyarrow and `msm` lacks rasterio. `pipeline.py` also reads PROJ data from `./projdata`, and every raster adapter fails without it. `recheck/adapters/go.sh` shows the working setup. `poc/README.md` names a `requirements.txt` that does not exist.
- Wikimedia search answers HTTP 200 with a `cirrussearch-too-busy-error` body under load. Retry it like a 429.

## Next sessions

1. Get the user's decision on S4: a commercial tier and quote-only adapters.
2. Ask the National Zoning Atlas for permission, or drop it for US zoning.
3. Get a free Mapillary token and fix the POC adapter.
4. Refactor the POC adapters to return observations, with quality metrics as features in the family they qualify.
5. Build adapters for the best candidates in the gap table, starting with S7, S8, S5 and S3.
6. Change the POC query to an AOI, a list of moments and a list of filters.
7. Build the picture-to-location pipeline as an adapter that returns a place and a radius.
8. Pin one env that runs every adapter, with PROJ data, before the production build.

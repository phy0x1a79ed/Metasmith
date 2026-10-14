# Source expansion report

## Purpose & Contents

This report prepares the next sessions, which will add many sources to each feature family. It holds:

- the quality metadata each kind of source exposes, and where the POC put it
- the gaps between the original brief and the POC, with a way to close each one
- the unbuilt candidates for each family, ranked for the next build round
- the decision the spec needs before more adapters get written

Inputs: `catalogue_reconciliation.csv`, `layer_inventory.csv`, `source_registry.csv`, `feature_values_long.csv`, and `geolocatable_data_registry.md` (the science agents' original 316-module catalogue). Live STAC probes from 2026-10-13 confirm the quality fields.

## Where the catalogue stands

There are 328 modules in scope. 70 were probed, 57 got an adapter, and 53 return data. 252 were never probed. 42 passed triage but have no adapter.

Working adapters by SourceType:

| SourceType | Working adapters |
|---|---|
| satellite | sentinel2_l2a, s2_signature_v1, landsat_c2l2_st, sentinel1_rtc, alos_palsar_mosaic, modis_13q1, esa_worldcover, io_lulc_annual_v02, hansen_gfc_v1_13, hgb, nrcan_landcover, usda_cdl, usda_csb_fiboa, jrc_gsw, noaa_nsidc_sic_cdr, cop_dem_glo30, mrdem_30 (part lidar) |
| airborne | usgs_namrad |
| drone | none |
| ground station | eccc_naps, epa_aqs_airdata, usgs_fdsn, wqp |
| field survey | macrostrat, gsc_surficial_1880a, gbif, mgnify, ena_geo, cdc_nwss, phac_wastewater |
| model | era5_open_meteo, cams_open_meteo, etopo_2022_30s_bed, ghs_pop_r2023a, ghs_smod_r2023a, lehd_lodes8, cdc_places, alphaearth_v1_annual, clay_v0_embeddings |
| registry | the 11 overture_* adapters, epa_echo, epa_echo_tri, epa_frs_sems, eccc_npri, eccc_ghgrp, tbs_fcsi, nrcan_900a, usgs_mineplant, wri_gppd, natural_earth_10m, nrcan_permafrost, statcan_*, tigerweb_*, bc_pmbc_parcel_fabric, bc_tantalis_crown, nrcan_alta, wikidata_sparql, cdc_nndss, phac_rvdss, statcan_odhf |

**CAUTION** Many "satellite" rows are derived products such as land cover, biomass or composites. A derived product is not a measurement. Use processing_level (below), not SourceType, to tell them apart.

## Quality metadata

### What the POC does now

Each adapter returns `(features, meta)`. The `meta` dict holds obs_date, res_m, item, licence and fill_type. It applies to every feature from that call. That record is the observation the user described. The spec flattened it away.

About 70 of the 814 feature names are quality metadata stored as features, across 42 adapters. They fall into five kinds:

- pixel counts: `*_n_px`, `aef_emb_pixel_count`, `ghspop_n_cells`
- distance to the measuring site: `naps_*_src_km`, `aqs_nearest_monitor_km`, `nsidc_sic_nearest_cell_km`
- vintage: `*_year`, `phacww_latest_date`
- sample size: `s2sig_n_scenes`, `clim_n_days`, `cams_n_hours`, `modis_n_composites`, `nwss_sites_county`
- join level and coverage: `statcan_popest_geo_level`, `bcpmbc_parcel_coverage_frac`, `echo_bbox_pad_km`

`s2_cloud_cover_pct` is the only scene-quality field. It is the cloud cover of the whole 110 km tile, not of the AOI.

### What each SourceType exposes

| SourceType | Available quality metadata | Where it lives |
|---|---|---|
| satellite, optical (S2 L2A) | cloud %, cloud shadow, thin cirrus, snow, nodata %, degraded %, sun zenith and azimuth, processing baseline, product type, orbit state, tile | STAC item properties (`eo:cloud_cover`, `s2:*_percentage`, `s2:mean_solar_*`, `s2:processing_baseline`) |
| satellite, optical (S2) | viewing incidence (off-nadir) per band, about 9° on the probed tile | `granule-metadata` asset (MTD_TL.xml). It is not in the item properties |
| satellite, optical (Landsat C2 L2) | cloud %, land cloud %, sun elevation and azimuth, `view:off_nadir`, correction level (L2SP), tier (T1/T2), WRS path/row | STAC item properties |
| satellite, AOI-level cloud | cloud and shadow fraction inside the AOI | derive it from the `SCL` band (S2) or `qa_pixel` (Landsat) |
| satellite, SAR (S1 RTC) | orbit direction, relative orbit, polarisations, mode, looks, resolution, orbit source, timeliness | STAC item properties. Incidence angle is a per-pixel asset |
| satellite, derived (MODIS, WorldCover, DEM) | product version, input missions, compositing period. MODIS reports cloud % per tile | STAC item properties. Pixel reliability is a QA band |
| airborne (NAIP) | GSD, year, state | STAC item properties. Nothing else |
| airborne lidar (3DEP COPC) | point count, acquisition window, USGS project id | STAC item properties. Quality level (QL1/QL2) is in USGS WESM, not STAC |
| hyperspectral (EMIT L2A) | scene cloud % | NASA CMR granule. EMIT is not on Planetary Computer |
| ground station | station distance, station count, observation count, completeness, year | computed by the adapter |
| model | grid resolution, time steps used, model version | computed by the adapter or from the dataset attributes |
| registry | snapshot date, join level (point, block, county, province), records joined, search radius | computed by the adapter |

Off-nadir matters for tasked high-resolution imagery. That means commercial sources and airborne surveys. S2 and Landsat always look nearly straight down.

### The pending spec change

Add an Observation level between QueryResult and Feature:

- Observation: source, family, source_type, time, licence, platform, sensor, processing_level, resolution_m, aoi_coverage, quality, features
- Feature: feature, value, SI_unit
- QueryResult: aoi, observations, errors

`quality` is an open map of the fields in the table above. `processing_level` uses the NASA levels: L1 calibrated, L2 geophysical per scene, L3 gridded composite, L4 model output. Registries take none. All 70 quality features move into `quality`. **This needs the user's approval before the next build round.** Every new adapter written to the flat spec has to be rewritten later.

## Gaps against the original brief

| Gap | Current state | How to close it |
|---|---|---|
| Band selection | Each adapter fixes its bands. The query cannot name a band or index | Add an optional `bands` / `indices` field to the query. Add a raw-reflectance mode to the optical adapters |
| Periodic time | The query takes one time plus a tolerance | Add an optional recurrence (for example "every July, 2018–2024") that fans out to one observation per period |
| Quality filters | The S2 and Landsat adapters hard-code cloud < 20/25 % | Add query filters (max cloud, max off-nadir, min sun elevation, min processing level) after the Observation level exists |
| Platform | 17 satellite adapters, 1 airborne, 0 drone, lidar only through MRDEM at 30 m | Build `naip`, 3DEP lidar (`3dep-lidar-dtm`, `-dsm`, `-hag` on Planetary Computer), `openaerialmap` for drone |
| Hyperspectral | None built. EMIT triaged reachable | Build `emit` through NASA CMR (free Earthdata login). Keep EnMAP/PRISMA as a stretch. PACE (`ocean_color`) covers water |
| Paid brokers | Out of scope. SkyFi, UP42 and Maxar are not catalogued | Add a `paid` licence tier and a quote-only adapter (archive search, price, no purchase). Free open-data programmes (Maxar Open Data, Umbra and Capella open SAR) come first |
| Correction level | L2 chosen silently | Record it as processing_level. Expose L1C (`sentinel2_l1c`, catalogued) for users who correct themselves |
| Raw data | Output is summary statistics only | Put the STAC item id and asset hrefs into each Observation. The caller can fetch pixels itself. The POC already keeps `item` |
| Zoning and planning | Missing. `cadastre_us` (with zoning) is unresolved. `overture_land_use` is land cover, not zoning | Catalogue the open municipal zoning feeds (US: NZA, state portals; Canada: provincial open data). Treat it as a new socio-economic sub-family |

## Expansion candidates per family

Priority comes from the catalogue (1 is highest). "Reachable" means triage passed but no adapter exists.

| Family | Build next | Then |
|---|---|---|
| socio-economic | `gridded_gdp`, `cdc_svi_eji` (registry), `accessibility_iso` (model) | `hmda`, `wikipedia_geo`, `business_estab` (reachable), zoning (new) |
| infrastructure | `ghsl_built`, `blackmarble` (reachable, satellite), `google_open_buildings`, `ms_buildings` (reachable) | `climate_trace`, `eprtr`, `fcc_uls`, `ookla` (NC), `housing_registry` |
| hazards | `nwis` (reachable, P1, ground station), `sentinel5p` (reachable, satellite), `drought` | `ibtracs`, `severe_wx` (reachable), `pfas_usgs`, `gemstat_waterbase`, `flood_zones` |
| macrobiology | `gedi`, `gedi_l4b` (reachable, satellite lidar), `canopy_height`, `jrc_tmf` | `cci_biomass`, `inat_ebird` (key), `obis`, `spam_earthstat`, `gaez`. `aafc_aci` failed and needs a retry |
| geology | `soilgrids` (P1), `terrain_derived` (reachable, P1), `egms` (P1, EU only) | `usgs_sgmc`, `onegeology`, `grav_anomaly`, `mag_anomaly`, `geochem_soil`, `ssurgo` (reachable), `nasadem` |
| microbiology-health | `ncbi_biosample`, `sandpiper`, `spire` (field survey) | `emp_qiita`, `globalfungi`, `logan`, `pathogen_genomics`, `vectorbase`, `ihme_lbd` (P1, restricted) |
| climate | `terraclimate`, `chirps`, `worldclim_chelsa` (model) | `daymet_prism`, `modis_lc_fire` (reachable) |
| spectral | `sentinel1_grd` (P1), `hls`, `naip` (reachable, airborne) | `sentinel2_l1c`, `modis_sr`, `ecostress`, `openaerialmap` (drone), `enmap_prisma` |
| water | `cmems` (P1), `mur_sst` | `ocean_color`, `grace` (reachable) |
| latent | `emit` (reachable, hyperspectral) | `cgls` |

Water has 6 features and climate has 12. They are the thinnest families and the cheapest to grow. Most candidates there are gridded STAC or HTTP products with no credentials.

## Next sessions

1. Get the user's decision on the Observation level.
2. Refactor the POC adapters to return Observations. Move the 70 quality features into `quality`.
3. Build the "Build next" column, thinnest family first: water, climate, then spectral and the platform gaps.
4. Add the query fields: bands, recurrence, quality filters.
5. Probe the 252 never-probed modules in bulk. Test every filter against a control, as the catalogue warns. MGnify returns HTTP 200 for an unknown parameter.

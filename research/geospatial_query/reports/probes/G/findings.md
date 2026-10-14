# Lane G: source_type for every source

`reports/apply_source_type.py` adds a `source_type` column right after `adapter` in `source_registry.csv` (76 rows, 75 distinct adapters; `epa_echo` appears twice) and `feature_values_long.csv`. It raises if an adapter is unmapped, or if a mapping names an adapter absent from the registry. Re-running it produces byte-identical files (md5 checked). Both CSVs had link count 1; the script still writes a temp file and renames over the original.

## Count per source_type (distinct adapters, all 75)

| source_type | adapters | of which working |
|---|---|---|
| registry | 35 | 32 |
| satellite | 18 | 17 |
| model | 9 | 9 |
| field survey | 7 | 7 |
| ground station | 4 | 4 |
| airborne | 1 | 1 |
| vehicle | 1 | 0 (failing) |
| drone, fixed camera, handheld | 0 | 0 |

## Adapters I assigned (not in the brief's table)

- aafc_aci: satellite. Annual Crop Inventory is a classification of satellite imagery. Failing adapter (404).
- mapillary_kartaview: vehicle. Street-level imagery from vehicle-mounted cameras. Failing adapter.
- osm_overpass: registry. Crowd-mapped vector snapshot; no sensing act. Failing adapter.
- acs5_api: registry. Published survey statistics as a table. Failing adapter (US-only, key required).
- donneesquebec_role: registry. Municipal assessment roll. Failing adapter.
- statcan_dwelling_value: registry. Covered by the brief's `statcan_*` wildcard.
- Wildcards expanded: overture_* to 9 concrete adapters in the registry (the brief says 11; the registry has 9), tigerweb_* to tigerweb_blocks2020 and tigerweb_aiannh, statcan_* to 4 adapters.

## Ambiguous types

- Satellite-derived products (esa_worldcover, io_lulc_annual_v02, hansen_gfc_v1_13, hgb, nrcan_landcover, usda_cdl, usda_csb_fiboa, jrc_gsw, aafc_aci): typed satellite, but observation_unit is a composite or classification, not an acquisition.
- mrdem_30: part lidar (airborne) and part satellite; typed satellite per the brief.
- cop_dem_glo30: TanDEM-X/SAR-derived DEM; typed satellite.
- noaa_nsidc_sic_cdr: passive-microwave satellite, but a gridded climate data record; typed satellite.
- alphaearth_v1_annual, clay_v0_embeddings: embeddings learned from satellite imagery; typed model per the brief, though the inputs are satellite.
- era5_open_meteo, cams_open_meteo: reanalysis (model); ghs_pop_r2023a, ghs_smod_r2023a: modelled from census and built-up layers; etopo_2022_30s_bed: compilation of many sources. All model.
- usgs_namrad: airborne radiometric survey (the only airborne source).
- usgs_fdsn, wqp, eccc_naps, epa_aqs_airdata: ground station (seismometers, sampling or monitoring sites). wqp mixes lab samples with sensors.
- macrostrat, gsc_surficial_1880a: field survey (geologic mapping); gbif: field survey, though it includes citizen-science and museum records.
- cdc_places: model (small-area estimates from a survey), per the brief; cdc_nndss and phac_rvdss are registry (case reports); cdc_nwss and phac_wastewater are field survey (samples).
- wikidata_sparql, natural_earth_10m, nrcan_permafrost: registry; the last two are compiled maps rather than registries of records.

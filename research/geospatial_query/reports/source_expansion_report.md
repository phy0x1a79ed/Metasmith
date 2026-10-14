# Source expansion brief

## Purpose & Contents

This brief is the starting point for the sessions that expand the geospatial query's sources. Read it before you add a source, change the spec or re-probe the catalogue. It holds:

- links to every input: the design artifact, the POC, the reports, the science project
- what an observation is, and why the current spec has no place for quality metadata
- the quality metadata each kind of source exposes, checked live on 2026-10-13
- the ten gaps between the user's original brief and the POC, each with new candidate sources
- the open decisions and the traps that cost time before

It does not repeat the catalogue or the POC code. Follow the links for those.

## Links

| What | Where |
|---|---|
| Design artifact (spec, features, DAG) | https://claude.ai/artifact/Nj52Qha3utLQH7RVkssZJb (private, v17) |
| Artifact source | [`figures/design/build.py`](../figures/design/build.py) builds `index.html` from [`template.html`](../figures/design/template.html) and the tables below |
| POC adapters (Python, one function per source) | [`poc/`](../poc/), entry point [`poc/run_all.py`](../poc/run_all.py), shared code [`poc/pipeline.py`](../poc/pipeline.py) |
| POC write-up | [`poc_report.md`](poc_report.md) |
| Design decisions from the science project | [`session-debrief.md`](session-debrief.md), [`metasmith_core_set.md`](metasmith_core_set.md) |
| Family definitions and rules | [`layer_families.md`](layer_families.md) |
| Original catalogue, 316 modules | [`geolocatable_data_registry.md`](geolocatable_data_registry.md) |
| Catalogue as a table | [`layer_inventory.csv`](layer_inventory.csv) |
| Outcome per catalogue module | [`catalogue_reconciliation.csv`](catalogue_reconciliation.csv), totals in [`funnel_counts.json`](funnel_counts.json) |
| Per-adapter status | [`source_registry.csv`](source_registry.csv) |
| Every POC feature value (15 AOIs) | [`feature_values_long.csv`](feature_values_long.csv) |
| Triage probes | [`triage_results_merged.csv`](triage_results_merged.csv), [`layer_slots_triaged.csv`](layer_slots_triaged.csv) |
| Test AOIs | [`../examples/test_aois.geojson`](../examples/test_aois.geojson) |
| Family corrections | [`apply_family_fixes.py`](apply_family_fixes.py). Re-run it after any fresh copy from the science project |
| Science project | Claude Science `proj_8be587fb267f`, conversation `ea94976a-52cc-40e1-9649-39706ecd4d0e`. Files live under `~/.claude-science/orgs/0e7f7957-d72e-4f89-b89e-32275f97b806/artifacts/proj_8be587fb267f/<uuid>/v<hash>_<name>`. Take the newest by mtime |

**CAUTION** The local tables differ from the science project's copies. `apply_family_fixes.py` moved three family assignments.

## Where the sources stand

The catalogue held 317 modules in scope. 11 national modules were added, which gives 328. 70 were probed, 57 got an adapter and 53 return data. 4 adapters fail (mapillary, kartaview, osm_overpass, aafc_aci). 4 modules were dropped. 252 were never probed. 97 triage candidates match no catalogue module.

The user considers the catalogue already worked through. Do not treat its leftovers as the expansion plan. The gaps below are the plan. The leftovers stay in `catalogue_reconciliation.csv` for when a gap points at one.

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

Water (6 features) and climate (12 features) are the thinnest families. The design artifact's features panel has the counts for every family.

## What an observation is

The standard definition is OGC/ISO 19156 Observations & Measurements ([OGC](https://www.ogc.org/standard/om/)), with its W3C ontology form SOSA/SSN ([W3C](https://www.w3.org/TR/vocab-ssn/)). An observation is one act of sensing. It has:

- a procedure: the sensor on its platform
- a feature of interest: the place observed
- a phenomenon time: when the sensing happened
- results, with a result quality

For imagery, one observation is one acquisition: one scene, granule or STAC item. The sensing conditions belong to the acquisition: off-nadir angle, sun angle, cloud cover, orbit and processing level. Features such as NDVI mean and NDVI p90 are results computed from it. Many features therefore share one observation.

An adapter does not always return one observation. It returns a **product**, which takes one of three shapes:

| Product shape | Examples | Honest quality fields |
|---|---|---|
| one acquisition | sentinel2_l2a, landsat_c2l2_st, sentinel1_rtc | off-nadir, sun angles, cloud cover (tile and AOI), processing level, orbit |
| a composite of many acquisitions | modis_13q1 (16-day), s2_signature_v1 (season), esa_worldcover, hansen_gfc, era5 (days), epa_aqs (annual means) | scene or reading count, clear-pixel share, period, input missions, distance to the station |
| a registry snapshot | overture_*, eccc_npri, statcan_*, wikidata | snapshot date, join level (point, block, county, province), record count, search radius |

A registry snapshot is not an act of sensing. It still needs provenance and a vintage.

## Quality metadata

### What the POC keeps

The POC keeps one record per AOI × adapter: 792 records over 15 AOIs. Each record holds obs_date, res_m, item, licence and fill_type. No record holds an off-nadir angle or a sun angle.

Only 45 records carry a real STAC scene id: 15 AOIs × sentinel2_l2a, landsat_c2l2_st and sentinel1_rtc. Re-query those ids to recover the angles and the cloud breakdown. The other 639 `item` values are labels or product versions, not observations.

About 70 of the 814 feature names in 42 adapters are quality metadata stored as features:

- pixel counts: `*_n_px`, `aef_emb_pixel_count`, `ghspop_n_cells`
- distance to the measuring site: `naps_*_src_km`, `aqs_nearest_monitor_km`, `nsidc_sic_nearest_cell_km`
- vintage: `*_year`, `phacww_latest_date`
- sample size: `s2sig_n_scenes`, `clim_n_days`, `cams_n_hours`, `modis_n_composites`, `nwss_sites_county`
- join level and coverage: `statcan_popest_geo_level`, `bcpmbc_parcel_coverage_frac`, `echo_bbox_pad_km`
- controls: `ovt_control_*`, `mgnify_control_count`, `wd_control_entities`

`s2_cloud_cover_pct` is the only scene-quality value. It is the cloud cover of the whole 110 km tile, not of the AOI. The S2 and Landsat adapters hard-code cloud < 20 % and < 25 % ([`poc/pipeline.py`](../poc/pipeline.py), `_a_s2` and `_a_landsat_st`).

### What the sources expose

Checked live against Planetary Computer ([STAC API](https://planetarycomputer.microsoft.com/api/stac/v1)) and NASA CMR ([search](https://cmr.earthdata.nasa.gov/search)) on 2026-10-13. The field names follow the STAC extensions [eo](https://github.com/stac-extensions/eo), [view](https://github.com/stac-extensions/view), [sat](https://github.com/stac-extensions/sat) and [processing](https://github.com/stac-extensions/processing).

| Source | Quality metadata | Where it lives |
|---|---|---|
| Sentinel-2 L2A | `eo:cloud_cover`, `s2:cloud_shadow_percentage`, `s2:thin_cirrus_percentage`, `s2:high_proba_clouds_percentage`, `s2:snow_ice_percentage`, `s2:nodata_pixel_percentage`, `s2:degraded_msi_data_percentage`, `s2:mean_solar_zenith`, `s2:mean_solar_azimuth`, `s2:processing_baseline`, `s2:product_type`, `sat:orbit_state`, `sat:relative_orbit`, `s2:mgrs_tile` | item properties |
| Sentinel-2 L2A | viewing incidence (off-nadir) per band, 9.0° on tile 10UFV | `granule-metadata` asset (MTD_TL.xml, `Mean_Viewing_Incidence_Angle_List`). It is not in the item properties |
| Landsat C2 L2 | `eo:cloud_cover`, `landsat:cloud_cover_land`, `view:off_nadir`, `view:sun_elevation`, `view:sun_azimuth`, `landsat:correction` (L2SP), `landsat:collection_category` (T1/T2), `landsat:wrs_path`, `landsat:wrs_row` | item properties |
| S2 and Landsat, AOI level | cloud and shadow share inside the AOI | derive it from the `SCL` band (S2) or the `qa_pixel` band (Landsat) |
| Sentinel-1 RTC | `sat:orbit_state`, `sat:relative_orbit`, `sar:polarizations`, `sar:instrument_mode`, `sar:looks_*`, `sar:resolution_*`, `s1:orbit_source`, `s1:product_timeliness`, `s1:processing_level` | item properties. The incidence angle is a per-pixel asset |
| HLS L30 | `eo:cloud_cover`, `view:azimuth`, `view:sun_azimuth` | item properties |
| MODIS 13Q1 | `eo:cloud_cover`, platform (terra or aqua), tile | item properties. Pixel reliability is a QA band |
| ESA WorldCover, Copernicus DEM | product version, input missions, period | item properties |
| NAIP | `gsd`, `naip:year`, `naip:state` | item properties. Nothing else |
| 3DEP lidar COPC | `pc:count` (points), acquisition window, `3dep:usgs_id` | item properties. Quality level (QL1/QL2) is in USGS WESM, not STAC |
| EMIT L2A | `cloud_cover` | NASA CMR granule. EMIT is not on Planetary Computer STAC (the collection returns 404) |
| ground stations | distance to the station, station count, reading count, completeness, year | the adapter computes them |
| models | grid resolution, time steps used, model version | the adapter computes them or reads the dataset attributes |
| registries | snapshot date, join level, record count, search radius | the adapter computes them |

The off-nadir angle varies for tasked high-resolution imagery: commercial satellites and airborne surveys. Sentinel-2 and Landsat look nearly straight down. Off-nadir becomes a useful filter only after gap G7 (commercial and open commercial imagery) is closed.

## Proposed spec change

**This needs the user's approval.** The user agreed that features group into observations. The two-level shape below is not approved yet.

- **Observation** is composed of: source, sensor, platform, source_type, time, processing_level, resolution_m, aoi_coverage, quality, assets
- **Product** is composed of: source, family, source_type, time (one of time, Interval), licence, processing_level, observations (list of Observation, or a summary for a composite), quality, features
- **Feature** is composed of: feature, value, SI_unit
- **QueryResult** is composed of: aoi, products, errors

`quality` is an open map of the fields in the table above. `processing_level` uses the NASA levels: L1 calibrated, L2 geophysical per scene, L3 gridded composite, L4 model output. A registry takes none. `assets` holds the STAC item id and the asset hrefs (gap G9). All 70 quality features move into `quality`.

Every adapter written to the flat spec has to be rewritten later. Settle this before the next build round.

## Gaps against the original brief

The user's original brief asked for: an AOI as a lat/lon box plus periodic time plus spectral band, cloud cover, off-nadir angle, multispectral and hyperspectral, satellite vs plane vs lidar vs drone, paid brokers (SkyFi) and government agencies (NASA), correction steps (orthorectified, atmospheric), and knowledge representation for GIS and land-use records.

None of the candidate sources below are in the original catalogue unless marked. None are probed. The links resolved on 2026-10-13. usgs.gov returns 403 to scripts.

### G1. Observations and quality metadata

- **State:** no observation level. Quality is filed as features (see above).
- **Close it:** adopt the spec change. Refactor the POC adapters to return products. Re-query the 45 scene records to backfill angles.
- **Families:** all.

### G2. Band selection

- **State:** each adapter fixes its bands. The query names families only.
- **Close it:** add an optional `bands` or `indices` field to the query. Resolve band names through the STAC `eo:bands` metadata. Resolve index names through [Awesome Spectral Indices](https://github.com/awesome-spectral-indices/awesome-spectral-indices) (Python: `spyndex`).
- **Families:** spectral, macrobiology, water.

### G3. Periodic time

- **State:** the query takes one time plus a tolerance (default infinite). The user wants the result to hold the fetched data and a view that splits it into the periods requested. The helper that expands a recurrence into a list of times left the spec, not the plan.
- **Close it:** fan one query out per time. For STAC sources, search a date range once and bin the items. [openEO](https://openeo.org) defines a time-series process model worth borrowing.
- **Families:** spectral, climate, macrobiology, hazards.

### G4. Quality filters in the query

- **State:** hard-coded cloud thresholds.
- **Close it:** add query filters (maximum cloud, maximum off-nadir, minimum sun elevation, processing level) after G1. Push them into the STAC query where the property exists. Filter AOI cloud after the read.
- **Families:** spectral, plus every imagery-derived family.

### G5. Airborne, lidar and drone

- **State:** one airborne adapter (usgs_namrad, radiometrics). Lidar only through MRDEM at 30 m. No drone source. HRDEM 1 m lidar was probed and covers 6 of 12 POC AOIs. It is absent at the prairie AOIs ([`metasmith_core_set.md`](metasmith_core_set.md)).
- **Candidates:**
  - USGS 3DEP lidar on Planetary Computer, as ready layers: [DTM](https://planetarycomputer.microsoft.com/dataset/3dep-lidar-dtm), DSM, HAG, intensity, classification (catalogued as `natl_lidar`)
  - [NAIP](https://planetarycomputer.microsoft.com/dataset/naip) aerial imagery, 0.3–1 m, US (catalogued, triage reachable)
  - [HRDEM](https://open.canada.ca/data/en/dataset/957782bf-847c-4644-a757-e383c0057995), Canada 1 m lidar
  - [NEON AOP](https://www.neonscience.org/data-collection/airborne-remote-sensing): airborne lidar, hyperspectral and RGB over US NEON sites
  - [OpenTopography](https://opentopography.org): lidar point clouds and DEMs, API
  - [NOAA Digital Coast](https://coast.noaa.gov/digitalcoast/): coastal lidar and imagery
  - drone: [OpenAerialMap](https://openaerialmap.org) (catalogued, not probed), [GeoNadir](https://geonadir.com)
- **Families:** geology, macrobiology, infrastructure, spectral.

### G6. Hyperspectral

- **State:** none built.
- **Candidates:**
  - [EMIT](https://earth.jpl.nasa.gov/emit/), 285 bands, 60 m, through NASA CMR with a free Earthdata login (catalogued, triage reachable)
  - [AVIRIS](https://aviris.jpl.nasa.gov) airborne campaigns
  - NEON AOP hyperspectral (see G5)
  - [EnMAP](https://www.enmap.org) and PRISMA, free registration, sparse tasking (catalogued as `enmap_prisma`)
  - [PACE](https://pace.gsfc.nasa.gov) OCI, hyperspectral ocean colour (catalogued within `ocean_color`)
  - Planet Tanager sample products in [Planet's open data STAC](https://www.planet.com/data/stac/browser/)
- **Families:** spectral, latent, geology (mineralogy), water, hazards (methane plumes).

### G7. Commercial imagery and paid brokers

- **State:** out of scope under the "free and open" decision. The licence tiers have no commercial level.
- **Open commercial programmes (free, carry off-nadir metadata):**
  - [Maxar Open Data](https://registry.opendata.aws/maxar-open-data/): event imagery, STAC on AWS
  - [Umbra](https://registry.opendata.aws/umbra-open-data/), [Capella](https://registry.opendata.aws/capella_opendata/) and [ICEYE](https://registry.opendata.aws/iceye-opendata/): open SAR samples
  - [Satellogic EarthView](https://registry.opendata.aws/satellogic-earthview/)
  - Planet: [NICFI](https://planetarycomputer.microsoft.com/dataset/planet-nicfi-analytic) (tropics, on Planetary Computer) and [open SkySat data](https://www.planet.com/data/stac/browser/)
- **Paid brokers:** [SkyFi](https://skyfi.com), [UP42](https://up42.com), [Sentinel Hub](https://www.sentinel-hub.com). An adapter could search the archive and return a quote (scene, date, off-nadir, cloud, price) without buying.
- **Decision needed:** add a commercial licence tier, and decide whether quote-only adapters are in scope.
- **Families:** spectral, infrastructure, hazards.

### G8. Correction level

- **State:** the science project chose processed Level-2 data. The output does not record the level.
- **Close it:** record `processing_level` (G1). Offer L1C for callers who correct themselves: Sentinel-2 L1C is on [Earth Search](https://earth-search.aws.element84.com/v1) (`sentinel-2-l1c`). Planetary Computer returned no L1C items for the test tile.
- **Families:** spectral.

### G9. Returning the data itself

- **State:** the output is summary statistics only.
- **Close it:** put the STAC item id and the asset hrefs into each observation (`assets`). The caller fetches pixels itself. The POC already keeps `item` for the 45 scene records.
- **Families:** all imagery-derived families.

### G10. Zoning and land-use records

- **State:** missing. `layer_families.md` flags it. `cadastre_us` (with zoning) is unresolved. `overture_land_use` is land cover, not zoning. Parcel adapters exist for BC and Quebec only.
- **Candidates:**
  - [National Zoning Atlas](https://www.zoningatlas.org/atlas): US zoning by jurisdiction
  - [Regrid](https://regrid.com): US parcels with zoning, paid (catalogued under `cadastre_us`)
  - [BC Agricultural Land Reserve](https://www.alc.gov.bc.ca)
  - PAD-US: US protected areas, USGS Gap Analysis Project
  - [EU Urban Atlas](https://land.copernicus.eu/en/products/urban-atlas)
  - municipal open-data zoning by-laws (Toronto, Vancouver, Calgary and others), one adapter per city
- **Families:** socio-economic (new sub-family: planning and zoning).

## Traps

- MGnify returns HTTP 200 for an unknown query parameter and serves the unfiltered catalogue. Test every filter against a control: a differential count, not a 200 (`geolocatable_data_registry.md`).
- `eo:cloud_cover` is per tile. An AOI can be clear under a 60 % tile or cloudy under a 5 % tile.
- A derived product (land cover, biomass, a composite) has SourceType satellite but is not a measurement. Use processing_level to tell them apart.
- The triage did not keep endpoint URLs. `aafc_aci` passed triage, then failed in the POC with a 404 that nobody could trace ([`poc_report.md`](poc_report.md)). Keep the endpoint with every probe.
- Planetary Computer blob reads need a SAS token from its token endpoint. Unsigned reads return HTTP 409 and look like an absent layer ([`metasmith_core_set.md`](metasmith_core_set.md)).
- A STAC search by bbox in Canada returns nothing for US-only collections (NAIP, 3DEP). That is coverage, not failure.

## Next sessions

1. Get the user's decision on the Observation and Product levels.
2. Get the user's decision on G7: a commercial tier and quote-only adapters.
3. Refactor the POC adapters to return products. Move the quality features into `quality`. Backfill angles for the 45 scene records.
4. Close G5, G6 and G10 with new sources. These are the gaps with no source at all.
5. Add the query fields for G2, G3 and G4.
6. Update the design artifact's spec panel. Rebuild with `figures/design/build.py`.

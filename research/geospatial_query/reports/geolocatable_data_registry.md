# Master registry — geolocatable data sources

**316 candidate modules** across 35 groups, in 3 batches.
One row = one module (one source adapter) consuming `geospatial_query` and producing `gis_layer`.

## Batches

| Batch | Modules | Scope |
|---|---|---|
| 1 | 119 | Core Earth observation, climate, terrain, land cover, vector basemap |
| 2 | 99 | Atypical physics and modality: geophysics, deformation, marine, deep time, ground-level, activity, industry |
| 3 | 98 | Record-level geolocated data: geology maps, sequences, health, contamination, economics, knowledge |

## Verified this session

Four endpoints were actually called, not recalled:

| module | what was confirmed |
|---|---|
| `macrostrat` | lat/lng returns geologic units, lithology, age range |
| `mgnify` | latitude_gte/longitude_gte bbox filter (UNDERSCORES; hyphens silently ignored) |
| `ena_geo` | query=geo_box1(lat1,lon1,lat2,lon2) returns samples with location |
| `eq_catalog` | USGS FDSN bbox+time+magnitude; 342 events in a +/-1.5deg NL box since 1980 |

> **Trap worth remembering.** MGnify returns HTTP 200 and well-formed JSON for *unknown* query parameters, silently ignoring the filter and serving the unfiltered catalogue — a hyphenated `latitude-gte` returned exactly the same count (435,812) as a deliberately nonsense parameter, while `latitude_gte` returned 14,979. **A 200 is not verification; a differential count is.** Assume other APIs in this registry do the same and test every filter against a control.

## Totals

| Priority | Modules |
|---|---|
| 1 | 30 |
| 2 | 72 |
| 3 | 118 |
| 4 | 96 |

| Licence tier | Modules |
|---|---|
| `P` | 235 |
| `P/R` | 34 |
| `R` | 17 |
| `NC` | 12 |
| `SA` | 9 |
| `P/SA` | 6 |
| `P/R/X` | 1 |
| `NC/P` | 1 |
| `P/SA/R` | 1 |

**231 of 316 modules need no credentials.** 47 free registration, 15 an API key, 21 vary by jurisdiction, 2 Earth Engine only.

**Column key.** `res_m` native resolution in metres (`vector`/`point`/`admin` = not gridded). `lic_tier`: `P` permissive · `SA` share-alike · `NC` noncommercial · `R` restricted/registration · `X` paid (slashes = mixed by product). `access`: `stac` · `http` direct file/COG · `parquet` · `api` REST · `cds` Copernicus CDS · `gcs`/`s3` bucket · `ee` Earth Engine only · `portal` manual. `auth`: `none` · `free-reg` · `key` · `varies` · `ee`.

> Accuracy: group, source, layers and licence tier are reliable. Exact endpoints, collection ids and precise licence terms are **probe targets** except where verified above; rows whose notes say VERIFY are known-uncertain.

# Batch 1 — Core Earth observation, climate, terrain, land cover, vector basemap

## Climate/Weather (13)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `era5` | ERA5 / ERA5-Land reanalysis | 2m temp, dewpoint, precip, wind, radiation, soil moisture+temp (4 layers), snow, evaporation, pressure | 31000/9000 | hourly, 1950- | global | Copernicus open | `P` | `cds` | `key` | 1 | THE free historical weather source. CDS API key needed. Zarr/NetCDF not scenes |
| 20 | `chirps` | CHIRPS v2 | precipitation | 5000 | daily/pentad/monthly, 1981- | 50N-50S | public domain | `P` | `http` | `none` | 2 | Gauge-blended; better than reanalysis for tropical precip |
| 21 | `terraclimate` | TerraClimate | monthly climate + water balance, PET, soil moisture, PDSI | 4000 | monthly, 1958- | global | CC-BY | `P` | `stac` | `none` | 2 |  |
| 22 | `worldclim_chelsa` | WorldClim 2.1 / CHELSA | 19 bioclimatic variables, monthly climatologies | 1000 | climatology + projections | global | CC-BY 4.0 | `P` | `http` | `none` | 2 | Standard for species/suitability work |
| 48 | `agera5` | AgERA5 | agromet daily aggregates | 9000 | daily, 1979- | global | Copernicus open | `P` | `cds` | `key` | 3 | Pre-aggregated for agriculture |
| 49 | `daymet_prism` | Daymet / PRISM | daily/monthly climate | 1000/4000 | daily, 1980- | N.America / US | public domain / use-restricted | `P/R` | `http` | `none` | 3 | PRISM has use restrictions on some products - VERIFY |
| 50 | `imerg` | GPM IMERG | precipitation | 11000 | 30min, 2000- | global | NASA open | `P` | `http` | `free-reg` | 3 |  |
| 51 | `solar_atlas` | Global Solar Atlas / NSRDB | GHI, DNI, DIF, PVOUT, temp | 250-1000 | climatology + hourly | global / US | CC-BY / public domain | `P` | `http` | `none` | 3 | Siting use case |
| 52 | `wind_atlas` | Global Wind Atlas | wind speed/power density at heights | 250 | climatology | global | CC-BY 4.0 | `P` | `http` | `none` | 3 | Siting use case |
| 95 | `aridity` | CGIAR-CSI Global Aridity / PET | aridity index, PET | 1000 | climatology | global | CC-BY | `P` | `http` | `none` | 4 |  |
| 96 | `grace` | GRACE / GRACE-FO | total water storage anomaly, groundwater | ~100000 | monthly, 2002- | global | NASA open | `P` | `http` | `none` | 4 | Very coarse; AlphaEarth decode target |
| 97 | `koppen` | Koppen-Geiger classification | climate class | 1000 | present + future | global | CC-BY | `P` | `http` | `none` | 4 | Cheap single-value context layer |
| 98 | `nex_gddp` | NEX-GDDP-CMIP6 | downscaled climate projections | 25000 | daily, 1950-2100 | global | public domain | `P` | `stac` | `none` | 4 | Future scenarios |

## Elevation/Structure (11)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | `copernicus_dem` | Copernicus DEM GLO-30 / GLO-90 | elevation (DSM) | 30/90 | static ~2011-15 | global | ESA open | `P` | `stac` | `none` | 1 | Best free global DEM |
| 3 | `terrain_derived` | Derived terrain (compute) | slope, aspect, curvature, TPI, TWI, flow acc, hillshade | inherits | static | global | n/a | `P` | `http` | `none` | 1 | TIER-2 derivation, not a source. Cheap, high value |
| 23 | `canopy_height` | Global canopy height maps | canopy height | 1-30 | 1-few epochs | global | CC-BY mostly | `P` | `http` | `none` | 2 | Lang/ETH 10m, Meta-WRI 1m, Potapov/UMD 30m - separate adapters, VERIFY each |
| 24 | `gedi` | GEDI L2A/L2B/L4A | canopy height metrics (rh*), PAI, AGB density | 25 footprints | 2019-, sparse | 51N-51S | NASA open | `P` | `http` | `free-reg` | 2 | Sparse footprints, not raster - different data model |
| 25 | `nasadem` | NASADEM / SRTM v3 | elevation | 30 | static 2000 | global (60N-56S) | NASA open | `P` | `stac` | `none` | 2 |  |
| 53 | `aw3d30` | ALOS World 3D AW3D30 | elevation (DSM) | 30 | static | global | JAXA open | `R` | `http` | `free-reg` | 3 |  |
| 54 | `fabdem` | FABDEM | bare-earth DEM (forest+building removed) | 30 | static | global | varies | `NC` | `portal` | `free-reg` | 3 | VERIFY license - non-commercial restriction reported |
| 55 | `icesat2` | ICESat-2 ATL03/ATL08 | photon heights, terrain+canopy height | ~20 segments | 2018-, sparse | global | NASA open | `P` | `http` | `free-reg` | 3 | Sparse tracks |
| 56 | `merit_dem` | MERIT DEM / MERIT Hydro | hydrologically-conditioned elevation, flow dir/acc | 90 | static | global | CC-BY-NC? | `NC` | `http` | `none` | 3 | VERIFY license tier |
| 57 | `natl_lidar` | National lidar programmes | 1m DEM/DSM, point clouds, derived structure | 0.5-2 | 1-10y | per-country | varies | `P/R` | `portal` | `varies` | 3 | US 3DEP, NL AHN, DK, NO, FI, SE, ES, CH, FR LiDAR HD, NZ, UK EA, parts AU |
| 99 | `aster_gdem` | ASTER GDEM v3 | elevation | 30 | static | global | NASA open | `P` | `http` | `free-reg` | 4 | Noisier than alternatives |

## Embeddings (4)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | `alphaearth` | AlphaEarth Satellite Embedding V1 | 64-dim annual embedding + inferred layers via regression | 10 | annual 2017-2025 | global land | CC-BY 4.0 | `P` | `gcs` | `none` | 1 | VERIFY public vs requester-pays. Can fill many layer cells by inference |
| 58 | `major_tom` | Major TOM embeddings | Clay/DINOv2/SigLIP embeddings over S2/S1 | varies | multi-epoch | global | CC-BY | `P` | `parquet` | `none` | 3 | Alternative to AlphaEarth; multiple encoders |
| 100 | `clay_prithvi` | Clay v1.5 / Prithvi (run inference) | own embeddings on demand | inherits | on demand | global | Apache/open | `P` | `http` | `none` | 4 | Requires GPU inference - different cost profile |
| 101 | `mosaiks` | MOSAIKS random features | 512 random conv features | ~1000 | static | global | CC-BY | `P` | `http` | `none` | 4 | Cheap baseline featurization |

## Land cover/Change (18)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | `esa_worldcover` | ESA WorldCover | 11-class land cover | 10 | 2020, 2021 | global | CC-BY 4.0 | `P` | `stac` | `none` | 1 |  |
| 6 | `ghsl` | GHSL (GHS-BUILT-S/H/V, POP, SMOD) | built surface, BUILDING HEIGHT, volume, population, settlement class | 10/100 | 5y epochs 1975-2030 | global | CC-BY 4.0 | `P` | `http` | `none` | 1 | Building height globally - rare and valuable |
| 7 | `hansen_gfc` | Hansen Global Forest Change | treecover2000, annual loss year, gain, lossyear | 30 | annual, 2000- | global | CC-BY 4.0 | `P` | `http` | `none` | 1 | Directly serves forest-cover-over-time use case |
| 8 | `jrc_gsw` | JRC Global Surface Water | water occurrence, seasonality, recurrence, change, transitions | 30 | 1984- | global | Copernicus open | `P` | `http` | `none` | 1 |  |
| 27 | `dynamic_world` | Dynamic World | 9-class probabilities + label, near-real-time | 10 | per-S2-scene, 2015- | global | CC-BY 4.0 | `P` | `ee` | `ee` | 2 | EE-only access is the catch |
| 28 | `jrc_tmf` | JRC Tropical Moist Forest | deforestation, degradation, regrowth, annual change | 30 | annual, 1990- | tropics | Copernicus open | `P` | `http` | `none` | 2 | Better than Hansen for degradation |
| 62 | `corine` | CORINE Land Cover + CLC+ Backbone | 44-class land cover | 100 / 10 | 6y, 1990- | Europe | Copernicus open | `P` | `http` | `free-reg` | 3 |  |
| 63 | `esa_cci_lc` | ESA CCI Land Cover | 22-class land cover | 300 | annual 1992- | global | ESA open | `P` | `http` | `free-reg` | 3 | Long time series |
| 64 | `esri_lulc` | Esri 10m Land Cover | 9-class land cover | 10 | annual 2017- | global | CC-BY | `P` | `stac` | `none` | 3 |  |
| 65 | `eu_lpis` | EU LPIS / crop declarations | declared parcel geometry + crop code | vector | annual | per-member-state | varies | `P/R` | `portal` | `varies` | 3 | NL BRP, FR RPG, DK, DE, ES. Closest thing to free cadastre+crop |
| 66 | `firms` | FIRMS active fire / FireCCI | active fire detections, burned area | 375/1000 | near-real-time | global | NASA open | `P` | `api` | `key` | 3 |  |
| 67 | `mapbiomas` | MapBiomas | annual land cover/use, mining, pasture | 30 | annual, 1985- | S.America, Indonesia, Africa | CC-BY-SA | `SA` | `http` | `none` | 3 | Includes explicit MINING class - mining use case |
| 68 | `nlcd` | NLCD | land cover, impervious, canopy | 30 | 2-3y, 1985- | US | public domain | `P` | `stac` | `none` | 3 |  |
| 69 | `usda_cdl` | USDA Cropland Data Layer | annual crop type | 30 | annual, 1997- | US | public domain | `P` | `http` | `none` | 3 | Best crop-type labels anywhere |
| 70 | `worldcereal` | ESA WorldCereal | crop type, active cropland, irrigation | 10 | seasonal 2021- | global | CC-BY | `P` | `stac` | `none` | 3 |  |
| 71 | `wsf` | World Settlement Footprint / WSF-Evolution | settlement extent + evolution | 10/30 | annual 1985-2015 | global | CC-BY | `P` | `http` | `none` | 3 |  |
| 105 | `glc_fcs30` | GLC_FCS30 / GlobeLand30 | fine land cover classes | 30 | multi-epoch | global | CC-BY / varies | `P` | `http` | `none` | 4 | VERIFY |
| 106 | `mangrove_watch` | Global Mangrove Watch | mangrove extent + change | 10-25 | multi-epoch 1996- | coastal global | CC-BY | `P` | `http` | `none` | 4 |  |

## Optical (15)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | `landsat_c2l2` | Landsat 4-9 Collection 2 L2 | surface reflectance, SURFACE TEMPERATURE (ST), QA_PIXEL | 30/100 | 16d, 1982- | global | USGS public domain | `P` | `stac` | `none` | 1 | Only free global source of surface temperature at 30m |
| 10 | `modis_bio` | MODIS MOD11/13/15/16/17 | LST, NDVI/EVI, LAI/FPAR, ET, GPP/NPP | 500/1000 | 8-16d, 2000- | global | NASA open | `P` | `stac` | `none` | 1 | Many biophysical layers from one adapter - high value/effort ratio |
| 11 | `sentinel2_l2a` | Sentinel-2 MSI L2A | surface reflectance B1-B12, SCL scene class, cloud prob, AOT, WVP | 10/20/60 | 5d, 2017- | global | Copernicus open | `P` | `stac` | `none` | 1 | Earth Search + MPC + CDSE. Workhorse module. |
| 29 | `blackmarble` | VIIRS VNP46 Black Marble | nighttime lights radiance | 500 | daily/monthly, 2012- | global | NASA open | `P` | `http` | `free-reg` | 2 | Activity/development proxy |
| 30 | `cgls` | Copernicus Global Land Service | LAI, FAPAR, FCOVER, NDVI, albedo, soil moisture, burnt area, water bodies | 300/1000 | 10d, 1999- | global | Copernicus open | `P` | `http` | `free-reg` | 2 | Pre-computed biophysical vars; many layers per adapter |
| 31 | `hls` | HLS S30/L30 v2 | harmonized surface reflectance | 30 | 2-3d, 2013- | global | NASA open | `P` | `stac` | `free-reg` | 2 | NASA LP DAAC / CMR; Earthdata login |
| 32 | `modis_sr` | MODIS MOD09/MYD09 | surface reflectance | 250/500 | daily, 2000- | global | NASA open | `P` | `stac` | `none` | 2 | Daily - fills cloud gaps |
| 33 | `naip` | NAIP | aerial RGB+NIR orthoimagery | 0.6-1 | ~2-3y, 2003- | US only | public domain | `P` | `stac` | `none` | 2 | Highest-res free imagery in US |
| 34 | `sentinel2_l1c` | Sentinel-2 MSI L1C | TOA reflectance B1-B12 | 10/20/60 | 5d, 2015- | global | Copernicus open | `P` | `stac` | `none` | 2 | Fallback pre-2017 / where L2A absent |
| 72 | `modis_lc_fire` | MODIS MCD12Q1 / MCD64A1 | land cover class, burned area | 500 | annual / monthly | global | NASA open | `P` | `stac` | `none` | 3 |  |
| 73 | `natl_ortho` | National orthophoto portals | aerial RGB/CIR orthoimagery | 0.05-0.5 | 1-5y | per-country | varies | `P/R` | `portal` | `varies` | 3 | NL PDOK, FR IGN, ES PNOA, DK, NO, SE, FI, EE, CH swisstopo, DE per-state, JP, NZ LINZ, AU. Long tail - one adapter per country |
| 74 | `sentinel3` | Sentinel-3 OLCI / SLSTR | ocean+land colour, LST, FRP | 300/1000 | daily, 2016- | global | Copernicus open | `P` | `stac` | `none` | 3 |  |
| 75 | `viirs` | VIIRS VNP09/VNP21/VNP13 | surface reflectance, LST, vegetation indices | 375/750 | daily, 2012- | global | NASA open | `P` | `stac` | `free-reg` | 3 | MODIS continuity |
| 107 | `dmsp_ols` | DMSP-OLS nighttime lights | stable lights | 1000 | annual, 1992-2013 | global | NOAA open | `P` | `ee` | `ee` | 4 | Historical extension of Black Marble |
| 108 | `landsat_c2l1_mss` | Landsat 1-5 MSS C2 L1 | TOA 4-band | 60 | 18d, 1972- | global | USGS public domain | `P` | `stac` | `none` | 4 | Deep archive only; no SR |

## SAR (4)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | `sentinel1_grd` | Sentinel-1 GRD | VV, VH backscatter, incidence angle | 10 | 6-12d, 2014- | global | Copernicus open | `P` | `stac` | `none` | 1 | Cloud-penetrating; essential in tropics |
| 35 | `sentinel1_rtc` | Sentinel-1 RTC | terrain-corrected backscatter | 10 | 6-12d, 2014- | global | Copernicus open | `P` | `stac` | `none` | 2 | MPC/ASF; analysis-ready, prefer over raw GRD |
| 76 | `palsar_mosaic` | ALOS PALSAR/PALSAR-2 annual mosaic | HH, HV L-band + forest/non-forest | 25 | annual, 2007- | global | JAXA open | `R` | `http` | `free-reg` | 3 | L-band penetrates canopy; biomass-relevant |
| 109 | `nisar` | NISAR L+S band | interferometric SAR, coherence | ~10 | 12d, 2025- | global | NASA/ISRO open | `P` | `stac` | `free-reg` | 4 | New mission - verify data availability and maturity |

## Soil/Geology (9)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 13 | `soilgrids` | SoilGrids 2.0 (ISRIC) | clay, sand, silt, pH, SOC, CEC, bulk density, N at 6 depths + uncertainty | 250 | static | global | CC-BY 4.0 | `P` | `http` | `none` | 1 | Single highest-value soil adapter |
| 36 | `mine_polygons` | Global mining land use (Maus et al.) | mine footprint polygons | vector | 2019 epoch | global | CC-BY 4.0 | `P` | `http` | `none` | 2 | Directly serves the mining use case - polygons of mining land use |
| 77 | `mrds` | USGS MRDS / MRDATA | mineral deposit points, commodity, status | vector | static | global (US-complete) | public domain | `P` | `http` | `none` | 3 | Mining use case |
| 78 | `ssurgo` | gNATSGO / SSURGO | detailed soil polygons + ~100 properties | vector/30 | static | US | public domain | `P` | `api` | `none` | 3 | Far richer than SoilGrids where available |
| 110 | `esdac` | ESDAC / LUCAS topsoil | EU soil properties, erosion, LUCAS points | vector/500 | multi-epoch | Europe | registration + use conditions | `R` | `portal` | `free-reg` | 4 | Registration + use conditions |
| 111 | `glim` | GLiM global lithology | lithological class | vector | static | global | CC-BY? | `P` | `http` | `none` | 4 | VERIFY license |
| 112 | `groundwater` | Global water table depth / WHYMAP | water table depth, aquifer type, recharge | 1000-vector | static | global | varies | `P/R` | `http` | `none` | 4 | Fan et al. + BGR WHYMAP; VERIFY |
| 113 | `gsocmap` | FAO GSOCmap | soil organic carbon stock | 1000 | static | global | CC-BY | `P` | `http` | `none` | 4 |  |
| 114 | `tailings` | Global tailings dam inventory | tailings facility points/attributes | vector | static | global | varies | `R` | `portal` | `none` | 4 | GRID-Arendal / GTDI; VERIFY |

## Vector/Human (25)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 14 | `geoboundaries` | geoBoundaries | admin boundaries ADM0-ADM4 | vector | multi-epoch | global | CC-BY 4.0 | `P` | `api` | `none` | 1 |  |
| 15 | `osm_overpass` | OpenStreetMap (Overpass/extracts) | all tagged features: roads, buildings, landuse, power, water, POI | vector | continuous | global | ODbL | `SA` | `api` | `none` | 1 | Richer tagging than Overture; share-alike |
| 16 | `overture` | Overture Maps | buildings, places, transportation, addresses, divisions, base, land/water | vector | monthly releases | global | CDLA-Permissive / ODbL mix | `P/SA` | `parquet` | `none` | 1 | Highest-value vector adapter; bbox-queryable GeoParquet; GERS ids. NOTE mixed license by theme - VERIFY per theme |
| 17 | `worldpop` | WorldPop | population count/density, age-sex structure | 100 | annual 2000- | global | CC-BY 4.0 | `P` | `http` | `none` | 1 |  |
| 37 | `cadastre_open` | Open national cadastre | parcel geometry, parcel id, sometimes area/use | vector | continuous | FR, ES, NL, DK, EE, CZ, AT, LT + | varies | `P/R` | `portal` | `varies` | 2 | FR (Etalab) and ES (Catastro) are genuinely open national cadastres - start here |
| 38 | `field_boundaries` | Global field boundary map (fiboa) / AI4Boundaries | agricultural field polygons | 10/vector | 2022-ish epoch | global / EU | CC-BY 4.0 | `P` | `parquet` | `none` | 2 | NOT cadastral - follows S2 pixel edges |
| 39 | `google_open_buildings` | Google Open Buildings v3 + 2.5D Temporal | building polygons, presence+HEIGHT over time | vector/4m | annual 2016- | Global South | CC-BY 4.0 | `P` | `http` | `none` | 2 | 2.5D temporal gives building height time series - unusual |
| 40 | `ookla` | Ookla Open Data | measured fixed+mobile download, upload, latency, tests | ~610m tiles | quarterly 2019- | global | CC-BY-NC-SA | `NC` | `parquet` | `none` | 2 | Only MEASURED connectivity; noncommercial |
| 41 | `opencellid` | OpenCelliD | cell tower locations, radio type, operator | vector | continuous | global | CC-BY-SA 4.0 | `SA` | `api` | `key` | 2 | Tower POINTS not coverage; free API key |
| 42 | `power_plants` | WRI Global Power Plant Database | plant location, capacity, fuel, generation | vector | 2021 | global | CC-BY 4.0 | `P` | `http` | `none` | 2 | Stale but widely used; check for successor |
| 79 | `cadastre_us` | US county/state parcel portals | parcel geometry, owner, assessed value, zoning | vector | varies | US, county-by-county | varies | `P/R/X` | `portal` | `varies` | 3 | Thousands of portals; Regrid unifies commercially |
| 80 | `census_grids` | Eurostat GISCO / US TIGER + ACS | statistical grids, census geometry + socioeconomic attrs | vector | varies | EU / US | open | `P` | `api` | `none` | 3 |  |
| 81 | `gridfinder` | gridfinder / OSM power | predicted MV grid, transmission lines, substations | vector/raster | 2020 | global | CC-BY / ODbL | `P/SA` | `http` | `none` | 3 |  |
| 82 | `grip4` | GRIP4 global roads | road network by type | vector | 2018 | global | CC-BY | `P` | `http` | `none` | 3 | OSM-derived, cleaned |
| 83 | `gsma_mce` | GSMA Mobile Coverage Explorer | modelled 2G/3G/4G coverage polygons/raster | ~260m | annual | global | restricted | `R` | `portal` | `varies` | 3 | Tower-buffer approximation (12km GSM / 4km 3G-4G) |
| 84 | `hrsl` | Meta/CIESIN HRSL | high-res population | 30 | multi-epoch | most countries | CC-BY | `P` | `http` | `none` | 3 |  |
| 85 | `ms_buildings` | Microsoft Global Building Footprints | building footprints | vector | multi-epoch | global | ODbL | `SA` | `parquet` | `none` | 3 | Largely folded into Overture |
| 86 | `natural_earth` | Natural Earth | admin, coastline, physical features | vector | static | global | public domain | `P` | `http` | `none` | 3 | Coarse but zero-friction |
| 87 | `ogim` | OGIM oil & gas infrastructure | wells, compressors, processing, pipelines | vector | multi-epoch | global | CC-BY | `P` | `http` | `none` | 3 | Heavy-industry use case |
| 88 | `wdpa` | WDPA / Natura 2000 / KBA | protected area polygons, IUCN category, designation | vector | monthly | global | restricted (no commercial redistribution) | `R` | `api` | `free-reg` | 3 | License constrains redistribution - tier carefully |
| 115 | `gadm` | GADM | admin boundaries | vector | static | global | academic-only | `R` | `http` | `none` | 4 | License blocks commercial use - tier accordingly |
| 116 | `landmark` | LandMark indigenous & community lands | community land polygons, tenure status | vector | static | global (partial) | CC-BY | `P` | `http` | `none` | 4 | Closest free proxy for non-formal tenure |
| 117 | `mlab` | M-Lab / RIPE Atlas | measured throughput, latency, traceroute | point | continuous | global | CC-BY / open | `P` | `api` | `none` | 4 |  |
| 118 | `ourairports` | OurAirports / World Port Index | airports, runways, ports | vector | continuous | global | public domain | `P` | `http` | `none` | 4 |  |
| 119 | `viirs_nightfire` | VIIRS Nightfire / flaring | gas flare detections, radiant heat | 750 | nightly, 2012- | global | open | `P` | `http` | `none` | 4 | Industrial activity proxy |

## Atmosphere/AQ (7)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 18 | `sentinel5p` | Sentinel-5P TROPOMI | NO2, SO2, CO, CH4, O3, HCHO, aerosol index/height | 3500-7000 | daily, 2018- | global | Copernicus open | `P` | `stac` | `none` | 2 | Industrial emissions signal - mining/heavy industry use case |
| 43 | `cams` | CAMS reanalysis (EAC4) / forecasts | PM2.5, PM10, AOD, O3, NO2 | 40000 | 3-hourly, 2003- | global | Copernicus open | `P` | `cds` | `key` | 3 |  |
| 44 | `emit` | EMIT / methane point sources | imaging spectroscopy, CH4 plumes, mineralogy | 60 | 2022-, targeted | global land (partial) | NASA open | `P` | `stac` | `free-reg` | 3 | TRUE HYPERSPECTRAL (285 bands) - the only free hyperspectral at scale |
| 45 | `maiac_aod` | MODIS MAIAC MCD19A2 | aerosol optical depth | 1000 | daily, 2000- | global | NASA open | `P` | `stac` | `none` | 3 |  |
| 89 | `acag_pm25` | ACAG global PM2.5 | annual mean PM2.5 | 1000 | annual, 1998- | global | CC-BY-NC? | `NC` | `http` | `none` | 4 | VERIFY license |
| 90 | `enmap_prisma` | EnMAP / PRISMA / DESIS | hyperspectral radiance/reflectance | 30 | targeted tasking | sparse global | free w/ registration | `R` | `portal` | `free-reg` | 4 | Free with registration but sparse coverage - the realistic answer to 'hyperspectral' |
| 91 | `openaq` | OpenAQ | ground station air quality measurements | point | continuous | global (uneven) | CC-BY | `P` | `api` | `key` | 4 |  |

## Carbon/Biomass (4)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 19 | `cci_biomass` | ESA CCI Biomass | above-ground biomass + uncertainty | 100 | annual 2010- | global | CC-BY | `P` | `http` | `none` | 2 |  |
| 47 | `gedi_l4b` | GEDI L4A/L4B | AGB density, gridded mean biomass | 25/1000 | 2019- | 51N-51S | NASA open | `P` | `http` | `free-reg` | 3 |  |
| 93 | `odiac` | ODIAC / EDGAR emissions | fossil fuel CO2, sector emissions | 1000-11000 | monthly/annual | global | CC-BY / open | `P` | `http` | `none` | 4 |  |
| 94 | `spawn_biomass` | Spawn/Gibbs global biomass carbon | above+below-ground carbon density | 300 | 2010 | global | CC-BY | `P` | `http` | `none` | 4 |  |

## Hydrology (7)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 26 | `hydrosheds` | HydroSHEDS / RIVERS / BASINS / LAKES | drainage network, basins, lakes, flow acc | 15-500/vector | static | global | CC-BY 4.0* | `P` | `http` | `none` | 2 | *verify: some HydroATLAS attrs are NC |
| 59 | `glofas` | GloFAS / JRC flood hazard | flood hazard depth by return period, streamflow | 1000/100 | static + forecast | global | Copernicus open | `P` | `cds` | `key` | 3 |  |
| 60 | `hydroatlas` | BasinATLAS / RiverATLAS | ~280 hydro-environmental attributes per basin/reach | vector | static | global | CC-BY-NC? | `NC` | `http` | `none` | 3 | VERIFY license - huge attribute set if usable |
| 61 | `smap` | SMAP soil moisture | surface + root-zone soil moisture | 9000 | 2-3d, 2015- | global | NASA open | `P` | `stac` | `free-reg` | 3 |  |
| 102 | `grand_goodd` | GRanD / GOODD dams | dam points, reservoir polygons, capacity | vector | static | global | CC-BY-NC / CC-BY | `NC/P` | `http` | `none` | 4 | VERIFY per-dataset |
| 103 | `grwl` | Global River Widths from Landsat | river centerlines + width | 30/vector | static | global | CC-BY | `P` | `http` | `none` | 4 |  |
| 104 | `modis_snow` | MODIS/VIIRS snow cover | NDSI snow cover, fractional | 500 | daily, 2000- | global | NASA open | `P` | `stac` | `free-reg` | 4 |  |

## Biodiversity (2)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 46 | `gbif` | GBIF occurrences | species occurrence records | point | continuous | global | CC0/CC-BY mix | `P` | `api` | `none` | 3 | AlphaEarth decode target; per-record license varies |
| 92 | `iucn_ranges` | IUCN Red List range maps | species range polygons, threat status | vector | annual | global | restricted | `R` | `portal` | `free-reg` | 4 | Non-commercial terms |

# Batch 2 — Atypical physics and modality: geophysics, deformation, marine, deep time, ground-level, activity, industry

## Geodesy/Deformation (8)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 120 | `egms` | Copernicus EGMS (European Ground Motion Service) | vertical + E-W displacement TIME SERIES, mean velocity, acceleration, coherence | 100m (L3) | 2015-, annual updates | EU + UK | Copernicus open | `P` | `portal` | `free-reg` | 1 | First continental open InSAR deformation service. ~3mm/yr detection. MINING SUBSIDENCE, sinkholes, landslides. Measures MOTION not reflectance |
| 126 | `eq_catalog` | USGS ComCat / ISC / GCMT | earthquake hypocentres, magnitude, moment tensors | point | 1900- (continuous) | global | public domain | `P` | `api` | `none` | 2 | Real event history for a box |
| 152 | `active_faults` | GEM Global Active Faults | fault traces, slip rate, type | vector | static | global | CC-BY | `P` | `http` | `none` | 3 |  |
| 153 | `gnss_vel` | Nevada Geodetic Lab / EarthScope GNSS | station position time series, velocity vectors | point | 1990s- | global | open | `P` | `http` | `none` | 3 | mm-precision ground truth for deformation |
| 154 | `licsar` | COMET LiCSAR / ARIA | interferograms, coherence, displacement | ~100m | 2015- | global (tectonic belts) | open | `P` | `http` | `none` | 3 | Global complement to EGMS |
| 155 | `seismic_hazard` | GEM Global Seismic Hazard / Risk Map | PGA by return period, hazard curves | ~1km | static | global | CC-BY-NC-SA? | `NC` | `http` | `none` | 3 | VERIFY license tier |
| 190 | `landslides` | NASA COOLR / national inventories | landslide event points + polygons | point/vector | 2007- | global | open | `P` | `http` | `none` | 4 |  |
| 191 | `volcanoes` | Smithsonian GVP | volcano locations, eruption history, VEI | point | Holocene- | global | CC-BY-NC? | `NC` | `api` | `none` | 4 | VERIFY |

## Industry/Regulatory (6)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 121 | `gem_trackers` | Global Energy Monitor (25 trackers) | coal mines, coal plants, iron+steel, iron ore mines, cement, oil+gas extraction, pipelines, LNG, solar, wind, hydro, geothermal, nuclear, bioenergy, terminals, OWNERSHIP | point/vector | continuous, 200+ countries | global | CC BY 4.0 | `P` | `portal` | `free-reg` | 1 | Asset-level heavy-industry registry. Directly serves the mining + heavy industry use case. Download via form |
| 134 | `climate_trace` | Climate TRACE | asset-level GHG emissions by facility + sector | point/vector | annual 2015- | global | CC-BY | `P` | `api` | `none` | 2 | Emissions attributed to individual facilities |
| 135 | `epa_frs` | US EPA FRS / TRI / ECHO / NPDES / Superfund | regulated facilities, toxic releases, compliance, permits, contaminated sites | point/vector | continuous | US | public domain | `P` | `api` | `none` | 2 | Deepest regulatory record anywhere |
| 136 | `eprtr` | EU Industrial Emissions Portal (E-PRTR) | facility pollutant releases to air/water/soil, waste transfers | point | annual 2007- | EU | open | `P` | `api` | `none` | 2 | Per-facility regulated pollutant releases |
| 167 | `concessions` | Mining / logging / oil concessions (GFW, national registries) | concession + licence polygons, holder, commodity | vector | varies | partial global | varies | `P/R` | `portal` | `varies` | 3 | Legal right-to-extract - institutional, not inferable |
| 204 | `tailings2` | Global Tailings Portal / GRID-Arendal | tailings facility attributes, volume, hazard class | point | 2019- | global (disclosed subset) | varies | `R` | `portal` | `none` | 4 |  |

## Marine/Bathymetry (12)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 122 | `cmems` | Copernicus Marine (CMEMS) | SST, SSH, currents, salinity, waves, chlorophyll, oxygen, pH, mixed-layer depth | 4-25km | hourly-daily, 1993- | global ocean | Copernicus open | `P` | `api` | `free-reg` | 1 | Enormous free catalogue - ocean analogue of ERA5 |
| 123 | `gebco` | GEBCO 2024 / SRTM15+ | bathymetry + topography, seafloor depth | 15 arc-sec | biennial | global ocean | public domain | `P` | `http` | `none` | 1 | THE ocean-box DEM equivalent. Refutes 'ocean returns nothing' |
| 137 | `gfw` | Global Fishing Watch | AIS fishing effort, vessel presence, transshipment, port visits | ~1km / vector | daily, 2012- | global ocean | CC-BY-NC-SA? | `NC` | `api` | `key` | 2 | Human activity at sea. VERIFY license |
| 138 | `mur_sst` | MUR SST / OSTIA | gap-free analysed sea surface temperature | 1-5km | daily, 2002- | global ocean | open | `P` | `stac` | `none` | 2 |  |
| 139 | `ocean_color` | Sentinel-3 OLCI / MODIS / PACE ocean colour | chlorophyll-a, Kd490, suspended matter, PFTs | 300m-4km | daily | global ocean | open | `P` | `stac` | `free-reg` | 2 | PACE adds hyperspectral ocean colour |
| 168 | `ais_density` | EMODnet Human Activities vessel density | shipping density by vessel type | 1km | monthly, 2017- | EU seas | CC-BY | `P` | `http` | `none` | 3 |  |
| 169 | `argo_woa` | Argo floats / World Ocean Atlas / WOD | T/S/O2 depth profiles, climatology | point/1deg | 2000- / climatology | global ocean | open | `P` | `api` | `none` | 3 | Vertical structure - a depth axis, not a surface |
| 170 | `emodnet_bathy` | EMODnet Bathymetry / BlueTopo | high-res regional bathymetry | ~100m / varies | multi-epoch | EU seas / US | CC-BY / public domain | `P` | `http` | `none` | 3 |  |
| 171 | `sea_ice` | NSIDC sea ice concentration/extent/age/motion | ice concentration, age, drift | 3-25km | daily, 1978- | polar | open | `P` | `http` | `free-reg` | 3 |  |
| 205 | `offshore_infra` | Offshore platforms / wind farms / cables | platform + turbine points, cable routes | vector | varies | global | varies | `P/R` | `http` | `none` | 4 | Submarine cable data often restricted |
| 206 | `seabed_habitat` | EMODnet Seabed Habitats / substrate | habitat class, substrate type | vector | multi-epoch | EU seas | CC-BY | `P` | `http` | `none` | 4 |  |
| 207 | `tides` | FES2022 / TPXO | tidal constituents, amplitude, phase | 1/16 deg | model | global ocean | academic open | `P/R` | `http` | `none` | 4 |  |

## Deep time/Archival (9)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 124 | `declass_corona` | USGS Declass 1 (CORONA/ARGON/LANYARD) | panchromatic film imagery | 1.8-2.7m (KH-4A/4B) | 1960-1972 | near-global | public domain | `P` | `portal` | `free-reg` | 2 | Sub-3m imagery from the 1960s, free. Extends change detection 40yr before Landsat MSS |
| 125 | `declass_hexagon` | USGS Declass 2 + 3 (KH-7 GAMBIT, KH-9 HEXAGON) | panchromatic film, stereo mapping camera | 0.6-1.2m (pano), 6-9m (mapping) | 1963-1984 | near-global (not inner Greenland/Antarctica/AU) | public domain | `P` | `portal` | `free-reg` | 2 | ~630k KH-9 images. Stereo pairs -> historical DEMs. Unscanned frames may need ordering |
| 149 | `hist_aerial` | Historical aerial photography archives | panchromatic aerial frames | 0.3-2m | 1920s-1990s | US, EU, many | varies | `P/R` | `portal` | `varies` | 3 | USGS EarthExplorer aerial, national archives, IGN France remonterletemps |
| 150 | `hist_topo` | Historical topographic maps | scanned georeferenced map sheets | map scale | 1880s- | US, EU, Soviet global | public domain / varies | `P` | `portal` | `none` | 3 | USGS topoView; Soviet military topo covers much of the world |
| 151 | `hyde_luh` | HYDE 3.3 / LUH2 / Anthromes | cropland, grazing, population, land use | 5-10 arc-min | 10,000 BCE - 2100 | global | CC-BY | `P` | `http` | `none` | 3 | Land use back 12,000 years. The deepest time axis available |
| 186 | `heritage` | UNESCO WHS / Pleiades / EAMENA / national registers | heritage site points+polygons, period, condition | vector | antiquity- | global | varies | `P/R` | `api` | `none` | 4 |  |
| 187 | `itrdb` | ITRDB tree rings / SISAL speleothems | ring-width + isotope chronologies | point | centuries-millennia | global (sparse) | public domain | `P` | `http` | `none` | 4 | Annual-resolution local climate archive |
| 188 | `neotoma` | Neotoma Paleoecology Database | pollen, macrofossil, faunal records by site | point | Quaternary | global (sparse) | CC-BY | `P` | `api` | `none` | 4 | What grew here thousands of years ago |
| 189 | `paleoclim` | ERA-20C / 20CR / HadCRUT / PMIP | historical + paleo climate reconstruction | 1-2 deg | 1836- / paleo epochs | global | open | `P` | `cds` | `key` | 4 |  |

## Geophysics (potential fields) (8)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 127 | `grav_anomaly` | EGM2008 / XGM2019e / WGM2012 | free-air + Bouguer + isostatic gravity anomaly, geoid | ~2-10km | static | global | public domain / CC-BY | `P` | `http` | `none` | 2 | Gravity reveals density structure - no optical analogue at all |
| 128 | `mag_anomaly` | EMAG2 v3 / WDMAM v2 | crustal magnetic anomaly | 2 arc-min | static | global | public domain | `P` | `http` | `none` | 2 | Lithology + structure; mining staple |
| 129 | `radiometrics` | Airborne gamma-ray spectrometry (USGS NURE/EarthMRI, GA, GSC) | K %, equivalent U ppm, equivalent Th ppm, dose rate | 100m-5km line spacing | 1970s- + new surveys | US, CA, AU, parts others | public domain | `P` | `http` | `none` | 2 | GAMMA-ray spectral - different band region entirely. Top 0-50cm geochemistry. Mining/critical minerals |
| 156 | `crust_model` | CRUST1.0 / LITHO1.0 / GlobSed | crustal thickness, Moho depth, sediment thickness, Vp/Vs | 1deg / 5min | static | global | academic open | `P/R` | `http` | `none` | 3 | Basin depth matters for resources |
| 157 | `heat_flow` | IHFC Global Heat Flow Database | surface heat flow, gradient, conductivity | point | static | global (sparse) | CC-BY | `P` | `http` | `none` | 3 | Geothermal siting |
| 158 | `natl_geophys` | National geophysical compilations (GA, NRCan, USGS, BGS) | aeromagnetic, gravity, radiometric grids + flight lines | 50-400m | 1950s- | per-country | varies | `P/R` | `portal` | `varies` | 3 | Australia + Canada are exceptionally open. Highest-res geophysics available free |
| 192 | `geomag_field` | IGRF-14 / WMM | main field, declination, inclination, intensity | model | epoch model | global | public domain | `P` | `api` | `none` | 4 | Computed from model, not gridded data |
| 193 | `tomography` | IRIS EMC / SubMachine | 3D seismic velocity models | variable | static | global | open | `P` | `api` | `none` | 4 | Deep structure; research use |

## Ground-level imagery (4)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 130 | `mapillary` | Mapillary | street-level photos, detected objects, traffic signs | photo | 2014-, continuous | global (road-biased) | CC-BY-SA | `SA` | `api` | `key` | 2 | GROUND-LEVEL view - orthogonal to all nadir imagery. Object detections are a free vector layer |
| 159 | `kartaview` | KartaView (OpenStreetCam) | street-level photos, detections | photo | continuous | global | CC-BY-SA | `SA` | `api` | `none` | 3 |  |
| 160 | `openaerialmap` | OpenAerialMap | crowd-sourced drone + aerial imagery | 0.02-1m | continuous, event-driven | sparse global | CC-BY / varies | `P` | `api` | `none` | 3 | Often the ONLY sub-metre imagery in disaster/Global South areas |
| 194 | `geotagged_photos` | Wikimedia Commons / Flickr geotagged | photographs with coordinates | photo | continuous | global | CC mix | `P/SA` | `api` | `key` | 4 | Human-salience signal; AEF already uses geocoded Wikipedia |

## In-situ ecology/agronomy (11)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 131 | `fia_nfi` | USDA FIA / national forest inventories | plot-level species, DBH, height, biomass, growth | plot | continuous | US + many | public domain / varies | `P/R` | `api` | `none` | 2 | GROUND-MEASURED forest structure. Fuzzed plot coords in US |
| 132 | `gaez` | FAO GAEZ v4 | crop suitability, attainable yield, agro-climatic zones, constraints | ~10km | climatology + scenarios | global | CC-BY | `P` | `http` | `none` | 2 | Crop-by-crop land suitability - the agriculture use case answered directly |
| 133 | `spam_earthstat` | MapSPAM / EarthStat | crop area + yield + production for 40-175 crops | 10km | multi-epoch | global | CC-BY | `P` | `http` | `none` | 2 | Per-crop distribution, not just 'cropland' |
| 164 | `fluxnet` | FLUXNET / AmeriFlux / ICOS | eddy-covariance CO2, H2O, energy flux time series | tower | 1990s- | global (sparse) | CC-BY | `P` | `http` | `free-reg` | 3 | Ground truth for ET/GPP products |
| 165 | `glw` | FAO Gridded Livestock of the World | cattle, sheep, goat, pig, poultry density | 10km | multi-epoch | global | CC-BY | `P` | `http` | `none` | 3 |  |
| 166 | `irrigation` | GMIA / MIRCA / GRIPC | irrigated area fraction, irrigation type, crop calendars | 5-10 arc-min | multi-epoch | global | CC-BY / varies | `P` | `http` | `none` | 3 |  |
| 199 | `gfbi_splot` | GFBI / sPlot / TRY | forest + vegetation plot composition, plant traits | plot | compiled | global (sparse) | restricted (data agreement) | `R` | `portal` | `free-reg` | 4 | Data-sharing agreements required |
| 200 | `nutrients` | EarthStat / Ludemann fertiliser, PEST-CHEMGRIDS | N+P application rate by crop, pesticide application | 10km-5 arc-min | multi-epoch | global | CC-BY | `P` | `http` | `none` | 4 | Agronomic inputs - management, not biophysics |
| 201 | `phenology` | USA-NPN / PEP725 | observed phenophase dates by species+site | point | 1950s- | US / EU | CC-BY | `P` | `api` | `none` | 4 | Human-observed ground phenology vs satellite-derived |
| 202 | `soil_biodiversity` | SoilBON / GlobalFungi / earthworm + nematode atlases | soil taxa occurrence, diversity metrics, eDNA | point/1km | compiled | global (sparse) | CC-BY | `P` | `http` | `none` | 4 | WHAT LIVES IN THE SOIL - genuinely unavailable from any sensor |
| 203 | `yield_hist` | GDHY global historical yields | annual crop yield for major crops | ~55km | annual 1981-2016 | global | CC-BY | `P` | `http` | `none` | 4 |  |

## Non-optical EO (8)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 140 | `ecostress` | ECOSTRESS | land surface temperature, ET, ESI | 70m | 2018-, irregular | global (ISS orbit) | NASA open | `P` | `stac` | `free-reg` | 2 | 70m thermal - far finer than any other free LST |
| 172 | `passive_mw` | AMSR2 / SMOS / SSMIS | soil moisture, snow, SST, vegetation optical depth | 10-25km | daily | global | open | `P` | `http` | `free-reg` | 3 | All-weather, all-season, very coarse |
| 173 | `water_level` | DAHITI / Hydroweb / G-REALM | lake + river + reservoir water level time series from altimetry | per-waterbody | 1992- | global (large bodies) | CC-BY / open | `P` | `api` | `free-reg` | 3 | Satellite altimetry gives water LEVEL where gauges are absent |
| 208 | `ascat` | ASCAT scatterometer | backscatter, soil moisture, wind | 12-25km | daily, 2007- | global | open | `P` | `http` | `free-reg` | 4 |  |
| 209 | `cygnss` | CYGNSS (GNSS reflectometry) | ocean wind, soil moisture, flood inundation | ~25km | sub-daily | 38N-38S | NASA open | `P` | `http` | `free-reg` | 4 | Uses reflected GPS signals - an unusual physics |
| 210 | `lightning` | WWLLN / GOES-GLM / LIS-OTD climatology | lightning stroke locations, flash rate climatology | point/0.1deg | continuous / climatology | global | varies | `P/R` | `api` | `key` | 4 |  |
| 211 | `sounders` | AIRS / IASI / CrIS / GNSS-RO | vertical temperature + humidity profiles | 13-50km | daily | global | open | `P` | `http` | `free-reg` | 4 | A vertical atmospheric column over the box |
| 212 | `space_weather` | Ionosphere TEC / geomagnetic indices / cosmic ray | TEC maps, Kp/Dst, neutron monitor flux | 2.5deg | continuous | global | open | `P` | `api` | `none` | 4 | Relevant to GNSS accuracy and radiation exposure |

## Socioeconomic (11)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 141 | `gridded_gdp` | Kummu / Chen gridded GDP + HDI | GDP PPP per capita, HDI | 5 arc-min-1km | 1990- | global | CC-BY | `P` | `http` | `none` | 2 | Economic output as a raster |
| 174 | `conflict` | UCDP GED / ACLED / GDELT | geolocated conflict + protest events, fatalities | point | 1989- / 1997- | global | CC-BY / restricted | `P/R` | `api` | `key` | 3 | UCDP is CC-BY; ACLED has terms |
| 175 | `dhs_clusters` | DHS / LSMS / MICS survey clusters | health, wealth, agriculture indicators at displaced cluster points | point | varies | LMICs | restricted (data agreement) | `R` | `portal` | `free-reg` | 3 | Registration + data agreement; coordinates deliberately jittered |
| 176 | `giga_schools` | GIGA school mapping / healthsites.io | school + health facility locations, connectivity status | point | continuous | global (partial) | CC-BY / ODbL | `P/SA` | `api` | `none` | 3 | Service access points |
| 177 | `land_registry` | HM Land Registry Price Paid / NL / DK transactions | property transaction price, date, type | point/address | 1995- | UK, NL, DK, others | open gov | `P` | `api` | `none` | 3 | Actual market values - institutional and unavailable by inference |
| 178 | `meta_rwi` | Meta Relative Wealth Index | relative wealth index by 2.4km tile | 2.4km | 2021 | LMICs | CC-BY | `P` | `http` | `none` | 3 |  |
| 179 | `openaddresses` | OpenAddresses | address points with coordinates | point | continuous | global (patchy) | varies open | `P/SA` | `http` | `none` | 3 | Complements Overture addresses |
| 213 | `electoral` | Electoral + service districts | precincts, school/police/fire districts, results | vector | per-cycle | per-jurisdiction | varies | `P` | `portal` | `varies` | 4 |  |
| 214 | `food_security` | FEWS NET / IPC / WFP VAM prices | IPC phase classification, market food prices | admin/point | continuous | food-insecure regions | open | `P` | `api` | `none` | 4 |  |
| 215 | `gdl_shdi` | Global Data Lab subnational HDI | subnational HDI, education, income, health | admin unit | annual 1990- | global | CC-BY-NC? | `NC` | `api` | `none` | 4 | VERIFY |
| 216 | `native_land` | Native Land Digital / treaty boundaries | indigenous territory, treaty, language polygons | vector | static | N.America + global | CC-BY-NC? | `NC` | `api` | `none` | 4 | VERIFY; complements LandMark |

## Spectrum/EM (3)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 142 | `fcc_uls` | FCC ULS + broadband maps | licensed transmitter locations, frequency, power, licensee; broadband availability by address | point/address | continuous | US | public domain | `P` | `api` | `none` | 2 | AUTHORITATIVE transmitter registry - strictly better than OpenCelliD in the US |
| 180 | `spectrum_intl` | Ofcom / ITU / national spectrum registries | licensed sites, frequencies, coverage predictions | point | continuous | per-country | varies | `P/R` | `portal` | `varies` | 3 | Authoritative where published |
| 217 | `radio_quiet` | Radio quiet zones / observatory protection areas | restriction polygons | vector | static | sparse global | public | `P` | `portal` | `none` | 4 |  |

## Toponymy/Language (2)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 143 | `geonames` | GeoNames / NGA GNS | place names, feature class, population, alternate names | point | continuous | global | CC-BY / public domain | `P` | `api` | `none` | 2 | What this place is CALLED, in every language |
| 218 | `glottolog` | Glottolog / WALS | language locations, families, structural features | point | static | global | CC-BY | `P` | `api` | `none` | 4 | Which languages are spoken here |

## Activity streams (5)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 144 | `gtfs` | Mobility Database / transit.land (GTFS) | transit stops, routes, schedules, frequencies | vector | continuous | global (thousands of agencies) | varies open | `P/R` | `api` | `none` | 3 | Service accessibility, not physical surface |
| 145 | `opensky` | OpenSky Network | ADS-B aircraft tracks, altitude, type | point/track | 2013-, continuous | global | research-open | `R` | `api` | `free-reg` | 3 | Overflight activity; airport operations |
| 181 | `mobility` | Meta Data for Good (movement, social connectedness) | movement between tiles, social connectedness index | tile | 2020- | global | CC-BY / restricted | `P/R` | `portal` | `free-reg` | 4 | Availability has varied over time - VERIFY current status |
| 182 | `strava_metro` | Strava Metro | aggregated cycling/running volumes by segment | vector | continuous | global | restricted | `R` | `portal` | `free-reg` | 4 | Access limited to qualifying organisations |
| 183 | `traffic_counts` | National/state traffic counts (AADT) | annual average daily traffic by segment | vector | annual | per-jurisdiction | varies | `P` | `portal` | `varies` | 4 |  |

## Cryosphere (5)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 146 | `itslive` | ITS_LIVE | ice + glacier surface velocity time series | 120-240m | 1985- | global ice | open | `P` | `stac` | `none` | 3 | Motion again, not reflectance |
| 147 | `permafrost` | Obu et al. permafrost zonation / ground temperature | permafrost probability, mean annual ground temp, ALT | 1km | 2000-2016 | N hemisphere | CC-BY | `P` | `http` | `none` | 3 | Critical for northern infrastructure siting |
| 148 | `rgi_glims` | Randolph Glacier Inventory / GLIMS | glacier outlines, area, attributes | vector | multi-epoch | global | CC-BY | `P` | `http` | `none` | 3 |  |
| 184 | `glacier_thick` | Farinotti consensus ice thickness | glacier ice thickness, bed topography | 25-50m | static | global glaciers | CC-BY | `P` | `http` | `none` | 4 |  |
| 185 | `snow_swe` | ERA5-Land / GlobSnow / SNODAS SWE | snow water equivalent, depth, cover duration | 1-25km | daily | global / N hemi / US | open | `P` | `http` | `none` | 4 |  |

## Health/Exposure (7)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 161 | `flood_zones` | FEMA NFHL / national flood maps | regulatory flood zones, base flood elevation | vector | continuous | US + others | public domain | `P` | `api` | `none` | 3 | REGULATORY flood risk - a legal fact, not a physical one |
| 162 | `malaria_atlas` | Malaria Atlas Project | Pf/Pv prevalence, incidence, intervention coverage, vector occurrence | 5km | annual 2000- | endemic global | CC-BY | `P` | `api` | `none` | 3 | Model-grade disease rasters, freely gridded |
| 163 | `noise_maps` | EU Environmental Noise Directive strategic noise maps | Lden/Lnight contours for road, rail, air, industry | vector | 5y rounds | EU agglomerations | open | `P` | `portal` | `varies` | 3 | ACOUSTIC exposure - a modality absent from everything else |
| 195 | `espen_jmp` | ESPEN NTDs / WHO-UNICEF JMP | NTD prevalence, water+sanitation access | district/point | annual | global | open | `P` | `api` | `none` | 4 |  |
| 196 | `light_pollution` | Falchi World Atlas of Artificial Night Sky Brightness | zenith sky brightness, Bortle class | ~1km | 2016 + updates | global | CC-BY-NC? | `NC` | `http` | `none` | 4 | Distinct from nighttime-lights radiance - this is sky quality. VERIFY |
| 197 | `radon` | National radon potential maps | indoor radon potential class, measured concentrations | vector/grid | static | US, EU, many | varies | `P/R` | `portal` | `varies` | 4 | Links to the gamma-ray/geology layers |
| 198 | `wildfire_hazard` | CAL FIRE FHSZ / Pyrologix / national fire risk | fire hazard severity zones, burn probability | vector/30m | multi-epoch | US + others | public domain | `P` | `portal` | `none` | 4 |  |

# Batch 3 — Record-level geolocated data: geology maps, sequences, health, contamination, economics, knowledge

## Contamination/Toxics (16)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 219 | `nwis` | USGS NWIS | streamflow, groundwater levels, water chemistry by site | point | 1890s- | US | public domain | `P` | `api` | `none` | 1 | Also the streamflow gauge module |
| 220 | `pfas_ucmr` | EPA UCMR5 / PFAS Analytic Tools | MEASURED PFAS concentrations in public water systems + known sources | water system / point | 2023-2025 | US | public domain | `P` | `api` | `none` | 1 | Actual measured PFAS - UCMR5 is near-census of larger US systems |
| 221 | `wqp` | Water Quality Portal (USGS/EPA) | station-level measurements of thousands of analytes incl. metals, nutrients, PFAS | point | 1900s- | US | public domain | `P` | `api` | `none` | 1 | Tens of millions of results; the deepest water-chemistry archive anywhere |
| 228 | `gemstat_waterbase` | UNEP GEMStat / EEA Waterbase | river, lake, groundwater quality measurements | point | 1960s- | global / Europe | open / CC-BY | `P` | `api` | `free-reg` | 2 |  |
| 229 | `pfas_europe` | Forever Pollution Project / ECHA / national PFAS registers | PFAS contamination + suspected-site map | point | 2023- | Europe | varies | `P/R` | `portal` | `none` | 2 | VERIFY reuse terms - journalism consortium compilation |
| 230 | `pfas_sites` | EWG PFAS map / DoD installations / state programs (MI, NJ, CA GAMA) | suspected + confirmed PFAS contamination sites | point | continuous | US | varies | `P/R` | `portal` | `varies` | 2 | Site inventories; licence varies by publisher |
| 231 | `pfas_usgs` | USGS PFAS in groundwater + tapwater studies | PFAS detections and concentrations at sampled wells/taps | point | 2019- | US | public domain | `P` | `api` | `none` | 2 | Probability-of-detection models also published |
| 258 | `deposition` | NADP / EMEP / EURDEP | N + S + mercury deposition, radiological monitoring | point/grid | 1978- | US / Europe | open | `P` | `api` | `none` | 3 |  |
| 259 | `grdc_gauges` | GRDC / national streamflow archives | daily + monthly discharge time series | point | 1800s- | global | restricted (GRDC terms) | `R` | `portal` | `free-reg` | 3 |  |
| 260 | `sdwis` | EPA SDWIS drinking water violations | violation type, contaminant, system service area | water system | continuous | US | public domain | `P` | `api` | `none` | 3 | Regulatory non-compliance, not concentration |
| 297 | `landfills_waste` | EPA LMOP / EU waste facilities | landfill + waste facility location, capacity, gas capture | point | continuous | US / EU | public domain / open | `P` | `api` | `none` | 4 |  |
| 298 | `microplastics` | NOAA NCEI marine microplastics | microplastic concentration by sample | point | 1972- | global ocean | public domain | `P` | `api` | `none` | 4 |  |
| 299 | `mussel_watch` | NOAA Mussel Watch / biota contaminants | contaminant concentrations in sentinel organisms | point | 1986- | US coasts | public domain | `P` | `http` | `none` | 4 |  |
| 300 | `oil_spills` | NOAA IncidentNews / spill databases | spill location, volume, substance, date | point | 1957- | global | public domain | `P` | `api` | `none` | 4 |  |
| 301 | `pesticide_use` | USGS pesticide national synthesis | estimated pesticide application by compound | county | 1992- | US | public domain | `P` | `http` | `none` | 4 |  |
| 302 | `radnet_fallout` | EPA RadNet / Cs-137 fallout maps | ambient radiation, radionuclide deposition | point/grid | 1950s- | US / global | public domain | `P` | `api` | `none` | 4 |  |

## Economic/Demographic (14)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 222 | `census_micro` | National census + IPUMS International | population, housing, employment, education at fine geography | block/tract/grid | decennial + annual | global (100+ countries) | open / IPUMS terms | `P/R` | `api` | `free-reg` | 1 | US block-level is the finest demographic data in existence |
| 232 | `hmda` | HMDA mortgage lending | loan applications, approvals, denials, amounts, demographics | census tract | annual 1990- | US | public domain | `P` | `api` | `none` | 2 | Geolocated credit allocation - a rare direct economic-behaviour record |
| 233 | `housing_registry` | National building registries (NL BAG, DK BBR, FR, AT) | building age, use, floor area, dwelling count per address | address/building | continuous | several countries | open gov | `P` | `api` | `none` | 2 | Per-building attributes, authoritative; NL BAG is the exemplar |
| 234 | `lodes` | US LEHD LODES | jobs by block, home-work ORIGIN-DESTINATION flows, industry, earnings | census block | annual 2002- | US | public domain | `P` | `http` | `none` | 2 | Commuting flows at block level - extraordinary granularity |
| 261 | `ag_census` | USDA Census of Agriculture / FAO / Eurostat FSS | farms, area, crops, livestock, operator demographics | county/NUTS3 | 5y | global | public domain / open | `P` | `api` | `none` | 3 |  |
| 262 | `aiddata` | AidData geocoded aid / World Bank / IATI | development project locations, sector, commitment amounts | point/admin | 1950s- | global | CC-BY | `P` | `http` | `none` | 3 | Geocoded development finance incl. Chinese overseas lending |
| 263 | `business_estab` | Overture places / OSM / OpenCorporates / GLEIF | business locations, category, company registry + LEI addresses | point | continuous | global | varies | `P/SA/R` | `api` | `none` | 3 | Firm-level geography; the good registries are mostly paid |
| 264 | `epc` | EU Energy Performance Certificates | building energy rating, consumption, heating type per address | address | continuous | EU member states | varies | `P/R` | `portal` | `varies` | 3 | Per-address energy data; availability varies sharply by country |
| 265 | `gpwv4` | GPW v4 / LandScan | population count + density | 30 arc-sec | 5y epochs | global | CC-BY / restricted | `P/R` | `http` | `none` | 3 | Complements WorldPop/GHS-POP with different methodology |
| 266 | `land_matrix` | Land Matrix | large-scale land acquisition deals, investor, crop, area, status | point/polygon | 2000- | global (LMIC) | CC-BY | `P` | `api` | `none` | 3 | Geolocated land deals - directly relevant to tenure and agriculture |
| 267 | `migration` | UNHCR / IDMC / IOM DTM | refugee + IDP counts, camp + displacement site locations | point/admin | continuous | global | open | `P` | `api` | `none` | 3 |  |
| 268 | `nfip` | FEMA NFIP claims + policies | flood insurance claims, payouts, policy counts | census tract/ZIP | 1978- | US | public domain | `P` | `api` | `none` | 3 | Realized flood LOSSES - ground truth for hazard models |
| 303 | `cap_subsidies` | EU CAP payments / USDA farm payments | subsidy amounts by beneficiary + locality | beneficiary/locality | annual | EU / US | varies open | `P/R` | `portal` | `varies` | 4 | Transparency registers; granularity varies |
| 304 | `crop_insurance` | USDA RMA cause-of-loss | indemnities by cause (drought, hail, flood) and crop | county | 1989- | US | public domain | `P` | `http` | `none` | 4 | Realized agricultural losses by peril |

## Geology (maps) (7)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 223 | `macrostrat` | Macrostrat | geologic map unit, lithology, strat name, age range (b_age/t_age), interval names | map-scale | compiled | global (variable scale) | CC-BY | `P` | `api` | `none` | 1 | VERIFIED this session: lat/lng -> units. Best coordinate->geology API that exists |
| 235 | `geochem_soil` | USGS soil geochemical survey / GEMAS / FOREGS | multi-element soil + stream sediment concentrations (~60 elements) | point (grid-sampled) | 2000s- | US, Europe, national atlases | public domain / CC-BY | `P` | `http` | `none` | 2 | GEMAS: 2108 EU agricultural sites. Links geology to contamination and agronomy |
| 236 | `onegeology` | OneGeology portal | national geological maps via WMS/WFS | 1:50k-1:1M | compiled | global (per-survey) | varies | `P/R` | `portal` | `none` | 2 | Federation of national surveys; patchy service quality |
| 237 | `usgs_sgmc` | USGS State Geologic Map Compilation | geologic units, lithology, age, structure, faults | 1:500k | 2017 | US | public domain | `P` | `http` | `none` | 2 |  |
| 269 | `boreholes` | National borehole/well logs (BGS, DINOloket, USGS) | stratigraphic logs, depth, lithology, downhole data | point | 1900s- | per-country | varies | `P/R` | `api` | `none` | 3 | NL DINOloket + UK BGS are exceptionally open; TRUE subsurface truth |
| 270 | `egdi` | EGDI (European Geological Data Infrastructure) | geology, boreholes, mineral occurrences, geohazards | varies | compiled | Europe | varies | `P/R` | `portal` | `none` | 3 |  |
| 305 | `karst` | Karst/sinkhole susceptibility maps | karst extent, sinkhole inventory | vector | static | US, EU, global WOKAM | CC-BY / varies | `P` | `http` | `none` | 4 |  |

## Knowledge/Culture (8)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 224 | `wikidata_geo` | Wikidata coordinate-bearing entities | every geolocated entity: buildings, events, people, organisations, works | point | continuous | global | CC0 | `P` | `api` | `none` | 1 | Millions of geolocated entities under CC0, SPARQL-queryable. Broadest single semantic layer |
| 240 | `wikipedia_geo` | Wikipedia geocoded articles | article text + coordinates | point | continuous | global | CC-BY-SA | `SA` | `api` | `none` | 2 | Already an AlphaEarth training target - the model has seen these |
| 275 | `gdelt_news` | GDELT geocoded events + news | geolocated news events, themes, tone, actors | point | 1979- | global | open | `P` | `api` | `none` | 3 | Media attention as a layer; geocoding is noisy |
| 276 | `hist_gazetteer` | Pleiades / World Historical Gazetteer / Getty TGN | historical place names, periods, place types | point | antiquity- | global | CC-BY | `P` | `api` | `none` | 3 | Place identity through time |
| 309 | `archaeology` | Open Context / EAMENA / ADS / national registers | excavation records, site condition, threat assessment | point/vector | continuous | regional | CC-BY / restricted | `P/R` | `api` | `none` | 4 | Site locations are often deliberately obscured to prevent looting |
| 310 | `meteorites` | Meteoritical Bulletin DB / Earth Impact Database | meteorite find + fall locations, class, mass; impact crater locations | point | 1400s- | global | open | `P` | `api` | `none` | 4 |  |
| 311 | `pdo_gi` | EU protected designations (PDO/PGI/GI) | legally defined production-area polygons by product | vector | continuous | EU + global GI | open | `P` | `api` | `none` | 4 | Food provenance as a legal geography |
| 312 | `religion_census` | US Religion Census / congregations | congregation counts, adherents by tradition | county | decennial | US | varies | `P/R` | `portal` | `none` | 4 |  |

## Molecular/sequence (geolocated) (18)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 225 | `ena_geo` | ENA portal geospatial search | ANY ENA sample with coordinates: runs, assemblies, taxon, collection date | point | 1980s- | global | open (INSDC) | `P` | `api` | `none` | 1 | VERIFIED: query=geo_box1(lat1,lon1,lat2,lon2). Gateway to all 16S/WGS/amplicon by location |
| 226 | `mgnify` | MGnify (EBI) | metagenome + amplicon samples, taxonomic + functional profiles, MAGs, biome lineage | point | 2008- | global | open (EBI terms) | `P` | `api` | `none` | 1 | VERIFIED: latitude_gte/longitude_gte bbox filter works (UNDERSCORES). ~30k terrestrial-soil, ~87k environmental |
| 242 | `emp_qiita` | Earth Microbiome Project / Qiita | standardized 16S across biomes with coordinates + EMP ontology | point | 2010- | global | CC-BY / open | `P` | `api` | `none` | 2 | The canonical cross-biome reference set |
| 243 | `globalfungi` | GlobalFungi / GSMc | fungal ITS community composition by site | point | compiled | global | CC-BY | `P` | `http` | `none` | 2 | ~60k+ georeferenced fungal samples |
| 244 | `inat_ebird` | iNaturalist / eBird | verified species observations with coordinates | point | continuous | global | CC mix / restricted | `P/R` | `api` | `key` | 2 | eBird needs key + terms; iNat research-grade flows to GBIF |
| 245 | `logan` | Logan (SRA unitigs/contigs on AWS) | assembled unitigs + contigs for every public SRA run | per-run | 2024 snapshot | global via BioSample join | open | `P` | `s3` | `none` | 2 | Petabase-scale. Needs join to BioSample coords - the geo is in BioSample, not Logan |
| 246 | `ncbi_biosample` | NCBI BioSample / SRA lat_lon attribute | sequencing run metadata with coordinates, host, isolation source | point | 1980s- | global | public domain | `P` | `api` | `none` | 2 | Entrez or SRA metadata in cloud tables; attribute completeness is poor and inconsistent |
| 247 | `obis` | OBIS | marine species occurrence records | point | historical- | global ocean | CC-BY | `P` | `api` | `none` | 2 | Marine analogue of GBIF |
| 248 | `pathogen_genomics` | NCBI Pathogen Detection / Nextstrain / Pathogenwatch | pathogen isolate genomes, AMR genes, geo + date | point/admin | continuous | global | public domain / open | `P` | `api` | `none` | 2 | Isolate-level AMR and lineage by location |
| 249 | `sandpiper` | Sandpiper | taxonomic profiles for all public SRA metagenomes | per-run | continuous | global | CC-BY | `P` | `http` | `none` | 2 | Pre-computed profiles - avoids reprocessing raw reads |
| 250 | `spire` | SPIRE (planetary microbiome resource) | MAGs, functional annotation, habitat, geo metadata | per-sample | compiled | global | CC-BY | `P` | `http` | `none` | 2 | VERIFY endpoint; Bork lab |
| 277 | `bold` | BOLD Systems | DNA barcode records with collection coordinates | point | 2005- | global | open | `P` | `api` | `none` | 3 |  |
| 278 | `genesys` | Genesys PGR / GRIN | germplasm accession COLLECTION SITE coordinates, taxon, traits | point | 1900s- | global | CC-BY / public domain | `P` | `api` | `none` | 3 | Where crop genetic diversity was collected - deep agronomic value |
| 279 | `idigbio` | iDigBio / herbaria / museum specimens | georeferenced natural history specimens | point | 1700s- | global | CC mix | `P` | `api` | `none` | 3 | Deep historical biodiversity baseline |
| 280 | `ocean_omics` | Tara Oceans / Malaspina / bioGEOTRACES / OSD | marine metagenomes + physicochemistry by station and depth | point+depth | 2009- | global ocean | CC-BY | `P` | `api` | `none` | 3 | Has a DEPTH axis - 3D not 2D |
| 281 | `soil_fauna` | SoilBON / earthworm / nematode / soil fauna atlases | soil invertebrate abundance + diversity | point/1km | compiled | global (sparse) | CC-BY | `P` | `http` | `none` | 3 |  |
| 282 | `vectorbase` | VectorBase / MAP vector occurrence | disease vector occurrence, insecticide resistance | point | compiled | global | CC-BY | `P` | `api` | `none` | 3 |  |
| 283 | `wastewater` | CDC NWSS / WastewaterSCAN / EU sentinel | pathogen concentrations by sewershed | sewershed polygon | 2020- | US, EU | open | `P` | `api` | `none` | 3 | Population-level biology at sub-city resolution |

## Public health (13)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 227 | `ihme_lbd` | IHME Local Burden of Disease / GBD subnational | child mortality, stunting, wasting, vaccination, HIV, education, LF | 5km raster / admin | 1990- | global (LMIC focus) | IHME free-use | `R` | `portal` | `free-reg` | 1 | GRIDDED health outcomes - the highest-resolution global health rasters that exist |
| 251 | `cdc_places` | CDC PLACES | 40+ chronic disease, prevention, risk-factor estimates | census tract / ZCTA | annual | US | public domain | `P` | `api` | `none` | 2 | Model-based small-area health estimates |
| 252 | `cdc_svi_eji` | CDC SVI / Environmental Justice Index | social vulnerability + environmental burden indices | census tract | multi-epoch | US | public domain | `P` | `http` | `none` | 2 | Composite indices tying exposure to vulnerability |
| 253 | `health_facilities` | healthsites.io / NPI / CMS POS / GIGA | facility locations, type, capacity, services | point | continuous | global / US | ODbL / public domain | `P/SA` | `api` | `none` | 2 |  |
| 254 | `travel_time_health` | MAP / Weiss accessibility to healthcare + cities | travel time to nearest facility / city | 1km | multi-epoch | global | CC-BY | `P` | `http` | `none` | 2 | Converts infrastructure into ACCESS - a derived but very usable layer |
| 284 | `ecdc_atlas` | ECDC Surveillance Atlas / Eurostat health | notifiable disease incidence, regional health indicators | NUTS2/3 | annual | Europe | open | `P` | `api` | `none` | 3 |  |
| 285 | `outbreaks_animal` | WOAH WAHIS / FAO EMPRES-i | animal disease outbreak locations, species, pathogen | point | 2005- | global | open | `P` | `api` | `none` | 3 | Geolocated zoonotic + livestock outbreaks |
| 286 | `seer_globocan` | SEER / national cancer registries / GLOBOCAN | cancer incidence + survival by registry area | county/registry | 1973- | US / global | public domain / open | `P` | `api` | `free-reg` | 3 |  |
| 287 | `usaleep` | USALEEP / small-area life expectancy | life expectancy at birth | census tract | 2010-2015 | US | public domain | `P` | `http` | `none` | 3 |  |
| 288 | `vital_stats` | Vital statistics (births, deaths, causes) | birth + death counts and rates by cause | county/admin | annual | most countries | open | `P` | `api` | `none` | 3 |  |
| 289 | `who_gho` | WHO Global Health Observatory / GLASS | health indicators, AMR surveillance | country/admin1 | annual | global | open | `P` | `api` | `none` | 3 | Coarse admin units only |
| 315 | `food_access` | USDA Food Access Research Atlas | food desert flags, store access, vehicle access | census tract | multi-epoch | US | public domain | `P` | `http` | `none` | 4 |  |
| 316 | `overdose_rx` | CDC overdose / opioid dispensing / ARCOS | overdose deaths, prescribing rates, shipments | county | annual | US | public domain | `P` | `api` | `none` | 4 |  |

## Hazard/Risk (9)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 238 | `drought` | US Drought Monitor / SPEI / Combined Drought Indicator | drought class, standardized indices | polygon/0.5deg | weekly/monthly 1900- | US / global | open | `P` | `api` | `none` | 2 |  |
| 239 | `ibtracs` | IBTrACS | all historical tropical cyclone tracks, intensity, pressure, wind radii | track | 1842- | global | public domain | `P` | `http` | `none` | 2 | Complete historical TC exposure for any coastal box |
| 271 | `crashes` | US FARS / state crash DBs / EU CARE | crash location, severity, vehicles, conditions | point | 1975- | US / EU | public domain / restricted | `P/R` | `api` | `none` | 3 |  |
| 272 | `emdat` | EM-DAT / DesInventar | disaster events, deaths, damages, affected | country/admin | 1900- | global | academic free-use | `R` | `portal` | `free-reg` | 3 | Coarse geocoding; registration required |
| 273 | `exposure_model` | GEM Global Exposure + Vulnerability Model | building stock, occupancy, replacement cost, fragility | admin/grid | static | global | CC-BY-NC-SA? | `NC` | `http` | `none` | 3 | VERIFY licence |
| 274 | `severe_wx` | NOAA SPC storm reports / ESWD | tornado, hail, wind event locations, magnitude, damage | point/track | 1950- | US / Europe | public domain / open | `P` | `http` | `none` | 3 |  |
| 306 | `inform` | INFORM Risk Index / UNDRR GAR | composite hazard, vulnerability, coping-capacity scores | country/admin1 | annual | global | open | `P` | `http` | `none` | 4 |  |
| 307 | `nbi_bridges` | US National Bridge Inventory | bridge location, age, condition rating, traffic, material | point | annual 1992- | US | public domain | `P` | `http` | `none` | 4 | Asset-level infrastructure condition |
| 308 | `tsunami` | NOAA NGDC historical tsunami + runup DB | tsunami events, runup heights, sources | point | 2000 BCE- | global | public domain | `P` | `api` | `none` | 4 |  |

## Mobility/Access (3)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 241 | `accessibility_iso` | Computed isochrones / accessibility (OSRM, Valhalla, OTP+GTFS) | travel-time isochrones, reachable population, service access | derived | on demand | global | n/a (compute) | `P` | `http` | `none` | 2 | TIER-2 derivation combining OSM + GTFS + population |
| 313 | `gbfs` | GBFS bikeshare + micromobility feeds | station locations, vehicle availability, system geography | point | real-time | global (many cities) | open | `P` | `api` | `none` | 4 |  |
| 314 | `openflights` | OpenFlights / airline schedules | airport pairs, routes, airlines, frequencies | point/route | continuous | global | ODbL | `SA` | `http` | `none` | 4 |  |

## Built/Utility (10)

| # | module | source | layers | res | temporal | coverage | licence | tier | access | auth | prio | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 255 | `datacenters` | Data Center Map / IXPs / fibre routes (Afterfibre, ITU) | facility + exchange locations, terrestrial fibre routes | point/vector | continuous | global | varies | `P/R` | `api` | `none` | 3 | Digital infrastructure geography |
| 256 | `openchargemap` | OpenChargeMap / fuel stations | EV charger locations, connector type, power, operator | point | continuous | global | CC-BY-SA / ODbL | `SA` | `api` | `key` | 3 |  |
| 257 | `schools_edu` | US NCES CCD/EDGE / national school registries | school location, enrolment, demographics, performance | point | annual | US / many | public domain / varies | `P` | `api` | `none` | 3 |  |
| 290 | `building_permits` | City/state building permit records | permit type, valuation, date, status by address | address | continuous | many jurisdictions | open gov | `P` | `api` | `varies` | 4 | Leading indicator of construction change |
| 291 | `food_facilities` | USDA FSIS / slaughterhouses / grain elevators / processing | facility location, type, capacity, inspection status | point | continuous | US + others | public domain | `P` | `api` | `none` | 4 | Agricultural supply-chain geography |
| 292 | `iaea_pris` | IAEA PRIS / nuclear facilities | reactor location, type, capacity, status | point | continuous | global | open | `P` | `api` | `none` | 4 |  |
| 293 | `restaurant_inspect` | Municipal restaurant + facility inspections | inspection score, violations, date by address | address | continuous | many cities | open gov | `P` | `api` | `varies` | 4 |  |
| 294 | `tree_inventory` | Municipal street tree inventories / i-Tree | individual tree species, DBH, condition, planting date | point | continuous | many cities | open gov | `P` | `portal` | `varies` | 4 | Individual-tree records where published |
| 295 | `water_rights` | US western state water rights / irrigation districts | diversion points, allocation volume, priority date, district boundaries | point/vector | continuous | western US + others | public domain | `P` | `portal` | `varies` | 4 | Legal water entitlement - institutional, not physical |
| 296 | `wwtp` | EU UWWTD / EPA wastewater facilities | treatment plant location, capacity, load, outfalls | point | continuous | EU / US | open | `P` | `api` | `none` | 4 |  |

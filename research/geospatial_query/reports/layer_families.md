# Candidate layer families

Rolled up from the 35 fine-grained groups in `geolocatable_data_registry.md`
into **10 families**, then reclassified by subject under six rules.

317 entries from 312 placed modules. Five entries are splits over one upstream
source each (`ghsl` ×2, `ascat` ×3, `cygnss` ×3 count as 5 extra). Four modules
are dropped — see "Dropped" below. Counts here are **computed from the parsed
registry** (see `layer_inventory.csv`), and supersede the running tallies kept
during passes 1–17, which had drifted by 1–2 in five families.

### Rules

1. **Subject over provenance.** A module belongs to the family of the subject
   it describes, not the instrument, archive or organisation that produced it.
2. **"&" is a union, not an intersection.** A module qualifies by matching
   *either* term. Applies to Public health & microbiology (health *or* microbial
   life), Infrastructure & industry (built stock *or* industrial assets).
3. **Frozen water is filed by permanence.** Seasonal and annual ice — snow,
   sea ice — → climate, where it behaves as a state variable that accumulates
   and melts. Multi-decadal ice with its own geometry and motion — glaciers,
   permafrost — → geology, where it behaves as terrain. No cryosphere family.
4. **Geology owns elevation** — land DEMs and bathymetry alike. Water bodies
   owns the water, not the floor beneath it.
5. **Current data only.** A module whose data does not extend to the present
   is dropped, however deep its archive.
6. **Measured structures and material properties → geology; event catalogues
   and modelled risk surfaces → hazards.** The fault map is geology, the
   earthquake catalogue and the PGA model are hazards.

| # | Family | n | What it holds | Key examples | Stretch additions |
|---|---|---|---|---|---|
| 1 | **Socio-economic** | 56 | People, their money, their movement, the institutions governing their ground, and how places are named and known. Sub-groups: population & demography · economy, wealth & finance · activity & mobility · legal & political (admin/electoral units, cadastre, concessions, customary tenure, entitlements, designations) · naming & knowledge (toponymy, geolocated entities, media attention, cultural and heritage records). | `census_micro` (US block level is the finest demographic data in existence) · `lodes` (block-level home→work flows) · `cadastre_open` · `wikidata_geo` (millions of geolocated entities, CC0, SPARQL) · `geonames` | Zoning codes, land-use plans, planning consents — the regulatory half of the legal sub-group, absent entirely · Platform and marketplace listings |
| 2 | **Infrastructure & industry** | 46 | The physical stock people build and operate, and the light and heat it emits. Sub-groups: built form & housing · networks & utilities (road, rail, power, pipeline, sewer, spectrum, bandwidth) · industrial & facility assets with ownership and emissions · extraction (mines, deposits, tailings) · activity emission (nighttime lights, flaring). | `overture` · `osm_overpass` · `gem_trackers` (25 trackers, 200+ countries) · `ghsl_built` (built surface + **building height** globally) · `blackmarble` (nighttime lights) | Grid operations: ENTSO-E load/generation, EIA-860/923 plant output, nodal prices, interconnection queues |
| 3 | **Hazards** | 44 | Things that can hurt, plus the monitoring and structural records that feed risk assessment. Sub-groups: hazard/risk & episodic events (14) · contamination & toxics (16) · human-centred exposure (6). | `ibtracs` (all TC tracks 1842–) · `eq_catalog` (**verified**: USGS FDSN bbox+time+magnitude) · `wqp` (tens of millions of analyte results) · `pfas_ucmr` (**measured** PFAS) · `noise_maps` | UXO and landmine contamination (UNMAS, HALO) · Catastrophe-model loss curves to pair with `nfip` realized losses |
| 4 | **Macrobiology** | 39 | Life visible without a sequencer: land cover and change, biomass and carbon, crops and agronomy, canopy structure, species occurrence and specimens, ground-measured plots, palaeoecological records. | `esa_worldcover` · `hansen_gfc` · `gaez` (crop-by-crop suitability) · `gbif` · `gedi` (canopy height, PAI, AGB) | Animal movement — Movebank, Motus, telemetry (trajectories, a distinct data model) |
| 5 | **Geology** | 39 | The solid Earth and its surface form, above and below the waterline: geologic maps, lithology, soil properties, potential-field geophysics, boreholes, **all elevation** (land DEMs and bathymetry), derived terrain, glaciers and permafrost, crustal structure and fault geometry, ground motion. Episodic events moved to hazards; the structures that host them stay here. | `macrostrat` (**verified**: lat/lng → units, lithology, age) · `soilgrids` · `copernicus_dem` · `gebco` (seafloor elevation) · `egms` (open InSAR, ~3 mm/yr) · `active_faults` | **Isoscapes** — GNIP/OIPC δ²H/δ¹⁸O, ⁸⁷Sr/⁸⁶Sr and Pb ratios; stable isotopes, no radiation level, used for provenance tracing · Geotechnical soundings (CPT) |
| 6 | **Public health & microbiology** | 28 | Union family — a module qualifies if it concerns human health **or** microbial life. Sub-groups: *health outcomes & services* (18) — disease, mortality and life expectancy at the finest published geography, facilities and travel time mediating access, vector distributions driving burden; *microbiology* (12) — geolocated sequence of organisms below visual resolution: environmental metagenomes, amplicon surveys, pathogen isolates, soil eDNA, wastewater. | `ihme_lbd` (5 km gridded — highest-resolution global health rasters that exist) · `cdc_places` · `mgnify` (**verified**: `latitude_gte`/`longitude_gte`) · `ena_geo` (**verified**: `geo_box1()`) · `pathogen_genomics` | Small-area hospital discharge / claims data · AADR ancient human DNA with site coordinates · National eDNA monitoring programmes |
| 7 | **Climate** | 27 | Reanalysis, gridded climatology, projections, atmospheric composition and profiles, the cryospheric state (snow, sea ice), the land-surface state (soil moisture), fire as a disturbance process, and palaeoclimate reconstruction. | `era5` · `chirps` (gauge-blended; better than reanalysis for tropical precip) · `sentinel5p` · `smap` · `sea_ice` · `firms` (active fire + burned area) | High-resolution regional reanalyses — CERRA/CARRA (~5 km) · Bias-corrected CMIP6 beyond `nex_gddp` |
| 8 | **Spectral** | 18 | Sensor-native radiance and backscatter — the pixel before anyone turns it into a class, a construct or a stack. Optical, SAR, thermal, aerial photography. | `sentinel2_l2a` · `landsat_c2l2` (only free global 30 m **surface temperature**) · `sentinel1_grd` · `naip` | Geostationary optical/thermal — GOES ABI, MSG SEVIRI, Himawari AHI at 10-min cadence. The registry has no sub-daily imaging at all |
| 9 | **Water bodies** | 12 | Ocean, lakes, rivers, reservoirs and groundwater — surface, volume, level, chemistry, storage and flow. Strictly **blue water**: liquid water in bodies and aquifers. All frozen water is elsewhere (snow and sea ice → climate; glaciers and permafrost → geology), as is all elevation including bathymetry (→ geology). | `cmems` (ocean analogue of ERA5) · `hydrosheds` (drainage, basins, lakes) · `grace` (total water storage, groundwater) · `water_level` · `tides` | Reservoir operations and storage time series · Aquaculture facility inventories |
| 10 | **Latent** | 8 | High-dimensional or unreduced products whose dimensionality exceeds what the user wants, so the layer comes from fitting, unmixing or regressing rather than from reading a value. Carries a **density** attribute — members differ fundamentally in whether they can fill a box. | `alphaearth` (64-dim annual, 10 m, global land) · `emit` (285 bands) · `modis_bio` (5 variable groups) · `cgls` (8 variables) · `icesat2` (raw photon cloud, sparse transect) | Temporal and multi-scale embedding products; additional encoders over the same imagery |

## Dropped

Four modules fail rule 5 — static archives with no ongoing acquisition:

| Module | Coverage | Why dropped |
|---|---|---|
| `declass_corona` | 1960–1972 | Declassified film, fixed archive |
| `declass_hexagon` | 1963–1984 | Declassified film, fixed archive |
| `hist_aerial` | 1920s–1990s | Historical aerial frames, fixed archives |
| `hist_topo` | 1880s– | Scanned map sheets, fixed archives |

The other 14 formerly-dropped modules **do** hold current data and were
re-admitted by subject: `wikidata_geo`, `wikipedia_geo`, `gdelt_news`,
`geonames`, `glottolog`, `hist_gazetteer`, `religion_census`, `archaeology`
and `heritage` → socio-economic (naming & knowledge sub-group); `meteorites`
→ geology; `paleoclim` and `itrdb` → climate; `neotoma` and `hyde_luh` →
macrobiology. `hyde_luh` qualifies because it runs to 2100; `itrdb` and
`neotoma` because both take ongoing submissions.

## Registry corrections identified

| Module | Correction |
|---|---|
| `icesat2` | `layers` cell lists only photon heights and terrain+canopy. The mission also produces ice-sheet height and height *change* (ATL06, ATL11, ATL14, ATL15), sea ice height and freeboard (ATL07, ATL10, ATL20, ATL21), ocean and inland water surface height (ATL12, ATL13 — the latter including subsurface attenuation, wave height, wind speed and coarse bottom depth), and atmospheric backscatter, cloud layers and blowing snow (ATL04, ATL09) |
| `icesat2` | `res_m` of "~20 m segments" conflates products: ATL06 is 40 m segments posted every 20 m; ATL08 reports per 100 m |
| `modis_bio`, `cgls` | Accurately described as many layers from one adapter, but those layers span climate, macrobiology and water bodies, so a single family assignment loses most of them |
| `nwis` | Cited as a hydrology example in versions 4–7 of this document. It is in **hazards** (contamination sub-group) with `wqp` and `grdc_gauges`. Corrected |
| all | Proposed new `coverage` column: `wall-to-wall` · `swath-partial` · `transect` · `point-network` · `admin-aggregate`. `res_m` half-encodes this but reports `25` for GEDI footprints and `~20 segments` for ICESat-2, both of which read as raster |

## Decision log

| Pass | Decision |
|---|---|
| 1 | 35 registry groups → 15 families |
| 2 | Contamination & toxics → sub-group of hazards |
| 3 | Anthropocentric merge (107); embeddings split out of spectral; trade/freight dropped; animal movement → sub-group of macrobiology |
| 4 | Renames to short forms; terrain & cryosphere → geology; historical & deep time dropped |
| 5 | Anthropocentric decomposed → infrastructure & industry, socio-economic, legal & political; public health promoted; human-centred exposure → hazards; naming/knowledge/culture dropped |
| 6 | Isoscapes → geology; legal & political → sub-group of socio-economic; validation family dropped |
| 7 | Subject-over-provenance rule adopted; 27 modules moved |
| 8 | Duals resolved individually: `ghsl` split · `modis_bio`/`cgls` → Latent (Embedding renamed) · `mrds` → infrastructure · `firms` → climate |
| 9 | Remaining duals: `emit` → Latent · `ascat`/`cygnss` split by layer · `vectorbase` + `malaria_atlas` → public health · `eu_lpis` → socio-economic (legal) |
| 10 | `icesat2` → Latent with a sparse-transect flag; density promoted to a proposed registry-wide `coverage` column |
| 11 | Hydrology → **Water bodies**, rescoped to blue water · snow and soil moisture → climate |
| 12 | Frozen-water rule stated (rule 3); `sea_ice` confirmed in water bodies; no cryosphere family |
| 13 | Microbiology + public health → Health & microbiology; union-naming convention stated (rule 2) |
| 14 | Nighttime lights (`blackmarble`, `dmsp_ols`) → infrastructure · `modis_lc_fire` → climate · current-data rule adopted (rule 5), 4 archives dropped and 14 modules re-admitted · geology owns elevation (rule 4), `gebco` and `emodnet_bathy` → geology |
| 15 | `sea_ice` → climate (rule 3 restated by permanence); episodic events `eq_catalog`/`volcanoes`/`landslides`/`seismic_hazard` → hazards; `active_faults` stays geology |
| 16 | `volcanoes` confirmed in hazards on risk-signature grounds (concentrated low-frequency/high-consequence loss, event-catalogue data model), not on equivalent magnitude; 14 re-admitted modules confirmed |
| 17 | `active_faults` confirmed in geology; rule 6 added — measured structure → geology, event catalogues and modelled risk → hazards |
| 18 | **Registry parsed and every one of the 316 modules assigned (`layer_inventory.csv`). Family renamed to Public health & microbiology. `schools_edu` → infrastructure and `giga_schools` → socio-economic (education services were wrongly in the health sub-group). Five provenance misfilings corrected: `jrc_gsw` and `groundwater` → water bodies, `enmap_prisma` → spectral, `lightning` → climate, `geotagged_photos` → socio-economic |
| 19 | All 111 inherited placements reviewed: 103 confirmed, `glofas` → hazards (rule 6), `nutrients` → hazards (parallel to `pesticide_use`). 6 entries pending a judgement call: ambient air quality (`sentinel5p`, `cams`, `maiac_aod`, `acag_pm25`, `openaq`) and `space_weather` |

## Pass 15

| Change | Effect |
|---|---|
| `sea_ice` → climate | Rule 3 restated by **permanence** rather than host body: seasonal ice (snow, sea ice) is a climate state variable, multi-decadal ice (glaciers, permafrost) is terrain. Water bodies becomes strictly liquid |
| `eq_catalog`, `volcanoes`, `landslides`, `seismic_hazard` → hazards | Episodic events join `tsunami`, which was already there. Hazards' definition widened to match what it already contained — it holds `nbi_bridges`, `nwis`, `grdc_gauges` and `crashes`, which are monitoring records rather than hazards |
| `active_faults` stays in geology | Fault traces and slip rates are structural geology — a persistent feature, not an event. Geology keeps the structures; hazards takes the events they produce |

Hazards' episodic sub-group is now `drought` · `ibtracs` · `crashes` ·
`emdat` · `exposure_model` · `severe_wx` · `inform` · `nbi_bridges` ·
`tsunami` · `cygnss_flood` · `eq_catalog` · `volcanoes` · `landslides` ·
`seismic_hazard` (14).

## Open

Nothing substantive.

**`volcanoes` confirmed in hazards** (pass 16). Volcanic risk is one to two
orders of magnitude below seismic risk by mortality — about 280,000 recorded
fatalities since 1600 AD and ~540/year on average, described in the literature
as modest relative to other major natural hazards — but it has the same risk
*signature*: low frequency, high consequence, geologically sourced, with
mortality extremely concentrated (the ten deadliest eruptions account for >80%
of deaths) and 800 million people living within 100 km of an active volcano.
The Smithsonian GVP record functions in a risk workflow exactly as
`eq_catalog` does: an event catalogue with magnitudes (VEI) and dates, used for
recurrence estimation and hazard zonation. Filed by kind, not by magnitude —
magnitude was never the operative test in this family, which also contains
`light_pollution` and `noise_maps`.

**`active_faults` confirmed in geology** (pass 17), and the reason generalizes
into rule 6: **measured structures and material properties → geology; event
catalogues and modelled risk surfaces → hazards.** GEM's Global Active Faults
supplies trace geometry, dip, type and slip rate — a structural measurement
several modelling steps away from a risk number. Reaching `seismic_hazard`'s
PGA-by-return-period requires segmenting traces into sources, a scaling
relation for maximum magnitude, conversion of slip rate to moment rate
distributed over a magnitude-frequency model, background smoothed seismicity
from the earthquake catalogue, ground-motion prediction equations and site
amplification, then integration over all sources. `eq_catalog` is itself an
input at the background-seismicity step, so a hazards-resident catalogue and a
geology-resident fault map both feed a hazards-resident model output. Rule 6
also predicts the untouched placements correctly: `crust_model` and
`heat_flow` are measured properties and stay in geology; `exposure_model` and
`inform` are modelled risk and sit in hazards.

## Coverage of the decision record

**All 317 entries are explicitly decided.** All 111 entries that previously
inherited a registry-group default have been individually reviewed in pass 19:
103 confirmed where they sat, 2 moved under an existing rule or by parallel
(`glofas` → hazards by rule 6; `nutrients` → hazards, paralleling
`pesticide_use`), and 6 went to hazards in pass 20 (the
5 air-quality entries and `space_weather`). Per-entry detail with a `decided`
flag is in `layer_inventory.md` / `layer_inventory.csv`.

Resolutions worth recording, since each was a close call settled by precedent
rather than by rule:

| Entry | Kept in | Reasoning |
|---|---|---|
| `ecostress` | spectral | 70 m LST is a measured surface property; `landsat_c2l2` surface temperature is already in spectral |
| `fluxnet` | macrobiology | Eddy-covariance CO₂/H₂O/energy flux is an ecosystem carbon-and-water measurement, alongside GPP/NPP and biomass |
| `karst` | geology | Karst extent is a geological unit; the sinkhole inventory half would be hazards, but extent is the primary layer |
| `gsocmap` | geology | Soil organic carbon *stock* is a soil property; `soilgrids` already carries SOC |
| `solar_atlas`, `wind_atlas` | climate | Rule 1: the subject is a climate variable even though the use is infrastructure siting |
| `geomag_field` | geology | A model of the core field — solid-Earth, despite being computed rather than measured |
| `irrigation` | macrobiology | Irrigated area fraction and crop calendars are agronomy, not asset inventory |
| 20 | **All 6 pending → hazards: ambient air quality (`sentinel5p`, `cams`, `maiac_aod`, `acag_pm25`, `openaq`) → contamination & toxics; `space_weather` → episodic events. Every entry now explicitly assigned; hazards becomes the second-largest family at 44** |

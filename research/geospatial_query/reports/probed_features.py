"""Curated feature rows for the sources probed in lanes A-D, written to probed_features.csv."""
import csv
from pathlib import Path

OUT = Path(__file__).with_name("probed_features.csv")
FAMILIES = {"socio-economic", "infrastructure", "hazards", "macrobiology", "geology",
            "public health & microbiology", "climate", "spectral", "water bodies",
            "latent", "quality"}
TYPES = {"satellite", "airborne", "drone", "vehicle", "fixed camera", "handheld",
         "ground station", "field survey", "model", "registry"}

PC = "https://planetarycomputer.microsoft.com"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
NASA = "NASA Earthdata open data (no use restriction stated in the record)"
OGL_CA = "Environment and Climate Change Canada data, Open Government Licence - Canada"

# source id -> (source_type, source_url, licence, default gap)
SOURCES = {
    "sentinel2_l2a": ("satellite", f"{PC}/api/stac/v1/collections/sentinel-2-l2a", "Copernicus/Landsat open (PC: proprietary tag, free)", "Q1"),
    "landsat_c2l2_st": ("satellite", f"{PC}/api/stac/v1/collections/landsat-c2-l2", "Copernicus/Landsat open (PC: proprietary tag, free)", "Q1"),
    "sentinel1_rtc": ("satellite", f"{PC}/api/stac/v1/collections/sentinel-1-rtc", "Copernicus/Landsat open (PC: proprietary tag, free)", "Q1"),
    "hls": ("satellite", f"{PC}/api/stac/v1/search", "NASA open (proprietary tag on PC; free)", "Q1"),
    "s2_l1c": ("satellite", "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l1c", "Copernicus open (Sentinel Data Legal Notice)", "S5"),
    "landsat_l1": ("satellite", "https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l1", "USGS public domain", "S5"),
    "usgs3dep_pc": ("airborne", f"{PC}/dataset/3dep-lidar-copc", "proprietary (PC collection licence field; USGS data)", "S1"),
    "naip_pc": ("airborne", f"{PC}/dataset/naip", "proprietary (PC collection licence field; USDA FSA data)", "S1"),
    "usgs_wesm": ("airborne", "https://index.nationalmap.gov/arcgis/rest/services/3DEPElevationIndex/MapServer/8", "not stated by the service (USGS 3DEP index)", "S1"),
    "nrcan_hrdem": ("airborne", "https://datacube.services.geo.ca/pgstac/api", "OGL-Canada-2.0", "S1"),
    "nrcan_napl": ("airborne", "https://datacube.services.geo.ca/pgstac/api", "OGL-Canada-2.0 (collection licence field)", "S1"),
    "neon_aop": ("airborne", "https://data.neonscience.org/api/v0/sites", "NEON open data policy (licence not in the API; check neonscience.org data policy)", "S1"),
    "opentopography": ("airborne", "https://portal.opentopography.org/API/otCatalog", "per-dataset (USGS 3DEP public domain; others vary); citation required", "S1"),
    "noaa_dav": ("airborne", "https://coast.noaa.gov/arcgis/rest/services/DAV/DAV_footprints/MapServer/0", "not in the footprint layer; stated per InPort record", "S1"),
    "uavsar_asf": ("airborne", "https://api.daac.asf.alaska.edu/services/search/param", "NASA Earthdata open data (no use restriction stated in the record)", "S1"),
    "oam": ("drone", "https://api.imagery.hotosm.org/stac", "CC-BY-4.0", "S2"),
    "geonadir": ("drone", "https://api.geonadir.com/api/dataset/", "unstated in API; GeoNadir FAIR Open Data programme states CC-BY-4.0 for its AWS subset", "S2"),
    "emit": ("satellite", CMR, NASA, "S3"),
    "aviris": ("airborne", CMR, NASA, "S3"),
    "pace_oci": ("satellite", CMR, NASA, "S3"),
    "enmap": ("satellite", "https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/ENMAP_HSI_L2A", "proprietary (STAC licence field)", "S3"),
    "desis": ("satellite", "https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/DESIS_HSI_L2A", "proprietary (STAC licence field)", "S3"),
    "planet_open": ("satellite", "https://www.planet.com/data/stac/catalog.json", "CC-BY-4.0 / CC-BY-SA-4.0 / CC-BY-NC (per collection)", "S4"),
    "maxar_open": ("satellite", "https://maxar-opendata.s3.amazonaws.com/events/catalog.json", "CC-BY-NC-4.0", "S4"),
    "satellogic_earthview": ("satellite", "https://satellogic-earthview.s3.us-west-2.amazonaws.com/", "CC-BY-4.0", "S4"),
    "umbra_open": ("satellite", "https://umbra-open-data-catalog.s3.amazonaws.com/stac/catalog.json", "CC-BY-4.0", "S4"),
    "capella_open": ("satellite", "https://capella-open-data.s3.us-west-2.amazonaws.com/stac/catalog.json", "CC-BY-4.0", "S4"),
    "iceye_open": ("satellite", "https://iceye-open-data-catalog.s3.amazonaws.com/collections/iceye-sar.json", "CC-BY-4.0", "S4"),
    "nza": ("registry", "https://tiles.zoningatlas.org/", "Terms of Use (zoningatlas.org/terms) bar using, storing or downloading Website Content without written permission; no data licence published", "S6"),
    "padus": ("registry", "https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_4_1/MapServer/0", "U.S. Government work (USGS data release doi:10.5066/P96WBCHS)", "S6"),
    "bc_alr": ("registry", "https://openmaps.gov.bc.ca/geo/pub/ows", "Open Government Licence - British Columbia", "S6"),
    "eu_urban_atlas": ("registry", "https://image.discomap.eea.europa.eu/arcgis/rest/services/UrbanAtlas/UA_UrbanAtlas_2018/MapServer/2", "Not stated by the service (copyright text: 'European Environment Agency (EEA)')", "S6"),
    "vancouver_zoning": ("registry", "https://opendata.vancouver.ca/explore/dataset/zoning-districts-and-labels/", "Open Government Licence - Vancouver", "S6"),
    "toronto_zoning": ("registry", "https://open.toronto.ca/dataset/zoning-by-law/", "Open Government Licence - Toronto (portal default; CKAN licence field is null)", "S6"),
    "calgary_land_use": ("registry", "https://data.calgary.ca/resource/qe6k-p9nh.json", "See Terms of Use (City of Calgary Open Data Terms of Use / OGL-Calgary)", "S6"),
    "usgs_waterdata": ("ground station", "https://api.waterdata.usgs.gov/ogcapi/v0", "U.S. Government public domain (USGS)", "S7"),
    "eccc_hydrometric": ("ground station", "https://api.weather.gc.ca/collections/hydrometric-stations", OGL_CA, "S7"),
    "hydrorivers": ("model", "https://www.hydrosheds.org/products/hydrorivers", "HydroSHEDS licence: free for scientific, educational and commercial use under the HydroSHEDS licence agreement", "S7"),
    "nhdplus_hr": ("model", "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer", "U.S. Government public domain (USGS)", "S7"),
    "nrcan_nhn": ("registry", "https://maps.geogratis.gc.ca/wms/hydro_network_en", "Open Government Licence - Canada", "S7"),
    "eccc_climate": ("ground station", "https://api.weather.gc.ca/collections/climate-stations", OGL_CA, "S8"),
    "ghcn_daily": ("ground station", "https://www.ncei.noaa.gov/access/services/search/v1/data", "NOAA NCEI open data (GHCN-Daily v3, cite Menne et al. 2012)", "S8"),
    "daymet": ("model", "https://daymet.ornl.gov/single-pixel/api/data", "Citation required (Thornton et al. 2022, doi:10.3334/ORNLDAAC/2129)", "S8"),
    "terraclimate": ("model", "https://thredds.northwestknowledge.net/thredds/ncss/TERRACLIMATE_ALL/", "CC0-1.0", "S8"),
    "chirps": ("model", "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/tifs/", "Not stated (cite Funk et al.)", "S8"),
    "panoramax": ("vehicle", "https://api.panoramax.xyz/api/search", "CC-BY-SA-4.0", "S9"),
    "drivebc_webcams": ("fixed camera", "https://www.drivebc.ca/api/webcams/", "not stated in API response (images carry a DriveBC.ca mark)", "S9"),
    "phenocam": ("fixed camera", "https://phenocam.nau.edu/api/cameras/", "not stated in API response (PhenoCam data policy requires citation)", "S9"),
    "wikimedia_commons": ("handheld", "https://commons.wikimedia.org/w/api.php", "per file (CC BY, CC BY-SA, PD)", "S9"),
    "inaturalist": ("handheld", "https://api.inaturalist.org/v1/observations", "per observation license_code (cc-by, cc-by-nc, cc0, ...)", "S9"),
    "gbif_media": ("handheld", "https://api.gbif.org/v1/occurrence/search", "per record (CC0, CC-BY, CC-BY-NC)", "S9"),
    "geograph": ("handheld", "https://www.geograph.org.uk/syndicator.php", "CC-BY-SA-2.0", "S9"),
}

# (family, feature, description, source[, gap override])
ROWS = [
    # --- POC scene adapters (Q1) ---
    ("quality", "s2_off_nadir_deg", "Scene QC: view zenith, mean of the 13 per-band angles in the granule metadata", "sentinel2_l2a"),
    ("quality", "s2_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "sentinel2_l2a"),
    ("quality", "s2_sun_azimuth_deg", "Scene QC: sun azimuth", "sentinel2_l2a"),
    ("quality", "s2_cloud_cover_scene_pct", "Scene QC: cloud cover of the whole tile, percent", "sentinel2_l2a"),
    ("quality", "s2_cloud_cover_aoi_pct", "Scene QC: cloud cover inside the AOI from the scene classification, percent", "sentinel2_l2a"),
    ("quality", "lst_off_nadir_deg", "Scene QC: off-nadir angle of the Landsat scene", "landsat_c2l2_st"),
    ("quality", "lst_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "landsat_c2l2_st"),
    ("quality", "lst_sun_azimuth_deg", "Scene QC: sun azimuth", "landsat_c2l2_st"),
    ("quality", "lst_cloud_cover_scene_pct", "Scene QC: cloud cover of the whole scene, percent", "landsat_c2l2_st"),
    ("quality", "lst_cloud_cover_aoi_pct", "Scene QC: cloud cover inside the AOI from the QA band, percent", "landsat_c2l2_st"),
    ("quality", "s1_incidence_deg", "Scene QC: radar incidence angle at the AOI centroid from the GRD annotation", "sentinel1_rtc"),
    # --- HLS ---
    ("spectral", "hls_reflectance", "Harmonized Landsat Sentinel: surface reflectance", "hls"),
    ("quality", "hls_view_zenith_deg", "Scene QC: view zenith from the per-pixel VZA asset or the scene mean", "hls"),
    ("quality", "hls_view_azimuth_deg", "Scene QC: view azimuth", "hls"),
    ("quality", "hls_sun_azimuth_deg", "Scene QC: sun azimuth", "hls"),
    ("quality", "hls_cloud_cover_scene_pct", "Scene QC: cloud cover of the whole tile, percent", "hls"),
    # --- uncorrected imagery (S5) ---
    ("spectral", "s2l1c_toa_reflectance", "Sentinel-2 L1C: top-of-atmosphere reflectance", "s2_l1c"),
    ("quality", "s2l1c_view_zenith_deg", "Scene QC: view zenith from the granule metadata sidecar", "s2_l1c"),
    ("quality", "s2l1c_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "s2_l1c"),
    ("quality", "s2l1c_sun_azimuth_deg", "Scene QC: sun azimuth", "s2_l1c"),
    ("quality", "s2l1c_cloud_cover_scene_pct", "Scene QC: cloud cover of the whole tile, percent", "s2_l1c"),
    ("spectral", "lsl1_toa_reflectance", "Landsat Collection 2 Level-1: top-of-atmosphere reflectance", "landsat_l1"),
    ("quality", "lsl1_off_nadir_deg", "Scene QC: off-nadir angle", "landsat_l1"),
    ("quality", "lsl1_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "landsat_l1"),
    ("quality", "lsl1_sun_azimuth_deg", "Scene QC: sun azimuth", "landsat_l1"),
    ("quality", "lsl1_cloud_cover_scene_pct", "Scene QC: cloud cover of the whole scene, percent", "landsat_l1"),
    # --- airborne lidar and imagery (S1) ---
    ("geology", "usgs3dep_dtm_elev_m", "3DEP lidar terrain: bare-earth elevation, metres", "usgs3dep_pc"),
    ("geology", "usgs3dep_dsm_elev_m", "3DEP lidar surface: first-return elevation, metres", "usgs3dep_pc"),
    ("macrobiology", "usgs3dep_hag_m", "3DEP lidar height: height above ground, metres", "usgs3dep_pc"),
    ("spectral", "usgs3dep_intensity", "3DEP lidar intensity: return intensity", "usgs3dep_pc"),
    ("infrastructure", "usgs3dep_point_class", "3DEP lidar classes: ground, vegetation and building point classification", "usgs3dep_pc"),
    ("macrobiology", "usgs3dep_returns_n", "3DEP lidar returns: number of returns per pulse", "usgs3dep_pc"),
    ("quality", "usgs3dep_scan_angle_deg", "Lidar QC: per-point scan angle in the point cloud", "usgs3dep_pc"),
    ("spectral", "naip_rgbnir_dn", "Aerial imagery: NAIP four-band colour and near-infrared", "naip_pc"),
    ("quality", "naip_flight_year", "Imagery QC: state-wide flight year", "naip_pc"),
    ("geology", "wesm_workunit_n", "Lidar survey index: 3DEP work units covering the area", "usgs_wesm"),
    ("quality", "wesm_quality_level", "Lidar QC: USGS quality level of the survey (QL0 to QL3)", "usgs_wesm"),
    ("geology", "hrdem_dtm_elev_m", "Canadian lidar terrain: bare-earth elevation at 1 m, metres", "nrcan_hrdem"),
    ("geology", "hrdem_dsm_elev_m", "Canadian lidar surface: first-return elevation, metres", "nrcan_hrdem"),
    ("spectral", "napl_airphoto_dn", "Historical air photos: orthomosaic of National Air Photo Library frames", "nrcan_napl"),
    ("geology", "neon_lidar_elev_m", "NEON airborne lidar: elevation point cloud, metres", "neon_aop"),
    ("spectral", "neon_rgb_dn", "NEON airborne camera: high-resolution colour imagery", "neon_aop"),
    ("spectral", "neon_hyperspec_reflectance", "NEON airborne imaging spectrometer: surface reflectance", "neon_aop", "S3"),
    ("geology", "opentopo_lidar_survey_n", "OpenTopography catalogue: point-cloud surveys covering the area", "opentopography"),
    ("geology", "noaa_dav_lidar_survey_n", "NOAA Digital Coast: coastal lidar surveys covering the area", "noaa_dav"),
    ("spectral", "noaa_dav_imagery_n", "NOAA Digital Coast: coastal aerial imagery collections covering the area", "noaa_dav"),
    ("spectral", "uavsar_sar_backscatter", "UAVSAR: airborne L-band polarimetric radar backscatter", "uavsar_asf"),
    ("quality", "uavsar_incidence_deg", "Radar QC: per-pixel incidence angle raster listed with each scene", "uavsar_asf"),
    # --- drone (S2) ---
    ("spectral", "oam_uav_rgb_dn", "OpenAerialMap drone imagery: colour orthomosaic", "oam"),
    ("spectral", "geonadir_ortho_dn", "GeoNadir drone imagery: orthomosaic rasters", "geonadir"),
    # --- hyperspectral and other spectral satellites (S3) ---
    ("spectral", "emit_reflectance", "EMIT imaging spectrometer: surface reflectance", "emit"),
    ("quality", "emit_cloud_cover_scene_pct", "Scene QC: cloud cover of the granule, percent", "emit"),
    ("quality", "emit_sun_zenith_deg", "Scene QC: solar zenith angle", "emit"),
    ("quality", "emit_sun_azimuth_deg", "Scene QC: solar azimuth angle", "emit"),
    ("spectral", "aviris_reflectance", "AVIRIS airborne imaging spectrometer: surface reflectance by flight line", "aviris"),
    ("spectral", "pace_reflectance", "PACE ocean colour instrument: land surface reflectance", "pace_oci"),
    ("quality", "pace_cloud_cover_scene_pct", "Scene QC: cloud cover of the swath, percent", "pace_oci"),
    ("spectral", "enmap_reflectance", "EnMAP imaging spectrometer: surface reflectance at 30 m", "enmap"),
    ("quality", "enmap_off_nadir_across_deg", "Scene QC: across-track off-nadir angle, signed", "enmap"),
    ("quality", "enmap_off_nadir_along_deg", "Scene QC: along-track off-nadir angle, signed", "enmap"),
    ("quality", "enmap_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "enmap"),
    ("quality", "enmap_cloud_cover_scene_pct", "Scene QC: cloud cover of the scene, percent", "enmap"),
    ("quality", "enmap_overall_quality", "Scene QC: overall quality flag from the product metadata", "enmap"),
    ("spectral", "desis_reflectance", "DESIS imaging spectrometer: surface reflectance at 30 m", "desis"),
    ("quality", "desis_incidence_deg", "Scene QC: scene incidence angle", "desis"),
    ("quality", "desis_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "desis"),
    ("quality", "desis_cloud_cover_scene_pct", "Scene QC: cloud cover of the scene, percent", "desis"),
    ("quality", "desis_geometric_accuracy_m", "Scene QC: eastern and northern geometric accuracy, metres", "desis"),
    # --- open commercial imagery (S4) ---
    ("spectral", "planet_reflectance", "Planet open imagery: multispectral reflectance", "planet_open"),
    ("spectral", "planet_hyperspec_reflectance", "Planet Tanager open scenes: hyperspectral reflectance", "planet_open", "S3"),
    ("quality", "planet_off_nadir_deg", "Scene QC: off-nadir angle", "planet_open"),
    ("quality", "planet_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "planet_open"),
    ("quality", "planet_cloud_cover_scene_pct", "Scene QC: cloud cover of the scene, percent", "planet_open"),
    ("quality", "planet_quality_category", "Scene QC: Planet quality category (standard or test)", "planet_open"),
    ("spectral", "maxar_reflectance", "Maxar open data: analysis-ready multispectral imagery", "maxar_open"),
    ("quality", "maxar_off_nadir_deg", "Scene QC: off-nadir angle", "maxar_open"),
    ("quality", "maxar_incidence_deg", "Scene QC: incidence angle", "maxar_open"),
    ("quality", "maxar_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "maxar_open"),
    ("quality", "maxar_cloud_cover_scene_pct", "Scene QC: cloud cover of the tile, percent", "maxar_open"),
    ("spectral", "satl_reflectance", "Satellogic EarthView: multispectral reflectance", "satellogic_earthview"),
    ("quality", "satl_off_nadir_deg", "Scene QC: off-nadir angle", "satellogic_earthview"),
    ("quality", "satl_sun_elevation_deg", "Scene QC: sun elevation above the horizon", "satellogic_earthview"),
    ("spectral", "umbra_sar_backscatter", "Umbra open radar: X-band backscatter", "umbra_open"),
    ("quality", "umbra_incidence_deg", "Radar QC: incidence angle", "umbra_open"),
    ("spectral", "capella_sar_backscatter", "Capella open radar: X-band backscatter", "capella_open"),
    ("quality", "capella_incidence_deg", "Radar QC: incidence angle", "capella_open"),
    ("quality", "capella_look_angle_deg", "Radar QC: look angle, the off-nadir equivalent", "capella_open"),
    ("spectral", "iceye_sar_backscatter", "ICEYE open radar: X-band backscatter", "iceye_open"),
    ("quality", "iceye_off_nadir_deg", "Radar QC: off-nadir angle", "iceye_open"),
    ("quality", "iceye_incidence_deg", "Radar QC: incidence angle", "iceye_open"),
    # --- zoning and land designation (S6) ---
    ("socio-economic", "nza_zone_code", "Zoning atlas: district code and name", "nza"),
    ("socio-economic", "nza_housing_treatment", "Zoning atlas: how 1 to 4 family housing is treated (by right, hearing, prohibited)", "nza"),
    ("socio-economic", "nza_min_lot_acres", "Zoning atlas: minimum lot size, acres", "nza"),
    ("socio-economic", "nza_parking_required_flag", "Zoning atlas: parking minimum applies", "nza"),
    ("socio-economic", "nza_height_cap_flag", "Zoning atlas: height cap applies", "nza"),
    ("quality", "nza_snapshot_date", "Registry QC: date the district record was created", "nza"),
    ("socio-economic", "padus_designation", "Protected areas: designation category of the land", "padus"),
    ("socio-economic", "padus_gap_status", "Protected areas: GAP status code 1 to 4", "padus"),
    ("socio-economic", "padus_public_access", "Protected areas: public access class", "padus"),
    ("socio-economic", "padus_iucn_category", "Protected areas: IUCN management category", "padus"),
    ("quality", "padus_source_date", "Registry QC: source date of the polygon", "padus"),
    ("socio-economic", "bcalr_status", "Agricultural land reserve: ALR or non-ALR status", "bc_alr"),
    ("socio-economic", "bcalr_polygon_km2", "Agricultural land reserve: polygon area, square kilometres", "bc_alr"),
    ("infrastructure", "urbanatlas_land_use_class", "Urban Atlas land use: class of the mapped polygon (artificial surfaces, roads, water)", "eu_urban_atlas"),
    ("quality", "urbanatlas_snapshot_date", "Registry QC: production date of the polygon", "eu_urban_atlas"),
    ("socio-economic", "vanzone_district_code", "Vancouver zoning: district code", "vancouver_zoning"),
    ("socio-economic", "vanzone_category", "Vancouver zoning: zone category", "vancouver_zoning"),
    ("quality", "vanzone_snapshot_date", "Registry QC: date the dataset was last modified", "vancouver_zoning"),
    ("socio-economic", "torzone_zone_code", "Toronto zoning: by-law zone code", "toronto_zoning"),
    ("socio-economic", "torzone_fsi_ratio", "Toronto zoning: total floor space index", "toronto_zoning"),
    ("socio-economic", "torzone_coverage_pct", "Toronto zoning: maximum lot coverage, percent", "toronto_zoning"),
    ("quality", "torzone_snapshot_date", "Registry QC: date the package was last modified", "toronto_zoning"),
    ("socio-economic", "calzone_land_use_code", "Calgary land use: district code", "calgary_land_use"),
    ("socio-economic", "calzone_major_class", "Calgary land use: major class of the district", "calgary_land_use"),
    ("socio-economic", "calzone_far_ratio", "Calgary land use: floor area ratio limit", "calgary_land_use"),
    ("quality", "calzone_snapshot_date", "Registry QC: date the rows were last updated", "calgary_land_use"),
    # --- water (S7) ---
    ("water bodies", "usgs_discharge_cfs", "Stream gauge: latest discharge, cubic feet per second", "usgs_waterdata"),
    ("water bodies", "usgs_gage_height_ft", "Stream gauge: latest gage height, feet", "usgs_waterdata"),
    ("water bodies", "usgs_drainage_area_mi2", "Stream gauge: drainage area, square miles", "usgs_waterdata"),
    ("quality", "usgs_approval_status", "Gauge QC: approved or provisional status of the reading", "usgs_waterdata"),
    ("quality", "usgs_station_distance_km", "Gauge QC: distance to the nearest stream gauge, kilometres", "usgs_waterdata"),
    ("water bodies", "hydat_discharge_m3s", "Hydrometric gauge: latest discharge, cubic metres per second", "eccc_hydrometric"),
    ("water bodies", "hydat_level_m", "Hydrometric gauge: latest water level, metres", "eccc_hydrometric"),
    ("water bodies", "hydat_drainage_area_km2", "Hydrometric gauge: drainage area, square kilometres", "eccc_hydrometric"),
    ("quality", "hydat_station_distance_km", "Gauge QC: distance to the nearest active gauge, kilometres", "eccc_hydrometric"),
    ("quality", "hydat_daily_record_n", "Gauge QC: number of daily-mean records in the archive", "eccc_hydrometric"),
    ("water bodies", "hydrorivers_discharge_m3s", "Modelled river network: long-term mean discharge, cubic metres per second", "hydrorivers"),
    ("water bodies", "hydrorivers_upland_area_km2", "Modelled river network: upstream drainage area, square kilometres", "hydrorivers"),
    ("water bodies", "hydrorivers_strahler_order", "Modelled river network: Strahler stream order", "hydrorivers"),
    ("water bodies", "hydrorivers_nearest_km", "Modelled river network: distance to the nearest river, kilometres", "hydrorivers"),
    ("water bodies", "nhdhr_mean_flow_cfs", "Hydro network: mean annual flow, cubic feet per second", "nhdplus_hr"),
    ("water bodies", "nhdhr_stream_order", "Hydro network: stream order", "nhdplus_hr"),
    ("water bodies", "nhdhr_drainage_area_km2", "Hydro network: total upstream drainage area, square kilometres", "nhdplus_hr"),
    ("water bodies", "nhdhr_slope_frac", "Hydro network: channel slope", "nhdplus_hr"),
    ("quality", "nhdhr_feature_date", "Registry QC: date of the flowline feature", "nhdplus_hr"),
    ("water bodies", "nhn_permanency", "Canadian hydro network: permanent or intermittent watercourse", "nrcan_nhn"),
    ("water bodies", "nhn_water_type", "Canadian hydro network: watercourse or waterbody type", "nrcan_nhn"),
    ("quality", "nhn_survey_year", "Registry QC: source survey year of the feature", "nrcan_nhn"),
    ("quality", "nhn_horiz_accuracy_m", "Registry QC: horizontal position accuracy of the feature, metres", "nrcan_nhn"),
    # --- climate (S8) ---
    ("climate", "eccc_tmax_c", "Canadian station climate: daily maximum temperature, degrees C", "eccc_climate"),
    ("climate", "eccc_tmin_c", "Canadian station climate: daily minimum temperature, degrees C", "eccc_climate"),
    ("climate", "eccc_precip_mm", "Canadian station climate: daily total precipitation, millimetres", "eccc_climate"),
    ("quality", "eccc_station_distance_km", "Station QC: distance to the nearest climate station, kilometres", "eccc_climate"),
    ("quality", "eccc_record_completeness_pct", "Station QC: share of days with a non-null value, percent", "eccc_climate"),
    ("climate", "ghcnd_tmax_c", "Station climate: daily maximum temperature, degrees C", "ghcn_daily"),
    ("climate", "ghcnd_tmin_c", "Station climate: daily minimum temperature, degrees C", "ghcn_daily"),
    ("climate", "ghcnd_prcp_mm", "Station climate: daily precipitation, millimetres", "ghcn_daily"),
    ("quality", "ghcnd_station_distance_km", "Station QC: distance to the nearest station, kilometres", "ghcn_daily"),
    ("quality", "ghcnd_coverage_pct", "Station QC: per-variable data coverage over the record, percent", "ghcn_daily"),
    ("climate", "daymet_tmax_c", "Daily climate: maximum temperature, degrees C", "daymet"),
    ("climate", "daymet_tmin_c", "Daily climate: minimum temperature, degrees C", "daymet"),
    ("climate", "daymet_prcp_mm", "Daily climate: precipitation, millimetres", "daymet"),
    ("climate", "daymet_srad_wm2", "Daily climate: incident shortwave radiation, watts per square metre", "daymet"),
    ("climate", "daymet_swe_kgm2", "Daily climate: snow water equivalent, kilograms per square metre", "daymet"),
    ("climate", "daymet_vp_pa", "Daily climate: water vapour pressure, pascals", "daymet"),
    ("climate", "terraclim_tmax_c", "Monthly climate: maximum temperature, degrees C", "terraclimate"),
    ("climate", "terraclim_ppt_mm", "Monthly climate: precipitation, millimetres", "terraclimate"),
    ("climate", "terraclim_pet_mm", "Monthly climate: potential evapotranspiration, millimetres", "terraclimate"),
    ("climate", "terraclim_def_mm", "Monthly climate: climatic water deficit, millimetres", "terraclimate"),
    ("climate", "terraclim_soil_mm", "Monthly climate: soil moisture, millimetres", "terraclimate"),
    ("climate", "terraclim_swe_mm", "Monthly climate: snow water equivalent, millimetres", "terraclimate"),
    ("climate", "chirps_precip_mm", "Gridded precipitation: monthly rainfall from satellite and gauges, millimetres", "chirps"),
    # --- ground-level cameras (S9) ---
    ("infrastructure", "panoramax_image_n", "Street-level imagery: Panoramax images in the area", "panoramax"),
    ("quality", "panoramax_camera_pitch_deg", "Camera QC: pitch of the camera", "panoramax"),
    ("quality", "panoramax_camera_heading_deg", "Camera QC: heading of the camera", "panoramax"),
    ("quality", "panoramax_gps_accuracy_m", "Camera QC: horizontal accuracy of the capture position, metres", "panoramax"),
    ("infrastructure", "drivebc_webcam_n", "Highway webcams: DriveBC cameras in the area", "drivebc_webcams"),
    ("quality", "drivebc_camera_heading", "Camera QC: compass direction the camera faces", "drivebc_webcams"),
    ("quality", "drivebc_snapshot_date", "Camera QC: time of the latest frame", "drivebc_webcams"),
    ("macrobiology", "phenocam_gcc", "Phenology camera: green chromatic coordinate of the canopy", "phenocam"),
    ("quality", "phenocam_camera_heading", "Camera QC: compass direction the camera faces", "phenocam"),
    ("quality", "phenocam_missing_data_pct", "Camera QC: share of missing days in the ROI series, percent", "phenocam"),
    ("quality", "phenocam_station_distance_km", "Camera QC: distance to the nearest camera, kilometres", "phenocam"),
    ("infrastructure", "wikimedia_photo_n", "Geotagged photos: Wikimedia Commons files in the area", "wikimedia_commons"),
    ("quality", "wikimedia_camera_heading_deg", "Camera QC: EXIF image direction when present", "wikimedia_commons"),
    ("macrobiology", "inat_observation_n", "Species photos: iNaturalist observations with photos in the area", "inaturalist"),
    ("quality", "inat_gps_accuracy_m", "Photo QC: positional accuracy of the observation, metres", "inaturalist"),
    ("quality", "inat_quality_grade", "Photo QC: community quality grade of the observation", "inaturalist"),
    ("macrobiology", "gbifmedia_image_n", "Species photos: GBIF occurrences with still images in the area", "gbif_media"),
    ("quality", "gbifmedia_coordinate_uncertainty_m", "Photo QC: coordinate uncertainty of the occurrence, metres", "gbif_media"),
    ("infrastructure", "geograph_photo_n", "Geotagged photos: Geograph images in the area (UK and Ireland)", "geograph"),
]

HEADER = ["family", "feature", "description", "source", "source_type", "source_url", "licence", "gap"]


def build():
    out, seen = [], set()
    for row in ROWS:
        family, feature, description, source = row[:4]
        stype, url, licence, gap = SOURCES[source]
        gap = row[4] if len(row) > 4 else gap
        assert family in FAMILIES, family
        assert stype in TYPES, stype
        assert feature not in seen, feature
        seen.add(feature)
        out.append([family, feature, description, source, stype, url, licence, gap])
    return out


if __name__ == "__main__":
    rows = build()
    unused = set(SOURCES) - {r[3] for r in rows}
    assert not unused, unused
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    print(len(rows), "rows,", len({r[3] for r in rows}), "sources")

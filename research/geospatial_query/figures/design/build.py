"""Build the design artifact: POC features by family, the metasmith DAG, injected into template.html."""

import csv
from dataclasses import replace
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from metasmith.models.dag_draw import Label, render_svg
from metasmith.models.dag_renderer import DARK, LIGHT, NodeKind
from metasmith.models.dag_layout import layout

FAMILIES = [
    "Socio-economic", "Infrastructure & industry", "Hazards", "Macrobiology", "Geology",
    "Microbiology & health", "Climate", "Spectral", "Water bodies", "Latent",
]

BLURBS = [
    "People, money, movement and tenure: census, population, commuting, parcels.",
    "What people build and run: buildings, roads, rail, power, pipelines, mines.",
    "Things that can hurt: air quality, contamination, toxic releases, earthquakes.",
    "Visible life: land cover and change, biomass, crops, vegetation, species.",
    "The solid Earth: bedrock, surficial geology, elevation, radiometrics, permafrost.",
    "Human health and microbes: disease and wastewater surveillance, clinics, sequencing.",
    "Atmospheric and seasonal state: reanalysis climatology and sea ice.",
    "Raw sensor pixels: Sentinel-2 optical, Sentinel-1 and PALSAR radar, Landsat thermal.",
    "Liquid water in lakes, rivers, oceans and aquifers.",
    "Embeddings and other high-dimensional products, read by fitting a model.",
]

# POC slot -> family, under the rules in reports/layer_families.md
SLOT_FAMILY = {
    "census_demography": 0, "mobility_flows": 0, "parcels_cadastre": 0, "population_gridded": 0,
    "property_assessment": 0, "ground_level_imagery": 1, "infrastructure_osm": 1, "crop_type_ca": 3, "indigenous_lands": 0, "crown_land": 0, "gazetteer": 0,
    "urban_extent": 1, "addresses": 1, "cell_towers": 1, "industrial_facilities": 1,
    "mines_producing": 1, "pipelines": 1, "power_plants": 1, "railways": 1, "transmission_lines": 1,
    "air_quality_modelled": 2, "air_quality_monitors": 2, "contaminated_sites": 2,
    "emissions_releases": 2, "facility_compliance": 2, "earthquake_catalogue": 2, "water_quality": 2,
    "biomass": 3, "crop_type_us": 3, "field_boundaries": 3, "forest_change": 3, "land_cover": 3,
    "land_cover_ca": 3, "species_occurrence": 3, "vegetation_timeseries": 3,
    "bathymetry": 4, "bedrock_geology": 4, "dem_medium_res": 4, "dem_medium_res_ca": 4,
    "gamma_radiometrics": 4, "surficial_geology": 4, "glaciers": 4, "permafrost_extent": 4,
    "healthcare_accessibility": 5, "disease_surveillance": 5, "wastewater_surveillance": 5,
    "geolocated_sequence": 5, "geolocated_sequence_insdc": 5,
    "reanalysis_climate": 6, "sea_ice": 6,
    "optical_multispectral": 7, "sar_backscatter_c": 7, "sar_backscatter_l": 7, "thermal_surface_temp": 7,
    "surface_water_extent": 8,
    "embeddings": 9,
}
PC = "https://planetarycomputer.microsoft.com/dataset/"
OVT = "https://docs.overturemaps.org/guides/"
SOURCE_URLS = {
    "alos_palsar_mosaic": PC + "alos-palsar-mosaic",
    "bc_pmbc_parcel_fabric": "https://catalogue.data.gov.bc.ca/dataset/parcelmap-bc-parcel-fabric",
    "bc_tantalis_crown": "https://catalogue.data.gov.bc.ca/dataset/parcelmap-bc-parcel-fabric",
    "cams_open_meteo": "https://open-meteo.com/en/docs/air-quality-api",
    "cdc_nndss": "https://data.cdc.gov/d/x9gk-5huc",
    "cdc_nwss": "https://data.cdc.gov/d/2ew6-ywp6",
    "cdc_places": "https://data.cdc.gov/d/yjkw-uj5s",
    "clay_v0_embeddings": "https://source.coop/clay/clay-model-v0-embeddings",
    "cop_dem_glo30": PC + "cop-dem-glo-30",
    "eccc_ghgrp": "https://www.canada.ca/en/environment-climate-change/services/climate-change/greenhouse-gas-emissions/facility-reporting.html",
    "eccc_naps": "https://www.canada.ca/en/environment-climate-change/services/air-pollution/monitoring-networks-data/national-air-pollution-program.html",
    "eccc_npri": "https://www.canada.ca/en/services/environment/pollution-waste-management/national-pollutant-release-inventory.html",
    "ena_geo": "https://www.ebi.ac.uk/ena/browser/",
    "epa_aqs_airdata": "https://aqs.epa.gov/aqsweb/airdata/download_files.html",
    "epa_echo": "https://echo.epa.gov/",
    "epa_echo_tri": "https://www.epa.gov/toxics-release-inventory-tri-program",
    "epa_frs_sems": "https://www.epa.gov/superfund/superfund-data-and-reports",
    "era5_open_meteo": "https://open-meteo.com/en/docs/historical-weather-api",
    "esa_worldcover": PC + "esa-worldcover",
    "etopo_2022_30s_bed": "https://www.ncei.noaa.gov/products/etopo-global-relief-model",
    "gbif": "https://www.gbif.org/",
    "ghs_pop_r2023a": "https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php",
    "ghs_smod_r2023a": "https://human-settlement.emergency.copernicus.eu/ghs_smod2023.php",
    "gsc_surficial_1880a": "https://ftp.maps.canada.ca/pub/nrcan_rncan/Surficial-geology_Geologie-des-depots-meubles/",
    "hansen_gfc_v1_13": "https://glad.earthengine.app/view/global-forest-change",
    "hgb": PC + "hgb",
    "io_lulc_annual_v02": PC + "io-lulc-annual-v02",
    "jrc_gsw": "https://global-surface-water.appspot.com/",
    "landsat_c2l2_st": PC + "landsat-c2-l2",
    "lehd_lodes8": "https://lehd.ces.census.gov/data/",
    "macrostrat": "https://macrostrat.org/",
    "mgnify": "https://www.ebi.ac.uk/metagenomics",
    "modis_13q1": PC + "modis-13Q1-061",
    "mrdem_30": "https://search.open.canada.ca/opendata/?search_text=MRDEM",
    "natural_earth_10m": "https://www.naturalearthdata.com/downloads/10m-physical-vectors/",
    "noaa_nsidc_sic_cdr": "https://nsidc.org/data/g02202",
    "nrcan_900a": "https://ftp.maps.canada.ca/pub/nrcan_rncan/Mining-industry_Industrie-miniere/900A_and_top_100/",
    "nrcan_alta": "https://ftp.maps.canada.ca/pub/nrcan_rncan/vector/geobase_al_ta/",
    "nrcan_landcover": PC + "nrcan-landcover",
    "nrcan_permafrost": "https://search.open.canada.ca/opendata/?search_text=permafrost%20atlas%20of%20canada",
    "overture_addresses": OVT + "addresses/",
    "overture_buildings": OVT + "buildings/",
    "overture_communication": OVT + "base/",
    "overture_divisions": OVT + "divisions/",
    "overture_land_use": OVT + "base/",
    "overture_power": OVT + "base/",
    "overture_power_plant": OVT + "base/",
    "overture_transportation": OVT + "transportation/",
    "overture_utility": OVT + "base/",
    "phac_rvdss": "https://health-infobase.canada.ca/respiratory-virus-detections/",
    "phac_wastewater": "https://health-infobase.canada.ca/wastewater/",
    "s2_signature_v1": PC + "sentinel-2-l2a",
    "sentinel1_rtc": PC + "sentinel-1-rtc",
    "sentinel2_l2a": PC + "sentinel-2-l2a",
    "statcan_csd_2016": "https://www12.statcan.gc.ca/census-recensement/2016/index-eng.cfm",
    "statcan_dwelling_value": "https://www12.statcan.gc.ca/census-recensement/2016/index-eng.cfm",
    "statcan_odhf": "https://www.statcan.gc.ca/en/lode/databases/odhf",
    "statcan_wds_popest": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710015501",
    "tbs_fcsi": "https://www.tbs-sct.canada.ca/fcsi-rscf/home-accueil-eng.aspx",
    "tigerweb_aiannh": "https://tigerweb.geo.census.gov/",
    "tigerweb_blocks2020": "https://tigerweb.geo.census.gov/",
    "usda_cdl": PC + "usda-cdl",
    "usda_csb_fiboa": "https://source.coop/fiboa/us-usda-cropland",
    "usgs_fdsn": "https://earthquake.usgs.gov/fdsnws/event/1/",
    "usgs_mineplant": "https://mrdata.usgs.gov/mineplant/",
    "usgs_namrad": "https://mrdata.usgs.gov/radiometric/",
    "wikidata_sparql": "https://query.wikidata.org/",
    "wqp": "https://www.waterqualitydata.us/",
    "wri_gppd": "https://datasets.wri.org/dataset/globalpowerplantdatabase",
}
DROPPED_SOURCES = {"alphaearth_v1_annual"}
def licence_tier(licence: str) -> str:
    if "ODbL" in licence or "-SA" in licence:
        return "share-alike"
    if "-NC" in licence:
        return "noncommercial"
    if "EULA" in licence:
        return "restricted"
    return "permissive"


QA_TOKENS = ("control", "bbox_pad", "sample_pad", "skipped")

TOKENS = {
    "n": "count", "frac": "fraction", "pct": "%", "km": "km", "km2": "km²", "m": "m", "mm": "mm",
    "ha": "ha", "c": "°C", "db": "dB", "ppb": "ppb", "ppm": "ppm", "ugm3": "µg/m³", "mgha": "Mg/ha",
    "kg": "kg", "kt": "kt", "mw": "MW", "cad": "CAD", "ma": "Ma", "p10": "10th percentile",
    "p90": "90th percentile", "p95": "95th percentile", "std": "std dev", "px": "pixels",
    "elev": "elevation", "aoi": "AOI", "ytd": "year to date", "emb": "embedding", "uid": "id",
    "csd": "census subdivision", "cma": "metro area", "co2e": "CO₂e", "lst": "surface temperature",
    "ndvi": "NDVI", "aod550": "AOD 550 nm", "sic": "sea ice concentration", "vv": "VV", "hh": "HH",
    "hv": "HV", "fips": "FIPS", "mag": "magnitude", "eq": "earthquakes",
}


def humanise(text: str) -> str:
    return text.replace("_", " ").strip()


def describe(feature: str, slot: str) -> str:
    parts = feature.split("_")
    words = [TOKENS.get(p, p) for p in parts[1:]] if len(parts) > 1 else parts
    phrase = re.sub(r"\s+", " ", " ".join(words)).strip()
    return f"{humanise(slot).capitalize()}: {phrase}"


def features_by_family(long_csv: Path) -> list[list[dict]]:
    seen: set[str] = set()
    out: list[list[dict]] = [[] for _ in FAMILIES]
    with long_csv.open() as fh:
        for r in csv.DictReader(fh):
            name, slot, source = r["feature"], r["slot"], r["source"]
            if name in seen or source in DROPPED_SOURCES or any(t in name for t in QA_TOKENS):
                continue
            seen.add(name)
            out[SLOT_FAMILY[slot]].append(
                {"name": name, "description": describe(name, slot), "source": source, "layer": slot,
                 "licence": licence_tier(r["licence"]), "url": SOURCE_URLS[source]}
            )
    for fam in out:
        fam.sort(key=lambda f: (f["layer"], f["name"]))
    return out


FAMILY_NAMES = {
    "socio-economic": "Socio-economic", "infrastructure": "Infrastructure & industry", "hazards": "Hazards",
    "macrobiology": "Macrobiology", "geology": "Geology", "public health & microbiology": "Microbiology & health",
    "climate": "Climate", "spectral": "Spectral", "water bodies": "Water bodies", "latent": "Latent",
    "constructor": "Constructor",
}


def related(a: str, b: str) -> bool:
    return a == b or a.startswith(b + "_") or b.startswith(a + "_")


def failed_sources(reports: Path) -> list[dict]:
    """Every catalogue or triage source that did not end up as a working POC adapter, with the stage it stopped at."""
    rows = lambda name: list(csv.DictReader((reports / name).open()))
    registry = rows("source_registry.csv")
    working = [r for r in registry if r["status"] == "working"]
    filled = defaultdict(list)
    for r in working:
        filled[r["slot"]].append(r["source"])
    slot_family = {r["slot"]: FAMILY_NAMES.get(r["family"], r["family"]) for r in rows("layer_slots_triaged.csv")}
    is_working = lambda name: any(related(name, w["source"]) for w in working)
    out = []
    for r in registry:
        if r["status"] == "failing":
            out.append({"stage": "poc-failed", "family": FAMILIES[SLOT_FAMILY[r["slot"]]], "layer": r["slot"],
                        "source": r["source"], "reason": r["reason"], "slot_filled_by": " ".join(filled[r["slot"]])})
    tested = {r["source"] for r in registry}
    for r in rows("triage_results_merged.csv"):
        name = r["candidate"].split(" (")[0]
        tested.add(name)
        if r["reachable"] == "yes" or is_working(name):
            continue
        out.append({"stage": "triage-unreachable" if r["reachable"] == "no" else "triage-unresolved",
                    "family": slot_family.get(r["slot"], ""), "layer": r["slot"], "source": name,
                    "reason": r["blocker"] or r["http_status"] or r["notes"],
                    "slot_filled_by": " ".join(filled[r["slot"]])})
    for r in rows("layer_inventory.csv"):
        if r["family"] == "DROP" or any(related(r["module"], t) for t in tested):
            continue
        out.append({"stage": "not-probed", "family": FAMILY_NAMES.get(r["family"], r["family"]), "layer": "",
                    "source": r["module"], "reason": "catalogued, never probed in the POC", "slot_filled_by": ""})
    return out


def dag_svg(theme) -> str:
    nodes = {"query": NodeKind.GIVEN}
    edges, labels = [], {"query": Label(name="")}
    for i, fam in enumerate(FAMILIES):
        nodes[f"fam{i}"] = NodeKind.TRANSFORM
        labels[f"fam{i}"] = Label(name=fam)
        edges += [("query", f"fam{i}"), (f"fam{i}", "aggregate")]
    nodes["aggregate"] = NodeKind.TRANSFORM
    nodes["feature_set"] = NodeKind.TARGET
    edges.append(("aggregate", "feature_set"))
    labels["aggregate"] = Label(name="aggregate")
    labels["feature_set"] = Label(name="")
    styles = {**theme.styles, NodeKind.TRANSFORM: replace(theme.styles[NodeKind.TRANSFORM], heading=False, weight="normal")}
    return render_svg(
        layout(list(nodes), edges), styles, kinds=nodes, labels=labels,
        font="IBM Plex Mono", font_size=12.5, max_label_chars=48,
        plate=replace(theme.plate, paint_background=False),
    )


def vibe_variants() -> None:
    src = (HERE / "vibe.svg").read_text()
    for name, panel, ink in [("light", "#fbfbf8", "#1d2420"), ("dark", "#1b201d", "#e4e8e2")]:
        out = src.replace('fill="#ffffff"', f'fill="{panel}"', 1).replace('fill="#1e1e1e"', f'fill="{ink}"')
        (HERE / f"vibe-{name}.svg").write_text(out)


def main() -> None:
    vibe_variants()
    families = features_by_family(HERE.parents[1] / "reports" / "feature_values_long.csv")
    data = [{"family": f, "blurb": b, "features": feats} for f, b, feats in zip(FAMILIES, BLURBS, families)]
    page = (HERE / "template.html").read_text()
    failed = failed_sources(HERE.parents[1] / "reports")
    page = page.replace("/*FEATURES*/[]", json.dumps(data, ensure_ascii=False))
    page = page.replace("/*FAILED*/[]", json.dumps(failed, ensure_ascii=False))
    page = page.replace("<!--DAG-LIGHT-->", dag_svg(LIGHT)).replace("<!--DAG-DARK-->", dag_svg(DARK))
    (HERE / "index.html").write_text(page)
    for f, feats in zip(FAMILIES, families):
        print(f"{len(feats):4d}  {len({x['source'] for x in feats}):3d}  {f}")
    from collections import Counter
    print(Counter(x["stage"] for x in failed))


if __name__ == "__main__":
    main()

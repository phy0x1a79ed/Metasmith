"""Add a source_type column (right after adapter) to the registry and the long feature table. Safe to re-run."""

import csv
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

SOURCE_TYPES = {
    "satellite", "airborne", "drone", "vehicle", "fixed camera", "handheld",
    "ground station", "field survey", "model", "registry",
}

# Seeded from the "Working adapters by SourceType" table in source_expansion_report.md,
# with its wildcards expanded to the concrete adapters in source_registry.csv.
TYPE_ADAPTERS = {
    "satellite": [
        "sentinel2_l2a", "s2_signature_v1", "landsat_c2l2_st", "sentinel1_rtc", "alos_palsar_mosaic",
        "modis_13q1", "esa_worldcover", "io_lulc_annual_v02", "hansen_gfc_v1_13", "hgb", "nrcan_landcover",
        "usda_cdl", "usda_csb_fiboa", "jrc_gsw", "noaa_nsidc_sic_cdr", "cop_dem_glo30",
        "mrdem_30",  # part lidar
        "aafc_aci",  # crop classification from satellite imagery
    ],
    "airborne": ["usgs_namrad"],
    "ground station": ["eccc_naps", "epa_aqs_airdata", "usgs_fdsn", "wqp"],
    "field survey": [
        "macrostrat", "gsc_surficial_1880a", "gbif", "mgnify", "ena_geo", "cdc_nwss", "phac_wastewater",
    ],
    "model": [
        "era5_open_meteo", "cams_open_meteo", "etopo_2022_30s_bed", "ghs_pop_r2023a", "ghs_smod_r2023a",
        "lehd_lodes8", "cdc_places", "alphaearth_v1_annual", "clay_v0_embeddings",
    ],
    "registry": [
        "overture_addresses", "overture_buildings", "overture_communication", "overture_divisions",
        "overture_land_use", "overture_power", "overture_power_plant", "overture_transportation",
        "overture_utility",
        "epa_echo", "epa_echo_tri", "epa_frs_sems", "eccc_npri", "eccc_ghgrp", "tbs_fcsi", "nrcan_900a",
        "usgs_mineplant", "wri_gppd", "natural_earth_10m", "nrcan_permafrost",
        "statcan_csd_2016", "statcan_wds_popest", "statcan_dwelling_value", "statcan_odhf",
        "tigerweb_blocks2020", "tigerweb_aiannh",
        "bc_pmbc_parcel_fabric", "bc_tantalis_crown", "nrcan_alta", "wikidata_sparql", "cdc_nndss",
        "phac_rvdss",
        "acs5_api",  # survey statistics published as a table
        "donneesquebec_role",  # municipal assessment roll
        "osm_overpass",  # crowd-mapped vector snapshot
    ],
    "vehicle": ["mapillary_kartaview"],  # street-level imagery from vehicle-mounted cameras
}

SOURCE_TYPE = {a: t for t, adapters in TYPE_ADAPTERS.items() for a in adapters}
assert set(TYPE_ADAPTERS) <= SOURCE_TYPES
assert len(SOURCE_TYPE) == sum(map(len, TYPE_ADAPTERS.values())), "adapter listed under two types"


def rewrite(name: str) -> set:
    path = HERE / name
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = reader.fieldnames, list(reader)
    seen = {r["adapter"] for r in rows}
    unmapped = seen - SOURCE_TYPE.keys()
    if unmapped:
        raise SystemExit(f"{name}: adapters with no source_type: {sorted(unmapped)}")
    if name == "source_registry.csv":
        stale = SOURCE_TYPE.keys() - seen
        if stale:
            raise SystemExit(f"mapping names adapters not in {name}: {sorted(stale)}")
    fields = [f for f in fields if f != "source_type"]
    fields.insert(fields.index("adapter") + 1, "source_type")
    for r in rows:
        r["source_type"] = SOURCE_TYPE[r["adapter"]]
    # Write a new file and rename over the old one so a hardlinked original is never edited in place.
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)
    return seen


def main() -> None:
    rewrite("source_registry.csv")
    rewrite("feature_values_long.csv")


if __name__ == "__main__":
    main()

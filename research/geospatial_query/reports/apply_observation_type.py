"""Add an observation_type column (right after adapter) to the registry and the long feature table. Safe to re-run."""

import csv
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

OBSERVATION_TYPES = {"satellite", "aerial", "surface vehicle", "fixed sensor", "crowdsourced", "field sample", "survey", "blended"}

# A modelled or derived product takes the type of its inputs. "blended" marks one built from inputs of several types.
TYPE_ADAPTERS = {
    "satellite": [
        "sentinel2_l2a", "s2_signature_v1", "landsat_c2l2_st", "sentinel1_rtc", "alos_palsar_mosaic",
        "modis_13q1", "esa_worldcover", "io_lulc_annual_v02", "hansen_gfc_v1_13", "hgb", "nrcan_landcover",
        "usda_cdl", "usda_csb_fiboa", "jrc_gsw", "noaa_nsidc_sic_cdr", "cop_dem_glo30", "aafc_aci",
        "alphaearth_v1_annual", "clay_v0_embeddings",
    ],
    "aerial": ["usgs_namrad"],
    "surface vehicle": ["mapillary_kartaview"],
    "fixed sensor": ["eccc_naps", "epa_aqs_airdata", "usgs_fdsn"],
    "field sample": ["mgnify", "ena_geo", "cdc_nwss", "phac_wastewater", "wqp"],
    "crowdsourced": [
        "osm_overpass", "wikidata_sparql", "gbif",
        "overture_communication", "overture_divisions", "overture_land_use", "overture_power",
        "overture_power_plant", "overture_transportation", "overture_utility",
    ],
    "survey": [
        "macrostrat", "gsc_surficial_1880a",
        "cdc_places", "lehd_lodes8", "overture_addresses",
        "epa_echo", "epa_echo_tri", "epa_frs_sems", "eccc_npri", "eccc_ghgrp", "tbs_fcsi", "nrcan_900a",
        "usgs_mineplant", "wri_gppd", "natural_earth_10m", "nrcan_permafrost",
        "statcan_csd_2016", "statcan_wds_popest", "statcan_dwelling_value", "statcan_odhf",
        "tigerweb_blocks2020", "tigerweb_aiannh",
        "bc_pmbc_parcel_fabric", "bc_tantalis_crown", "nrcan_alta", "cdc_nndss", "phac_rvdss",
        "acs5_api", "donneesquebec_role",
    ],
    "blended": [
        "era5_open_meteo", "cams_open_meteo", "etopo_2022_30s_bed", "ghs_pop_r2023a", "ghs_smod_r2023a",
        "mrdem_30", "overture_buildings",
    ],
}

OBSERVATION_TYPE = {a: t for t, adapters in TYPE_ADAPTERS.items() for a in adapters}
assert set(TYPE_ADAPTERS) <= OBSERVATION_TYPES
assert len(OBSERVATION_TYPE) == sum(map(len, TYPE_ADAPTERS.values())), "adapter listed under two types"


def rewrite(name: str) -> set:
    path = HERE / name
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = reader.fieldnames, list(reader)
    seen = {r["adapter"] for r in rows}
    unmapped = seen - OBSERVATION_TYPE.keys()
    if unmapped:
        raise SystemExit(f"{name}: adapters with no observation_type: {sorted(unmapped)}")
    if name == "source_registry.csv":
        stale = OBSERVATION_TYPE.keys() - seen
        if stale:
            raise SystemExit(f"mapping names adapters not in {name}: {sorted(stale)}")
    fields = [f for f in fields if f not in ("source_type", "observation_type")]
    fields.insert(fields.index("adapter") + 1, "observation_type")
    for r in rows:
        r.pop("source_type", None)
        r["observation_type"] = OBSERVATION_TYPE[r["adapter"]]
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

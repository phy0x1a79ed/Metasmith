"""Build the design artifact: POC features by family, the metasmith DAG, injected into template.html."""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from metasmith.models.dag_colour import Colouring
from metasmith.models.dag_draw import Label, Plate, Style, render_svg
from metasmith.models.dag_layout import layout

FAMILIES = [
    "Socio-economic", "Infrastructure & industry", "Hazards", "Macrobiology", "Geology",
    "Public health & microbiology", "Climate", "Spectral", "Water bodies", "Latent",
]

# POC slot -> family, under the rules in reports/layer_families.md
SLOT_FAMILY = {
    "census_demography": 0, "mobility_flows": 0, "parcels_cadastre": 0, "population_gridded": 0,
    "property_assessment": 0, "indigenous_lands": 0, "crown_land": 0, "gazetteer": 0,
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
DROPPED_SOURCES = {"alphaearth_v1_annual"}
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
                {"name": name, "description": describe(name, slot), "source": source, "layer": slot}
            )
    for fam in out:
        fam.sort(key=lambda f: (f["layer"], f["name"]))
    return out


def dag_svg(families: list[list[dict]]) -> str:
    query, agg, out = "query", "aggregate", "feature_set"
    nodes, edges, labels, colours = [query], [], {}, {}
    labels[query] = Label(name="geospatial_query", namespace="aoi")
    for i, (fam, feats) in enumerate(zip(FAMILIES, families)):
        n_src = len({f["source"] for f in feats})
        node = f"fam{i}"
        nodes.append(node)
        edges += [(query, node), (node, agg)]
        labels[node] = Label(name=f"{fam} ×{n_src} → {len(feats)} features", namespace="fetch")
        colours[node] = f"#F{i:05d}"
    nodes += [agg, out]
    edges.append((agg, out))
    labels[agg] = Label(name="aggregate", namespace="gis_layer")
    labels[out] = Label(name="feature_set", namespace="aoi")
    lay = layout(nodes, edges)
    colouring = Colouring(nodes=colours, edges={(a, b): colours[a] for a, b in edges if a in colours})
    style = {None: Style(fill="#FFFFFE", stroke="#111110", text="#111111", muted="#8A8A8A")}
    svg = render_svg(
        lay, style, labels=labels, colour=colouring, font="IBM Plex Mono", font_size=12.5, max_label_chars=48,
        plate=Plate(paint_background=False, edge="#666665"),
    )
    svg = re.sub(r"<\?xml[^>]*>\s*", "", svg)
    for i in range(len(FAMILIES)):
        svg = svg.replace(f"#F{i:05d}", f"var(--f{i + 1})")
    for hexv, var in [("#FFFFFE", "var(--panel)"), ("#111110", "var(--ink)"), ("#111111", "var(--ink)"),
                      ("#8A8A8A", "var(--muted)"), ("#666665", "var(--muted)")]:
        svg = svg.replace(hexv, var)
    # SVG presentation attributes ignore var(); move each colour into a style declaration
    svg = re.sub(r'\b(fill|stroke)="(var\([^)]*\))"', r'style="\1:\2"', svg)
    svg = re.sub(r'style="([^"]*)"\s+style="([^"]*)"', r'style="\1;\2"', svg)
    return svg


def main() -> None:
    families = features_by_family(HERE.parents[1] / "reports" / "feature_values_long.csv")
    data = [{"family": f, "features": feats} for f, feats in zip(FAMILIES, families)]
    page = (HERE / "template.html").read_text()
    page = page.replace("/*FEATURES*/[]", json.dumps(data, ensure_ascii=False))
    page = page.replace("<!--DAG-->", dag_svg(families))
    (HERE / "index.html").write_text(page)
    for f, feats in zip(FAMILIES, families):
        print(f"{len(feats):4d}  {len({x['source'] for x in feats}):3d}  {f}")


if __name__ == "__main__":
    main()

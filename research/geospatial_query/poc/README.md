# AOI → feature set: pilot pipeline

Takes a list of areas of interest (polygons) and returns one provenance-tagged feature set per AOI,
drawn from 74 public open-data sources. No credentials, no API keys, no vendor SDKs — every adapter
is plain HTTPS against a public endpoint.

```
AOI polygons (GeoJSON)  →  74 adapters in parallel  →  feature matrix + coverage matrix + run log
```

**Current scale:** 15 AOIs × 74 adapters = 1 110 fetches in 191 s wall (8 threads), returning
**662 distinct features**, 392–447 per AOI.

## Install and run

```bash
pip install -r requirements.txt
python run_all.py            # AOI_PATH=my_aois.geojson to use your own
python build_outputs.py      # writes the four CSV deliverables
```

`AOI_PATH` must point at a GeoJSON FeatureCollection whose features carry the properties
`aoi_id`, `aoi_class`, `country` (`CA`/`US`), `area_km2` and `tier`. `test_aois.geojson` has 15
examples (farmland, mine and city AOIs in Canada and the US, 0.5–630 km²).

Outputs:

| File | Contents |
|---|---|
| `feature_matrix.csv` | AOI × feature, the modelling-ready table |
| `feature_values_long.csv` | one row per value with source, licence, observation date, native resolution, fill type |
| `coverage_matrix.csv` | AOI × slot, each cell `found` / `unavailable` / `not-attempted` |
| `run_log.csv` | every fetch with status, failure reason and wall time |

## Design

**Slots, not sources.** A *slot* is a semantic layer (`land_cover`, `bedrock_geology`,
`power_plants`); a *source* is one provider that can fill it. Several sources may compete for a
slot, and the same source can fill different slots in different jurisdictions. The registry of
adapters is the asset, not the code around it.

**Absence is declared, never silent.** Every (AOI, source) pair resolves to exactly one of three
states, and all three are written to the output:

- `found` — data returned, with provenance
- `unavailable` — the source was asked and could not answer (HTTP error, network block, auth wall,
  empty window); the verbatim reason is kept
- `not-attempted` — the source does not cover this AOI by construction (a US-only layer for a
  Canadian AOI). Raised as `PermissionError`, recorded, never retried.

**A 200 is not verification.** Every geometry-filtering endpoint was tested against a nonsense
control box in the mid-Pacific; a source returning the same answer for a real AOI and the control is
not filtering and was not shipped. (MGnify returns HTTP 200 and well-formed JSON for unrecognised
query parameters while silently serving the unfiltered catalogue; EPA Envirofacts ignores lat/long
operators and returns byte-identical payloads. Both were caught this way.)

**Fill types.** Every value is labelled `observed`. The design reserves `inferred` (model output,
e.g. an embedding decode) and `analogue` (a value borrowed from an environmentally-matched donor
AOI); neither is implemented here, and neither may ever be silently substituted for an observation.

## Writing an adapter

```python
def _a_mysource(aoi):
    """aoi: dict with aoi_id, country, area_km2, geom (GeoJSON), bbox, centroid"""
    arr = read_window(href, aoi["bbox"], aoi["geom"])        # decimated, AOI-clipped COG read
    return stats(arr, "mysource_band"), {"obs_date": "2024-06-01", "res_m": 30}

ADAPTERS = [("slot_name", "source_id", "family", "CC-BY-4.0", "none", _a_mysource)]
```

Rules: return flat scalars only, globally unique feature names prefixed by source, raise
`PermissionError` for out-of-coverage and any other exception for failure, never return an empty
dict. Drop the module in as `adapters_<name>.py` and add it to `LANES` in `run_all.py`.

Helpers in `pipeline.py`: `read_window` (decimated AOI-clipped read, masks only *declared* nodata),
`stats`, `class_fractions`, `pc_item` (Planetary Computer STAC search with backoff), `pc_sign`.

## Licence tiers

Features carry their source licence so a query can constrain the acceptable set. Across the 69
working adapters: 22 public-domain (US federal), 16 OGL-Canada-2.0, 14 CC-BY-4.0, 8 ODbL-1.0
(OpenStreetMap-derived, **share-alike**), plus BC OGL, CC0, CDLA-Permissive and the Copernicus DEM
EULA. ODbL and share-alike sources are tagged and must not be mixed into a permissively-licensed
derivative without checking.

## Known constraints

- **Admin-aggregate features are not AOI measurements.** CDC NNDSS (state), CDC NWSS (county),
  PHAC (province) and StatCan census attributes (census subdivision) are joined at the publisher's
  jurisdiction, flagged with `res_m='admin:<level>'` and a jurisdiction prefix in the feature name.
- **US income and age structure are missing**: the Census ACS API requires a key, so US demography
  comes from the TIGERweb 2020 decennial counts instead. No key is embedded anywhere.
- **Three slots have no keyless route**: `ground_level_imagery` (Mapillary and KartaView are both
  token-gated), `tailings_facilities` via the Global Tailings Portal (login-gated; a published
  shapefile substitute is used), and NSIDC cryosphere products (Earthdata Login; NOAA-hosted
  equivalents are used).
- **Partial-coverage sources report honestly**: `field_boundaries` is US-only (NASS Crop Sequence
  Boundaries), `embeddings` covers 5 of 15 AOIs (Clay v0 MGRS tiles), `gamma_radiometrics` covers 3
  of 15 (genuine survey gaps in the North American grid), `glaciers` is Natural Earth 1:10M and is
  provisional below ~10 km.
- **Raster features are decimated samples**, capped at 320 px per side (`pipeline.MAXPIX`), not every
  native pixel.
- `projdata/` holds a copy of the PROJ database; it exists only to work around a read-only conda
  share directory and is unnecessary on a normal install.

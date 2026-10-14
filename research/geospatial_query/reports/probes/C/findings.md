# Lane C: records, water and climate (S6, S7, S8)

`probe.py` reproduces `C_probes.csv` (19 rows) in about 8 min. `C_probe_detail.csv` holds per-AOI counts and nearest-station distances. A station or river counts as a hit inside a stated buffer (25 or 50 km). Zoning, ALR and PAD-US use the strict AOI bbox. Every row except Regrid passed a control and a differential count. No source carries an off-nadir field.

Large downloads (HydroRIVERS 66 MB, CHIRPS v2 14 MB, NZA tiles) are cached outside the repo. `probe.py` re-downloads them.

## S6. Zoning and land use

| Source | AOI hits | Notes |
|---|---|---|
| National Zoning Atlas vector tiles | 2/15 (Detroit, Bingham) | district code, housing treatment, parking, height cap, minimum lot. Layers `zoningdistricts,zoningdistrictslices`. `nza_merged` is only a basemap. **CAUTION** its terms bar download without written permission |
| Toronto open data | 2/15 | no server-side spatial filter. Intersect locally |
| Vancouver, Calgary open data | 0/15 (the cities are not test AOIs) | spatial filter confirmed |
| BC ALR WFS | 2/15 (both HVC AOIs) | |
| PAD-US | 1/15 (Detroit) | protected land, not zoning |
| EU Urban Atlas | 0/15 is coverage | a Paris control returns 134 polygons |
| Regrid | — | 401 without a token. Paid |

## S7. Water

| Source | AOI hits | Notes |
|---|---|---|
| ECCC hydrometric (api.weather.gc.ca) | 13/15 within 25 km | sample: South Saskatchewan River at Saskatoon, 28.3 km, drainage 141,200 km², 41,554 daily means |
| USGS Water Data API | 5/15 (US AOIs) | |
| HydroRIVERS v10 | 13/15 | one schema for both countries: stream order, mean discharge, upstream area. A 66 MB download, not an API |
| NHDPlus HR | 8/15 | none at the prairie, BC or Montreal AOIs |
| NRCan NHN | 9/15, a lower bound | WMS GetFeatureInfo only, 9 sample points per AOI. Carries source year and accuracy per feature |

## S8. Climate

| Source | AOI hits | Notes |
|---|---|---|
| NOAA GHCN-Daily | 15/15 | coverage % and period. Sample: Taber AB, 2.0 km, TMAX coverage 59 %, 1907–2026 |
| Daymet | 15/15 | |
| TerraClimate | 15/15 | **CAUTION** the THREDDS subset returns packed integers. Apply scale 0.1. The ocean control returns the fill value with HTTP 200 |
| CHIRPS v3.0 | 15/15 | precipitation only. v3.0 covers 60S–60N. v2.0 (50S–50N) misses 5 AOIs |
| ECCC daily climate | 13/15 | none at the Iowa and Utah AOIs. Station `LATITUDE`/`LONGITUDE` are integers × 1e7. Use the geometry. Saskatoon Intl A has 0 % non-null precipitation over 2020–2024 |

## Traps

- NCEI search `totalCount` is the whole dataset (132,893), not the bbox count. Its bbox order is north, west, south, east. The data endpoint returns 400 without a station id.

## Best per gap

- S6: National Zoning Atlas (US, pending permission) and municipal open data (Canada, one adapter per city). BC ALR for agricultural reserve.
- S7: ECCC hydrometric plus USGS Water Data for gauges. HydroRIVERS for one cross-border river schema.
- S8: GHCN-Daily for stations. Daymet and TerraClimate for gridded values at every AOI.

The `notes` column in `C_probes.csv` lists the new features each source adds per AOI.

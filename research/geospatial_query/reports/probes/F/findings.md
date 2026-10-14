# Lane F: query ideas (Q2–Q5)

`probe.py` runs all four scripts (about 25 min, mostly Q4) and writes `F_probes.csv`. `probe.py --reuse` rebuilds the CSV from `out/`. The mid-Pacific control returned 0 items everywhere. PC is Planetary Computer, ES is Earth Search.

## Q2. Bands and indices

- One spec (bands red, nir, swir16; indices NDVI, NDWI, NBR) resolves on S2 and Landsat, PC and ES, 15/15 AOIs. The chain: index name, spyndex formula, band common name, asset whose `eo:bands` carries that common name.
- Landsat calls NIR `nir08`. Add a wavelength fallback (N = 760–900 nm). `rededge` is ambiguous on S2 (B05, B06, B07, B8A).
- ES Landsat `item_assets` lack `eo:bands`. Read a real item to resolve.
- Scaling differs per source. PC Landsat has `raster:bands` scale and offset. PC S2 has none: use 1e-4 and offset -0.1 when `s2:processing_baseline` ≥ 04.00. ES S2 declares offset -0.1 but already applied it (`earthsearch:boa_offset_applied=true`).
- NDVI at farm_sk_quarter, July 2023: PC S2 0.5458, ES S2 0.5458, PC Landsat 0.5419.
- ES Landsat assets are requester-pays `s3://`. They cannot be read without AWS credentials.
- Spec: `bands: list[str]`, `indices: list[str]`, `index_params: dict[str, float]` (SAVI, EVI need constants).

## Q3. Periodic time

- One search over 2023–2024, binned client-side, picks the same best-cloud item as a per-period fan-out in 24/24 months and 2/2 "every July".
- Requests over 15 AOIs: PC 15 against 360 for a monthly fan-out. ES needs 40, because it returns 502 above about 200 items per page.
- PC returns reprocessed duplicates: 199 items, 142 distinct datetimes at farm_sk_quarter. Dedupe before binning.
- A bbox across tiles returns several items per period. Pick the best per tile.
- Spec: `period: {start, end, every: "month" | "year" | "<N>d", months?: list[int]}`. "Every July" is `{every: "year", months: [7]}`.

## Q4. QC filters

2023, farm_sk_quarter. N unfiltered, F filtered, notF complement, imp impossible value.

| Catalogue, filter | N | F | notF | imp |
|---|---|---|---|---|
| PC S2 `eo:cloud_cover<10` | 129 | 36 | 93 | 0 |
| PC S2 `s2:mean_solar_zenith<60` | 129 | 80 | 49 | 0 |
| PC Landsat `view:sun_elevation>30` | 108 | 69 | 39 | 0 |
| PC Landsat `view:off_nadir<5` | 108 | 108 | 0 | 0 |
| ES S2 `eo:cloud_cover<10`, `query` extension | 79 | 23 | 56 | 0 |
| ES S2 same filter, CQL2-JSON | 79 | 79 | 79 | 79 |

- PC honours CQL2-JSON and the `query` extension on 15/15 AOIs.
- **CAUTION** ES ignores CQL2-JSON with HTTP 200. Use the `query` extension. Its `/queryables` lists only `eo:cloud_cover`.
- The sun-angle property differs per catalogue: PC S2 has `s2:mean_solar_zenith`, ES S2 has `view:sun_elevation`. The filter needs a property map per collection.
- Landsat `view:off_nadir` is below 1° in every 2023 scene at all 15 AOIs. The filter works but removes nothing.
- Processing-level filters remove nothing: every item has the same level.
- AOI cloud from SCL, 40 scenes April–October 2023: tile cloud < 10 % passes 13, AOI cloud < 10 % passes 17, and they disagree on 8. Example: 2023-07-01 is 8.99 % on the tile and 64.7 % over the AOI. Tile cloud is only a prefilter.
- Spec: `qc: {max_cloud_tile_pct, max_cloud_aoi_pct, max_off_nadir_deg, min_sun_elevation_deg, processing_level}`. Tile fields go to the server. AOI cloud applies after the read.

## Q5. Pointers to the data

- A range GET returns 206 for PC S2 15/15, PC Landsat 15/15, ES S2 14/15 (the miss has only `s3://` jp2 hrefs), ES Landsat 0/15.
- An unsigned PC href returns 409. The SAS token lasts about 44 min. Store the unsigned href and sign at read time.
- Spec: `Observation.assets: dict[str, {href, type, requester_pays, signed_until?}]`, plus `item_id`, `collection` and the STAC self link.

## Sample observation

PC S2 `S2B_MSIL2A_20230731T180919_R084_T13UDT_20230731T233252`: `eo:cloud_cover` 0.29, `s2:cloud_shadow_percentage` 0.19, `s2:thin_cirrus_percentage` 0.20, `s2:mean_solar_zenith` 35.04, `s2:mean_solar_azimuth` 159.34, `s2:processing_baseline` 05.09, `sat:relative_orbit` 84, `s2:mgrs_tile` 13UDT. Off-nadir is in the `granule-metadata` XML only.

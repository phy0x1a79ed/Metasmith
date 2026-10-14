# Lane B: airborne, drone and hyperspectral (S1, S2, S3)

`probe.py` reproduces `B_probes.csv` (41 rows) in about 15 min. `probe.py probe_enmap` re-runs one step and merges it. `samples/` holds one observation per source. `aoi_hits_detail.json` holds per-AOI detail.

## Best per gap

| Gap | Source | AOI hits | Notes |
|---|---|---|---|
| S1 US | Planetary Computer `3dep-lidar-copc` | 3/15 | points. The seven derived-raster collections also hit 3/15 |
| S1 US | USGS WESM, layer 8 of `index.nationalmap.gov/arcgis/rest/services/3DEPElevationIndex/MapServer` | 4/15 (adds Story IA) | quality level per work unit: `ql`, `spec`, `workunit`, `collect_*`. Planetary Computer holds a subset of 3DEP |
| S1 US | NAIP | 4/15 | |
| S1 CA | NRCan HRDEM | 8/15 valid 1 m pixels | absent at both prairie farms and HVC BC. A bbox STAC search overstates it (11/15, mosaic 13/15). Read the COG to confirm |
| S1 | OpenTopography `otCatalog` | — | needs `include_federated=true` (Detroit 0 without, 2 with). The only catalogue that hits Montreal |
| S2 | OpenAerialMap through HOT's STAC (`api.imagery.hotosm.org/stac`), `oam:platform_type=uav` | 1/15 (Toronto stress, 2 scenes, ~3 cm, DJI M3E) | GeoNadir lists 3 for Toronto |
| S3 | EnMAP L2A on the DLR STAC | 15/15, control 0 | the only hyperspectral source with off-nadir fields |
| S3 | EMIT through CMR | 11/15, Canada included | download needs Earthdata login |
| S3 | Planet Tanager open samples | 3/15 | |
| S3 | AVIRIS-NG | 2/15 (Syncrude, oil-sands stress) | |
| S3 | NEON AOP | 0/15 | the nearest site is 41.6 km from Bingham |

## Off-nadir fields

| Source | Field | Where |
|---|---|---|
| EnMAP | `enmap:acrossOffNadirAngle`, `enmap:alongOffNadirAngle` | item property |
| DESIS | `desis:sceneIncidenceAngle` (incidence) | item property |
| Planet Tanager | `view:off_nadir`, 0.2–30.5° over 153 scenes | item property |
| 3DEP COPC | `ScanAngleRank` | per-point dimension in `pc:schemas`, no item summary |
| AVIRIS | none. The flight-line table has altitude, speed and heading | behind Earthdata login, columns from the guide |

None: NAIP, HRDEM, NAPL, WESM, NOAA Digital Coast, OpenTopography, OpenAerialMap, GeoNadir, EMIT, PACE. NEON returns 403 on its file listing from this host.

## Walls

- Login: Earthdata (CMR downloads, AVIRIS flight table), DLR SSO (EnMAP and DESIS assets), OpenTopography API key (401), ASI (PRISMA).
- PRISMA has a portal only, no public catalogue. DroneDB hub is a single-page app with no search API.
- The DLR host returned 502 for about an hour. A rerun after recovery fixed the EnMAP rows.

## Traps

- Planetary Computer 3DEP dates are year-granular. `start_datetime` equals `end_datetime`: 2018-01-01 for a survey flown in April 2017.
- The Windsor ON hits are Detroit River footprint edges: COPC covers 17 % of the AOI, NAIP 54 %.
- OpenAerialMap `/meta` fails the control without `platform=uav`. The mid-Pacific box returns a satellite item. Its `gsd` is in CRS units: a 4326 upload shows 1.9e-07.
- GeoNadir `api.geonadir.com/api/dataset/` answers without auth (8,856 records) but is undocumented. Only `bbox` (lon,lat order) filters. Its announced STAC returns 404. Reuse terms are unknown.
- PACE OCI is global, so the control cannot discriminate (`control_passed` n/a). The AVIRIS flight-line collection in CMR spans the globe, so CMR cannot select lines.

## Second pass

- UAVSAR (S1): ASF search is open, 12,581 scenes, 0/15 AOI hits, control 0. Off-nadir lives in a per-pixel `.inc` incidence raster beside each scene, behind Earthdata login.
- EarthExplorer UAS (S2): unreachable. The M2M host returns 403 to anonymous calls. CMR has no USGS UAS collection. Needs a USGS account.
- Planet Open Canada (S4): one Fort McKay box, nine collections, 1/15 (oil-sands stress, PlanetScope), control 0. CC-BY-SA-4.0. Items carry no `view:off_nadir`.

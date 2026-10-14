# Lane A: satellite QC and tasked imagery (Q1, S4, S5)

`probe.py` reproduces `A_probes.csv` (19 rows). `backfill.py` writes `scene_qc_backfill.csv` (45 rows). The `crawl_*.py` scripts fill `cache/` (263 MB of static catalogs, gitignored). Run them before `probe.py` on a fresh checkout.

## Q1. Backfill of the 45 POC scene records

All 45 ids resolve on Planetary Computer.

| Field | Filled of 45 | Source |
|---|---|---|
| off-nadir or incidence | 45 | S2: mean of 13 per-band `ZENITH_ANGLE` in `MTD_TL.xml` (2.8–10.3°). Landsat: `view:off_nadir` (0 on all 15). S1: `geolocationGrid/incidenceAngle` in the GRD sidecar `annotation/iw-vv.xml`, at the AOI centroid (33.3–44.3°) |
| processing level | 45 | item properties |
| sun elevation, azimuth | 30 | n/a for SAR |
| scene cloud, AOI cloud | 30 | AOI cloud from SCL (S2) and `qa_pixel` (Landsat). n/a for SAR |
| relative orbit | 30 | |
| S1 mid-swath incidence | 15 | `incidenceAngleMidSwath` |

- Sentinel-1 RTC items carry only `vv` and `vh`. The angle comes from the matching GRD scene. The Detroit/Windsor/Essex scene has no `sentinel-1-grd` STAC item (404). Its blob folder exists, so the sidecar URL is built from the RTC asset href.
- AOI cloud differs from tile cloud. Landsat at `mine_us_bingham_ut`: 0.48 % scene, 31 % AOI (shadow 25 %, likely pit terrain shadow).

## S4. Open commercial imagery

| Source | AOI hits | Off-nadir field (item property) | Sample |
|---|---|---|---|
| ICEYE (SAR) | 3/15 | `view:off_nadir`, `view:incidence_angle` | |
| Umbra (SAR) | 2/15 | `view:incidence_angle` | |
| Capella (SAR) | 2/15 | `view:incidence_angle`, `capella:look_angle` (the off-nadir equivalent) | |
| Satellogic EarthView | 1/15 (Bingham) | `view:off_nadir` | 18.8° |
| Planet open STAC | 3/15 (all Tanager, see S3) | `view:off_nadir` | |
| Maxar Open Data | 0/15. A Maui control matched | `view:off_nadir` | 41.2° |
| Planet NICFI | 0/15, tropics only. The pixel token endpoint returns 403 | | |

- Maxar and Satellogic have no search endpoint. Maxar is matched by intersecting its 55 event collections. Satellogic region ids are 384 m UTM tiles in the S3 keys, July–December 2022 only.
- **CAUTION** the STAC roots are incomplete. Umbra links only 2024–2025: list the bucket (7,561 items). ICEYE links 589 of 663 items. Capella has 9,999 per-product items. Take one per acquisition minute (2,313).

## S4. Brokers, without an account

| Broker | Open | Behind 401 | A quote returns |
|---|---|---|---|
| SkyFi | OpenAPI spec | `/archives`, `/pricing` | `offNadirAngle`, `cloudCoveragePercent`, `captureTimestamp`, `priceForOneSquareKm` (USD) |
| UP42 | `GET /collections` (71) | search, `/v2/orders/estimate` | price floors in credits per km² (docs) |
| Sentinel Hub, Copernicus Data Space | collection list | search | no price, no view angle |

## S5. Uncorrected imagery

- Earth Search `sentinel-2-l1c`: 15/15. The cloud filter cuts counts 3–8×. Off-nadir is in the anonymous `metadata.xml` (sample 4.5°). Planetary Computer has no L1C.
- LandsatLook `landsat-c2l1`: 15/15, anonymous search, `view:off_nadir` in item properties. Pixels redirect to the EROS login.

## HLS

Planetary Computer `hls2-l30`, `hls2-s30`: 15/15, cloud filter works. Items carry `eo:cloud_cover` and azimuths only. View zenith is the per-pixel `VZA` asset (1.9°). The scene mean `MEAN_VIEW_ZENITH_ANGLE` is in the public CMR record (3.17°). CMR-STAC (LPCLOUD) also gives 15/15 with sparse properties.

## Best per gap

- Q1: Planetary Computer S2, Landsat, S1 (done). HLS for a harmonised stack.
- S4: ICEYE, Umbra, Capella (open, off-nadir in the item), then Satellogic. Brokers need an account to quote.
- S5: Earth Search Sentinel-2 L1C.

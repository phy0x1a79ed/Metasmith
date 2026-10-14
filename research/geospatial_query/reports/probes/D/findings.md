# Lane D: ground-level cameras (S9)

`probe.py` reproduces `D_probes.csv` (20 rows). It needs an unsandboxed run. `sample_*.json` holds one live observation per working source.

## Working, keyless, control returns 0

| Source | Type | AOI hits | Per-image QC |
|---|---|---|---|
| Panoramax | vehicle | 3/15 on the AOI extent (Toronto core and Toronto stress capped at 1000, Montreal 39) | `view:azimuth`, `pers:pitch`, `pers:roll`, `quality:horizontal_accuracy`, `license`, EXIF make and model, `is_pano` |
| Wikimedia Commons geosearch | handheld | 7/15 | date and licence on every file. Make and model on 23/31, `GPSImgDirection` on 9/31 |
| iNaturalist | handheld | 15/15 | `positional_accuracy`. Obscured records shift up to 27 km |
| GBIF, `mediaType=StillImage` | handheld | 14/15 | mostly iNaturalist copies |
| DriveBC | fixed camera | 0/15 at 1 km (one camera 1.08 km from `mine_hvc_bc`) | BC only, latest frame only |
| PhenoCam | fixed camera | 0/15 at 1 km (nearest 11 km, Ames IA) | greenness (GCC) time series |
| Geograph | handheld | 0/15 is coverage (UK and Ireland). A London control returns 15/15 | HTTP 200 with `outside coverage area` |

The Panoramax datetime filter passes its differential test: a 2030+ range returns 0, August 2025 returns 842.

**CAUTION** Count Panoramax over the AOI extent, not a box at the centroid. The Toronto stress polygon is 25 km wide, and a 2 km centroid box there holds 0 items. GBIF, DriveBC, PhenoCam and AMOS are still counted around the centroid, so they may undercount the large polygons.

## Blocked

- **Mapillary v4.** The POC adapter sends no `access_token`. The graph API returns HTTP 500, code 190 "Invalid OAuth 2.0 Access Token". `tiles.mapillary.com` returns 403 too. A free client token fixes it.
- **KartaView.** Every keyless call returns `apiCode 400 "Restricted access!"` inside HTTP 200 on `api.kartaview.org`. The POC adapter checks only the HTTP status, which is 200, so it misses the error. The docs require OSM OAuth.
- **Google Street View metadata.** REQUEST_DENIED, key-we-lack. With a key it returns `pano_id`, capture month, location and copyright. It has no heading or pitch.
- **Bee Maps (Hivemapper).** Key plus metered credits, paid. 403 without.
- **Windy Webcams.** 403. Needs the `x-windy-api-key` header.
- **511 Ontario, 511 Alberta.** "Invalid Key". A free developer key needs an account. The limit is 10 calls per 60 s.
- **Flickr.** The REST API needs a key. The keyless geo feed ignores lat/lon, so the control fails.
- **AMOS.** `amos.cse.wustl.edu` no longer resolves. Access is a request form for a ~55 TB archive.

## Datasets with no area search

- **OSV-5M.** 5.1M Mapillary images, 259 GB, CC-BY-SA-4.0. Lat/lon and `captured_at` per image. No heading or pitch. Verified live.
- **BDD100K, nuScenes, YFCC100M.** Facts from the web and the AWS registry, not verified live.

## Camera angle as the off-nadir counterpart

`pers:pitch` is 0 on every Toronto core item (983 of 1000 carry it). It is non-zero on 202 of 999 items in the Toronto stress extent (2025-05 to 2026-09, -16 to +13°). The 39 Montreal items carry no pitch. Pitch can filter some surveys, but most of the data is level. `panoramax_pitch_by_aoi.json` holds the distribution. Heading is real: `view:azimuth` is on 2005 of 2039 items. About 30 % of Wikimedia files carry a heading.

## Best per gap

S9: Panoramax first, then Wikimedia Commons. Mapillary gains the most coverage once someone registers a free token.

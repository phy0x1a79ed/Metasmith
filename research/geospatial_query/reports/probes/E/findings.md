# Lane E: picture to location (R1)

`probe.py` rebuilds `E_probes.csv` (36 rows) from the stage outputs. `probe.py --rerun` re-runs every stage, which takes hours on CPU. `.gitignore` excludes `models/` (43 GB), `images/` and `orig/`.

## Verdict

Open tools place a photo in the right country for half to two thirds of photos, and within 25 km for 1 in 4 at best. None reached a verified street-level fix end to end (0/50). Exact placement worked only when the search area was handed to it.

## Env

- `mamba create -n geoloc python=3.11`. Then pip: torch and torchvision from the CPU index, `geoclip transformers accelerate diff-plonk hydra-core omegaconf peft pyproj opencv-python-headless kornia exifread`, and `git+https://github.com/cvg/LightGlue`.
- `env.sh` sets `HF_HOME` and `TORCH_HOME` to `models/`. The osv5m and G3 clones also live there. G3's `.to('cuda')` is patched to the input device.

## Test set

`testset.csv`: 50 CC or PD photos. 42 from Commons geosearch (12 AOI centroids, 12 world cities), 8 from Panoramax (360° frames dropped). 30 are near AOIs, 20 worldwide, 25 in Canada. Thumbnails are 640 px, re-saved without EXIF.

**CAUTION** the set is easy in places and hard in others:
- 5 are ISS or ASTER overhead frames. The `ground` subset in `scores.csv` drops them.
- 10 come from Flickr and may be in the MP-16 or YFCC training sets. The `noflickr` subset keeps the same ranking.
- A Commons coordinate can mark the subject, not the camera.
- Many photos are not road scenes.

## Scores

Error in km. "Within" columns are % of photos.

| Model | n | median | p25 | ≤1 | ≤25 | ≤200 | ≤750 | ≤2500 | country % |
|---|---|---|---|---|---|---|---|---|---|
| StreetCLIP, flat 7402-city labels | 50 | 803 | 80 | 4 | 24 | 28 | 46 | 68 | 68 |
| StreetCLIP, country then city | 50 | 976 | 203 | 4 | 18 | 26 | 44 | 60 | 56 |
| StreetCLIP, country only | 50 | 2520 | 958 | 0 | 0 | 4 | 18 | 48 | 56 |
| GeoCLIP | 50 | 1250 | 402 | 4 | 8 | 12 | 46 | 60 | 48 |
| OSV-5M baseline | 50 | 2808 | 731 | 0 | 6 | 6 | 26 | 46 | 28 |
| PLONK_YFCC | 50 | 1358 | 393 | 2 | 14 | 20 | 44 | 62 | 34 |
| PLONK_OSV_5M | 50 | 878 | 182 | 0 | 0 | 28 | 46 | 60 | 48 |
| PLONK_iNaturalist | 50 | 3999 | 2149 | 0 | 0 | 2 | 10 | 28 | 20 |
| G3 alignment checkpoint, 34k GeoNames gallery | 50 | 1108 | 299 | 6 | 12 | 16 | 44 | 60 | 50 |
| Qwen2.5-VL-3B, "lat, lon" prompt | 48 | 15313 | 12570 | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen2.5-VL-3B, "N/S E/W" prompt | 50 | 2683 | 603 | 0 | 4 | 6 | 28 | 50 | 24 |
| Geo-R1 7B (first 15 photos) | 15 | 536 | 332 | 7 | 13 | 13 | 53 | 73 | 33 |
| Best community 55-country classifier (SigLIP2) | 50 | 6519 | 2615 | 0 | 0 | 2 | 12 | 18 | 26 |
| Plurality vote of 6 models | 50 | 712 | 284 | 2 | 16 | 24 | 52 | 66 | 60 |

- Every model except PLONK_iNaturalist and the first Qwen prompt beats a label-shuffled null (p < 0.05).
- StreetCLIP flat-city leads at 25 km partly because its label list holds the AOI cities. It is optimistic on the 30 AOI photos.
- Geo-R1 stopped after 15 photos (3–8 min each). On those 15: GeoCLIP median 613 km, G3 491 km, PLONK_YFCC 586 km.
- The Canada share inflates the country hit rates.

## Confidence

- PLONK sample density ranks its own hits best: AUROC 0.86 for error ≤ 200 km. StreetCLIP flat-city 0.76, GeoCLIP 0.64, G3 0.44 (`confidence_check.py`).
- On grey, black and noise images, OSV-5M and PLONK still return a point. GeoCLIP's top probability drops to 0.0002–0.0007, against 0.002–0.13 on real photos (`controls.json`).

## Step zero: EXIF

24/50 originals carry EXIF GPS (Commons 16/42, Panoramax 8/8). It matches the stated coordinate, but the stated coordinate was read from it. Heading is in 12/50, camera model in 45/50.

## Failed or not run

- PIGEON and PIGEOTTO: the authors withhold weights, geocells and data.
- GeoSpy: sells to enterprise and law enforcement. `app.geospy.ai` redirects to a login.
- Picarta: API returns 400 "Incorrect access token". The API is Enterprise-only. The free plan is one search after sign-up.
- Img2Loc, GeoToken, Pinpoint: no weights.
- Public weights, not run: G3 full pipeline (38 GB index plus GPT-4V), GeoRanker (needs G3 candidates), GeoReasoner (Qwen-VL-Chat remote code breaks on transformers 5), GeoVista 7B (too slow on CPU), a fourth country classifier (needs `trust_remote_code`).
- Mapillary needs a token. KartaView times out.

## Exact placement (visual place recognition)

Method: DINOv2-base GeM retrieval, then SuperPoint + LightGlue with MAGSAC inliers, against Panoramax. No token needed. 360° frames are re-projected to 6 views. Only 7/50 photos have ≥ 5 Panoramax pictures from other sequences within 300 m. Those 7 were the queries.

| Search centre | Retrieval top-1 ≤ 1 km | Best-inlier ref ≤ 1 km | Verified (≥ 40 inliers) |
|---|---|---|---|
| Oracle: 1.5 km disc, 0.8 km off the truth | 6/7 | 7/7 | 1/7 (78 m) |
| GeoCLIP guess, 3 km disc | truth inside the disc 1/7 | 0/7 | 0/7 |
| StreetCLIP city guess, 8 km disc | 2/2 | 1/2 | 0/2 |

Refinement below 1 km is not shown end to end. Two things block it: the coarse guess is 300+ km out for 5 of the 7, and reference density is capped at 900 positions over 2,400–12,000 pictures per disc. Retrieval alone lands within a few hundred metres once the area is right. Geometric verification mostly fails across cameras and seasons.

## Recommended pipeline

1. Read EXIF GPS and accept it.
2. Otherwise run StreetCLIP zero-shot over a city list for the region, plus PLONK_YFCC and PLONK_OSV_5M. Take a plurality vote and keep PLONK density as the confidence. Report a place and a radius, not a point.
3. Where Panoramax or similar has pictures near the guess, run DINOv2 retrieval then LightGlue. Accept at ≥ 40 inliers. Otherwise stop at step 2.
4. Discard an OSV-5M or PLONK point without its confidence. Both answer for blank images.

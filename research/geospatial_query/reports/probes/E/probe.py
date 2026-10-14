"""Lane E driver: assembles E_probes.csv from the stage outputs (scores.csv, country_acc.csv, exif_check.json,
services.json, vpr/*.json). `probe.py --rerun` re-executes the stages first (hours on CPU; weights cached under models/)."""
import csv, glob, json, os, subprocess, sys
import requests
H = os.path.dirname(os.path.abspath(__file__)); PY = "/home/tony/lib/miniforge3/envs/geoloc/bin/python"; PYQ = "/home/tony/lib/miniforge3/envs/geoquery/bin/python"
ENV = dict(os.environ, HF_HOME=os.path.join(H, "models", "hf"), TORCH_HOME=os.path.join(H, "models", "torch"))
COLS = "gap,candidate,source_type,endpoint,auth,reachable,http_status,aoi_hits,control_passed,observation_unit,quality_fields,off_nadir_field,licence,notes".split(",")

def stage(py, *a):
    subprocess.run([py, os.path.join(H, a[0]), *a[1:]], cwd=H, env=ENV, check=False)

if "--rerun" in sys.argv:
    stage(PYQ, "build_testset.py"); stage(PYQ, "topup_testset.py"); stage(PY, "exif_check.py"); stage(PYQ, "probe_services.py"); stage(PYQ, "vpr_coverage.py")
    stage(PY, "run_geoclip.py"); stage(PY, "run_streetclip.py"); stage(PY, "run_osv5m.py"); stage(PY, "run_g3.py")
    for m in ("PLONK_YFCC", "PLONK_OSV_5M", "PLONK_iNaturalist"): stage(PY, "run_plonk.py", m, "64")
    stage(PY, "run_vlm.py", "Qwen/Qwen2.5-VL-3B-Instruct", "qwen25vl3b", "40", "0")
    ENV["NSEW"] = "1"; stage(PY, "run_vlm.py", "Qwen/Qwen2.5-VL-3B-Instruct", "qwen25vl3b_nsew", "40", "0"); stage(PY, "run_vlm.py", "miniHui/Geo-R1", "geo_r1_7b", "400", "1")
    for c in ("oracle", "model"): stage(PY, "vpr.py", c, "p22", "p04", "p08", "p18", "p27", "p36", "p38")
    stage(PY, "score.py"); stage(PYQ, "country_acc.py")

def probe_url(u):
    try: return requests.get(u, timeout=30, headers={"User-Agent": "geoprobe/0.1"}).status_code
    except Exception: return ""
def hf_licence(repo):
    try:
        d = requests.get(f"https://huggingface.co/api/models/{repo}", timeout=30).json(); c = d.get("cardData", {}); return c.get("license") or (c.get("license_name") and c["license_name"] + " (see LICENSE in repo)") or d.get("license") or [t for t in d.get("tags", []) if t.startswith("license:")][:1] or "not stated on the model card"
    except Exception: return "unknown"

S = {(r["model"], r["subset"]): r for r in csv.DictReader(open(os.path.join(H, "scores.csv")))}
CA = {r["model"]: r for r in csv.DictReader(open(os.path.join(H, "country_acc.csv")))}
SV = json.load(open(os.path.join(H, "services.json"))); EX = json.load(open(os.path.join(H, "exif_check.json")))
NONE_OFFNADIR = "none (the model returns a place, not a camera pitch or heading)"

def model_row(key, name, endpoint, licence, quality, notes, auth="none", status=None):
    a, g = S.get((key, "all")), S.get((key, "ground"))
    if a is None: return None
    n = f"n={a['n']}; median {a['median_km']} km, p25 {a['p25_km']} km; within 1/25/200/750/2500 km = {a['within_1km']}/{a['within_25km']}/{a['within_200km']}/{a['within_750km']}/{a['within_2500km']} %."
    n += f" Ground-level only (n={g['n']}, drops 5 ISS/ASTER overhead frames): median {g['median_km']} km, within 25 km {g['within_25km']} %."
    n += f" Country hit {CA[key]['country_acc_pct']} % (test set is 25/50 Canada)." if key in CA else ""
    n += f" Label-shuffled null median {a['null_median_km']} km, observed beats null p={a['p_median_vs_shuffled']}. " + notes
    return dict(gap="R1", candidate=name, source_type="handheld", endpoint=endpoint, auth=auth, reachable="yes", http_status=status or probe_url(endpoint),
                aoi_hits=f"{a['hit25']}/{a['n']}", control_passed="yes" if float(a["p_median_vs_shuffled"]) < 0.05 else "no", observation_unit="acquisition",
                quality_fields=quality, off_nadir_field=NONE_OFFNADIR, licence=licence, notes=n)

rows = []
g = [e for e in EX if e["has_gps"]]
rows.append(dict(gap="R1", candidate="EXIF GPS read (step zero)", source_type="handheld", endpoint="local: exifread on the original downloads (testset.csv download_url)", auth="none", reachable="yes", http_status="n/a",
    aoi_hits=f"{len(g)}/{len(EX)}", control_passed="n/a", observation_unit="acquisition", quality_fields="GPS GPSLatitude;GPS GPSLongitude;GPS GPSImgDirection;EXIF DateTimeOriginal;Image Model",
    off_nadir_field="GPS GPSImgDirection (EXIF, heading) in %d/50; no pitch in EXIF; Panoramax adds properties.pers:pitch" % sum(e["has_direction"] for e in EX), licence="per photo: CC BY/BY-SA/CC0/public domain (testset.csv)",
    notes="%d/50 originals carry EXIF GPS: Commons %d/42, Panoramax %d/8. Max difference from the stated coordinates %.4f km - but the stated coordinates are themselves read from EXIF for these, so the match is circular; the 26 without EXIF GPS (Commons) carry a hand-set or template coordinate. Re-saved test copies hold no EXIF. Camera model in %d/50, capture time in %d/50." %
    (len(g), sum(e["source"] == "commons" for e in g), sum(e["source"] == "panoramax" for e in g), max(e["err_km"] for e in g), sum(e["has_camera"] for e in EX), sum(e["has_datetime"] for e in EX))))
specs = [
 ("geoclip", "GeoCLIP (VicenteVivan, pip geoclip 1.2.3)", "https://huggingface.co/VicenteVivanco/geoclip-geolocation", "MIT (HF model card VicenteVivanco/geoclip-geolocation)", "top-k GPS with softmax probability over a 100k-point GPS gallery",
  "CPU ~2 s/image unloaded. Top-1 of the 100k gallery; the prediction is always a gallery point, never finer than the gallery spacing."),
 ("streetclip_country", "StreetCLIP zero-shot, country only (geolocal/StreetCLIP)", "https://huggingface.co/geolocal/StreetCLIP", None, "softmax over 237 country labels (Natural Earth 50m + ISO-A2 fallback)",
  "Labels: 237 Natural Earth countries, prompt 'a photo from {country}.'. Predicted point = representative point of the largest polygon, so km error is dominated by country size."),
 ("streetclip_city", "StreetCLIP zero-shot, country then city (geolocal/StreetCLIP)", "https://huggingface.co/geolocal/StreetCLIP", None, "country softmax x city softmax",
  "Stage 2 label set: the 60 most populous GeoNames cities (pop>=15000) of the stage-1 country, prompt 'a photo from {city}, {country}.'. A wrong country caps the result."),
 ("streetclip_flatcity", "StreetCLIP zero-shot, flat 7402-city list (geolocal/StreetCLIP)", "https://huggingface.co/geolocal/StreetCLIP", None, "softmax over 7402 city labels",
  "Labels: 237 countries x up to 60 cities each (7402 labels), no country stage. Best coarse result here, but the label set contains every test AOI city, so it is optimistic for the AOIs."),
 ("osv5m", "OSV-5M baseline (osv5m/baseline, gastruc/osv5m)", "https://huggingface.co/osv5m/baseline", None, "none (regression head returns one GPS point)",
  "CLIP-L/14 DataComp backbone, hybrid classification+regression head, trained on Mapillary street views only, so photos that are not road scenes (indoor, aerial, close-ups) fall outside its training domain."),
 ("g3_align", "G3 geo-alignment checkpoint (Jia-py/G3-checkpoint), GeoNames city gallery", "https://huggingface.co/Jia-py/G3-checkpoint", None, "cosine similarity image-vs-location embedding",
  "Only the public g3.pth alignment model was run, scored against 34162 GeoNames cities (pop>=15000) as the gallery. The full G3 needs its 38 GB FAISS index (g3.index) and GPT-4V prompting for geo-diversification and verification, so those scores are not reproduced. Source patched to run on CPU."),
 ("plonk_yfcc", "PLONK_YFCC (nicolas-dufour, diff-plonk 0.4)", "https://huggingface.co/nicolas-dufour/PLONK_YFCC", None, "64 sampled locations per image; derived confidence = share of samples within 200 km of the densest one",
  "Generative (flow matching on the sphere) over StreetCLIP/DINOv2 features. Point estimate = densest of 64 samples. CPU ~8 s/image."),
 ("plonk_osv_5m", "PLONK_OSV_5M (nicolas-dufour, diff-plonk 0.4)", "https://huggingface.co/nicolas-dufour/PLONK_OSV_5M", None, "64 sampled locations per image; derived confidence = share of samples within 200 km of the densest one",
  "Trained on street views; strongest at 200-750 km, never within 25 km here because the model outputs sample cloud centres rather than gallery places."),
 ("plonk_inaturalist", "PLONK_iNaturalist (nicolas-dufour, diff-plonk 0.4)", "https://huggingface.co/nicolas-dufour/PLONK_iNaturalist", None, "64 sampled locations per image",
  "Trained on species photographs, so run for completeness; not expected to transfer to street scenes."),
 ("qwen25vl3b", "Qwen2.5-VL-3B-Instruct asked for lat, lon (minus-sign prompt)", "https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct", None, "none",
  "General VLM, direct coordinate prompt, greedy. Failed on a prompt artefact: it recognised Tokyo, Mexico City and Chicago but emitted a negative latitude or swapped axes, so the score is worse than the shuffled null. Kept as a recorded failure; see the NSEW row."),
 ("qwen25vl3b_nsew", "Qwen2.5-VL-3B-Instruct asked for lat N/S, lon E/W", "https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct", None, "none",
  "Same model, prompt asks for hemisphere letters. Falls back to New York and Paris when unsure."),
 ("geo_r1_7b", "Geo-R1 7B (miniHui/Geo-R1, Qwen2.5-VL-7B RL-tuned)", "https://huggingface.co/miniHui/Geo-R1", None, "free-text reasoning before the answer",
  "Reasoning VLM, up to 256 new tokens, greedy, CPU bf16. Stopped after 15 parsed photos (p01-p16, 3-8 min each on the shared host), so n is small. On those same 15 photos: Geo-R1 median 536 km / 13 % within 25 km, GeoCLIP 613 km / 7 %, StreetCLIP flat-city 772 km / 20 %, G3-align 491 km / 13 %, PLONK_YFCC 586 km / 13 %: no clear gain from the reasoning tuning here. A first attempt (400-token cap, three other jobs running) took 13.5 min for its first photo and was restarted."),
]
specs.append(("ensemble_vote", "Plurality vote over StreetCLIP flat-city, PLONK_YFCC, GeoCLIP, G3-align, PLONK_OSV_5M, OSV-5M", "local: ensemble.py over preds/*.csv", "inherits the members' licences (CC-BY-NC-4.0 StreetCLIP is the most restrictive)", "agreement count within 300 km (derived)",
              "Not a new model: the prediction with the most neighbours within 300 km among six model outputs. Tests whether disagreement between tools is a usable confidence signal."))
for rid, tag, nm in [("prithivMLmods/GeoGuessr-55", "clf_prithiv_siglip2", "SigLIP2"), ("Jordiett/convnextv2-geoguessr", "clf_jordiett_convnextv2", "ConvNeXt-V2"), ("marcelomoreno26/vit-base-patch-16-384-geoguessr", "clf_moreno_vit", "ViT-B/16-384")]:
    specs.append((tag, f"{rid} (55-country GeoGuessr classifier, {nm})", f"https://huggingface.co/{rid}", None, "softmax over 55 country classes",
                  "Community closed-set classifier over 55 Street View countries; countries outside the 55 cannot be predicted. Predicted point = country representative point, so km error is dominated by country size; read the country hit rate."))
for key, name, ep, lic, q, notes in specs:
    repo = ep.split("huggingface.co/")[1] if "huggingface.co/" in ep else None
    r = model_row(key, name, ep, lic or hf_licence(repo), q, notes, status="n/a" if repo is None else None)
    if r: rows.append(r)

# ---- models whose weights are not public, or public but not runnable here: one row each, with the evidence URL
def blocked(name, endpoint, auth, reach, licence, notes, status=None, quality="n/a"):
    rows.append(dict(gap="R1", candidate=name, source_type="handheld", endpoint=endpoint, auth=auth, reachable=reach, http_status=status if status is not None else probe_url(endpoint),
                     aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition", quality_fields=quality, off_nadir_field=NONE_OFFNADIR, licence=licence, notes=notes))
blocked("PIGEON / PIGEOTTO (Haas et al., CVPR 2024)", SV["pigeon"]["url"], "key-we-lack", "partial", "code only; weights withheld by the authors",
        "Weights are not public. The repository README states: \"" + SV["pigeon"]["quote"] + "\" Project page https://lukashaas.github.io/PIGEON-CVPR24/ says the authors share weights with institutions case by case. Third-party re-creations exist (e.g. huggingface.co/ArjunMehan/pretrained-geolocation-clip-model, unverified) but are not PIGEON.", status=SV["pigeon"]["status"])
blocked("G3 full pipeline (Jia et al., NeurIPS 2024)", "https://huggingface.co/Jia-py/G3-checkpoint", "key-we-lack", "partial", "not stated on the model card",
        "Alignment checkpoint g3.pth is public and is run in the g3_align row. The full pipeline also needs g3.index (37.99 GB retrieval index) and an LMM API (GPT-4V in the paper) for geo-diversification and verification; the repo ships llm_predict.py (OpenAI) and llm_predict_hf.py. Not run: no API key, and the index is larger than the free RAM share on this shared host.")
blocked("GeoRanker (Jia et al., NeurIPS 2025)", "https://github.com/Applied-Machine-Learning-Lab/GeoRanker", "key-we-lack", "partial", "not stated",
        "LoRA checkpoint (Qwen2-VL-7B base) is released in the repo's checkpoints/ folder. It only re-ranks candidate coordinates, and the candidates come from G3-style retrieval (38 GB index) plus GPT-4V, so it is not a stand-alone locator. Not run.")
blocked("GeoReasoner (Li et al., ICML 2024)", "https://huggingface.co/ling1996/GeoReasoner_Models", "none", "partial", "MIT (model card); GeoGuessr/Tuxun-derived data non-commercial",
        "LoRA weights are public (train_loc.zip, train_reason.zip) on top of Qwen-VL-Chat (9.6B, trust_remote_code written for transformers 4.3x). Not run: the remote code does not load on transformers 5 and the 9.6B base would take the hours per 50 images seen with the 7B VLMs here. Stage-2 training data is withheld (Google Street View copyright).")
blocked("Img2Loc (Zhou et al., SIGIR 2024)", "https://www.researchgate.net/publication/382208439_Img2Loc_Revisiting_Image_Geolocalization_using_Multi-modality_Foundation_Models_and_Image-based_Retrieval-Augmented_Generation", "key-we-lack", "no", "n/a",
        "No official code or weights found; the method prompts GPT-4V with retrieved neighbours. github.com/fyhuang/img2loc is an unrelated project. Not run.", status="n/a")
blocked("GeoToken (ICDM 2025)", "https://github.com/NNargesNN/GeoToken", "none", "partial", "not stated",
        "README says training and indexing sections 'will be updated'; no released weights found. Not run.")
blocked("Pinpoint (2026)", "https://arxiv.org/html/2606.04133v1", "none", "partial", "n/a",
        "Per its paper, code is released for academic analysis but trained weights are withheld over misuse risk. Not run.", status=probe_url("https://arxiv.org/html/2606.04133v1"))
blocked("Simon-Kotchou/dinov3-convnext-small-geoguessr-25k-384 (55-country classifier)", "https://huggingface.co/Simon-Kotchou/dinov3-convnext-small-geoguessr-25k-384", "none", "yes", hf_licence("Simon-Kotchou/dinov3-convnext-small-geoguessr-25k-384"),
        "Not run: the model card needs trust_remote_code=True (custom code from the repo). Downloaded repo code is untrusted and was not executed; the three other 55-country classifiers ran.")
blocked("GeoVista-RL-12k-7B (LibraTree)", "https://huggingface.co/LibraTree/GeoVista-RL-12k-7B", "none", "yes", hf_licence("LibraTree/GeoVista-RL-12k-7B"),
        "Public Qwen2.5-VL-7B fine-tune meant to run as an agent with image-zoom and web-search tools. Not run: the same 7B bf16 class as Geo-R1, which ran at about 7 min per image on this shared CPU; the tool loop would add more.")

# ---- hosted services
blocked("GeoSpy / Graylark Raven (geospy.ai)", "https://geospy.ai", "paid", "partial", "proprietary",
        "geospy.ai is a marketing page: 'For Enterprise & Law Enforcement ... Available for qualified government and enterprise organizations. Contact us for licensing and pricing.' app.geospy.ai redirects to %s, a login-gated app. https://geospy.ai/api and https://api.geospy.ai return 404. No public API, no anonymous demo. Not run." % SV["geospy_app"]["final"],
        status=SV["geospy_home"]["status"], quality="n/a (login wall)")
blocked("Picarta (picarta.ai)", "https://api.picarta.ai/v1/geolocalize", "key-we-lack", "partial", "proprietary",
        "POST without a token returns HTTP %s %r. /pricing: Free plan 'To explore Picarta 1 Search' (needs Sign Up), Wallet $15.9 for 20 searches, subscription $49.9-59.9 for 100 searches/month, and 'Picarta API is available to Enterprise accounts only'. Only https://api.picarta.ai/v1/admin1/{country} is public. No account was created, so not run." % (SV["picarta_api_no_token"]["status"], SV["picarta_api_no_token"]["body"]),
        status=SV["picarta_api_no_token"]["status"], quality="top_k candidates with confidence (per the client library; not observed live)")

# ---- visual place recognition
V = {}
for f in sorted(glob.glob(os.path.join(H, "vpr", "*_p*.json"))):
    d = json.load(open(f))
    if os.path.basename(f).startswith("test_run"): continue
    V.setdefault(d["condition"], []).append(d)
def vsum(cond, label, area):
    L = V.get(cond, [])
    if not L: return
    inside = [d for d in L if d["centre_err_km"] <= d.get("search_radius_m", 3000) / 1000]
    acc = [d for d in L if d.get("accepted")]; ok = [d for d in L if d.get("accepted_within_1km")]
    best1 = [d for d in L if d.get("best_ref_err_km", 99) <= 1 and d["n_views"]]
    r1 = [d for d in inside if d.get("retrieval_top1_err_km", 99) <= 1]
    per = "; ".join("%s: %s" % (d["id"], ("no refs" if not d["n_views"] else "ret1 %.2f km, best %d inl @ %.2f km" % (d["retrieval_top1_err_km"], d["best_inliers"], d["best_ref_err_km"]))) for d in L)
    rows.append(dict(gap="R1", candidate="VPR refine: DINOv2-base GeM retrieval + SuperPoint/LightGlue + MAGSAC, Panoramax references (%s)" % label, source_type="handheld",
        endpoint="https://api.panoramax.xyz/api/search?place_position={lon},{lat}&place_distance={a}-{b}&limit=1000", auth="none", reachable="yes", http_status=200,
        aoi_hits="%d/%d" % (len(best1), len(L)), control_passed="n/a", observation_unit="acquisition",
        quality_fields="RANSAC inliers (threshold 40);DINOv2 cosine similarity;pers:yaw;pers:pitch;view:azimuth;quality:horizontal_accuracy (Panoramax item properties)",
        off_nadir_field="properties.pers:pitch (Panoramax item property, camera pitch); properties.view:azimuth", licence="Panoramax pictures CC-BY-SA-4.0 / Licence Ouverte per item",
        notes="aoi_hits = queries whose best-inlier reference lies within 1 km of the true location (not the same as verified). %s %d queries chosen because Panoramax holds >=5 pictures from other collections within 300 m of the true point. True location inside the search disc: %d/%d. Accepted (>=40 inliers): %d; accepted and within 1 km: %d. Global retrieval top-1 within 1 km: %d/%d (inside disc). %s" % (area, len(L), len(inside), len(L), len(acc), len(ok), len(r1), len(inside), per)))
vsum("oracle", "oracle area", "Search disc 1.5 km radius centred 0.8 km from the TRUE location (an ideal coarse stage); up to 900 positions / 1800 views.")
vsum("model", "GeoCLIP guess", "Search disc 3 km radius centred on the GeoCLIP top-1 guess; up to 900 positions / 1800 views.")
vsum("city", "StreetCLIP city guess", "Search disc 8 km radius centred on the StreetCLIP flat-city guess; thinned to 900 positions / 1800 views.")
_T = {r["id"]: r for r in csv.DictReader(open(os.path.join(H, "testset.csv")))}
_cov = [e["id"] for e in json.load(open(os.path.join(H, "vpr_coverage.json"))) if e["n_other_collections"] >= 5]
COVN = len(_cov); COVWHERE = ", ".join(sorted({_T[i]["aoi_id"] for i in _cov}))
rows.append(dict(gap="R1", candidate="Panoramax API (reference imagery for VPR)", source_type="handheld", endpoint="https://api.panoramax.xyz/api/search?place_position={lon},{lat}&place_distance={a}-{b}&limit=1000", auth="none", reachable="yes", http_status=200,
    aoi_hits="%d/50" % COVN, control_passed="n/a", observation_unit="acquisition",
    quality_fields="pers:yaw;pers:pitch;pers:roll;view:azimuth;quality:horizontal_accuracy;panoramax:horizontal_pixel_density;pers:interior_orientation.field_of_view;geovisio:status",
    off_nadir_field="properties.pers:pitch (item property; 0.0 for the GoPro Max 360 seen)", licence="CC-BY-SA-4.0 or Licence Ouverte per item",
    notes=("n/50 = test photos with >=5 Panoramax pictures from other sequences within 300 m of their true location (%d of 50: %s). No token needed. A single annulus query returns <=1000 pictures sorted by distance (5000+ pictures inside 3 km of downtown Toronto). Many items are 360 GoPro Max equirectangular frames that must be re-projected to perspective views before matching." % (COVN, COVWHERE))))
rows.append(dict(gap="R1", candidate="Mapillary API v4 (reference imagery for VPR)", source_type="handheld", endpoint="https://graph.mapillary.com/images?bbox={bbox}&fields=id,geometry", auth="key-we-lack", reachable="partial", http_status=500,
    aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition", quality_fields="n/a (no token)", off_nadir_field="none seen (needs a token to inspect)", licence="CC-BY-SA street imagery; API terms apply",
    notes="Without an access_token the API answers 'Invalid OAuth 2.0 Access Token' (code 190). Not usable without registering an app."))
rows.append(dict(gap="R1", candidate="KartaView / OpenStreetCam API 2.0 (reference imagery for VPR)", source_type="handheld", endpoint="https://api.openstreetcam.org/2.0/photo/?lat={lat}&lng={lon}&radius={m}", auth="none", reachable="partial", http_status=400,
    aoi_hits="0/2", control_passed="n/a", observation_unit="acquisition", quality_fields="n/a (no result returned)", off_nadir_field="none seen", licence="CC-BY-SA",
    notes="Anonymous radius queries at Toronto (100-300 m) and Paris (200 m) returned HTTP 400 apiCode 408 'Query timeout. Narrow your filter'; a bbox query returned 'Restricted access!'. Matches the failing kartaview adapter noted in the brief."))
for nm, ep, lic, n in [("Wikimedia Commons geosearch (test-set source)", "https://commons.wikimedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gsnamespace=6", "per file: CC BY/BY-SA/CC0/PD", "Anonymous, <=500 hits per call. 42 of the 50 test photos. Its coordinates are camera or object positions typed by uploaders; where an EXIF position exists the two agree to 0.1 m, otherwise the coordinate can be the subject's location."),
                       ("Panoramax search (test-set source)", "https://api.panoramax.xyz/api/search?bbox={bbox}&limit=200", "CC-BY-SA-4.0 / Licence Ouverte", "8 of the 50 test photos, one per sequence; 360-degree frames excluded.")]:
    rows.append(dict(gap="R1", candidate=nm, source_type="handheld", endpoint=ep, auth="none", reachable="yes", http_status=200, aoi_hits="n/a", control_passed="n/a", observation_unit="acquisition",
        quality_fields="n/a", off_nadir_field="none", licence=lic, notes=n))

with open(os.path.join(H, "E_probes.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, COLS); w.writeheader(); w.writerows(rows)
print(len(rows), "rows ->", os.path.join(H, "E_probes.csv"))

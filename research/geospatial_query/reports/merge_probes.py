"""Merge the lane probe CSVs (probes/A..F) into gap_source_probes.csv and off_nadir_fields.csv.

Re-runnable: every input CSV is read fresh. Unknown enum values, unmatched candidates in the
backfill, and unresolved classification ambiguities all abort the run.
"""
import re
import sys
from pathlib import Path

import pandas as pd

REPORTS = Path(__file__).resolve().parent
PROBES = REPORTS / "probes"
LANES = list("ABCDEF")
COLS = ["gap", "candidate", "source_type", "endpoint", "auth", "reachable", "http_status", "aoi_hits",
        "control_passed", "observation_unit", "quality_fields", "off_nadir_field", "licence", "notes"]

SOURCE_TYPES = ["satellite", "airborne", "drone", "vehicle", "fixed camera", "handheld",
                "ground station", "field survey", "model", "registry"]
OBS_UNITS = ["acquisition", "composite", "snapshot"]
LOCATIONS = ["item property", "sidecar file", "per-pixel band", "per-point dimension", "quote response", "none"]
ANGLE_KINDS = ["off-nadir", "incidence", "view zenith", "scan angle", "camera pitch", "camera heading", "none"]

SOURCE_TYPE_SYNONYMS = {"fixed_camera": "fixed camera", "fixed-camera": "fixed camera",
                        "ground_station": "ground station", "ground-station": "ground station",
                        "field_survey": "field survey", "field-survey": "field survey",
                        "uav": "drone", "uas": "drone", "plane": "airborne", "aircraft": "airborne",
                        "space": "satellite", "street-level": "vehicle", "street level": "vehicle"}

# Gap R1 (lane E) probes geolocation models; only these rows are imagery sources, typed by the imagery.
R1_IMAGERY_SOURCES = [(r"^Panoramax", "vehicle"), (r"^Mapillary", "vehicle"),
                      (r"^KartaView", "vehicle"), (r"^Wikimedia", "handheld")]


def normalise_source_type(row):
    st = str(row["source_type"]).strip().lower()
    st = SOURCE_TYPE_SYNONYMS.get(st, st)
    if row["gap"] == "R1":
        for pat, typ in R1_IMAGERY_SOURCES:
            if re.match(pat, row["candidate"]):
                return typ
        return "model"
    return st


# ---- off-nadir location rules -------------------------------------------------------------

# Phrases that mention an angle location only to deny it; removed before matching.
NEGATED = [
    r"not in item propert\w*", r"not an item propert\w*",
    r"item properties (?:carry|hold) only[^;]*", r"STAC item properties hold only[^;]*",
    r"not off-nadir",
]
LOCATION_RULES = [
    ("quote response", r"ArchiveResponse|quote response"),
    ("per-point dimension", r"ScanAngleRank|per-point"),
    ("per-pixel band", r"per-pixel|\bVZA\b|\.inc\b"),
    ("sidecar file", r"MTD_TL\.xml|metadata\.xml|annotation[\w/.\-]*\.xml|annotation xml|granule[-_ ]metadata|"
                     r"\bsidecar\b|calibrated_sensor\.json|\.ann\b|ANG\.txt|\bEXIF\b|\bexif\b|GPSImgDirection|"
                     r"CMR UMM"),
    ("item property", r"item propert|STAC propert|properties\.|view:off_nadir|view:incidence|\borientation\b|camera_orientation|"
                      r"desis:|enmap:"),
]
# A "none" row that still names an angle it might carry (after denials are stripped) is ambiguous.
NONE_DENIALS = [
    r"no heading or pitch( column)?", r"not a camera pitch or heading", r"does not expose EXIF heading",
    r"EXIF heading/pitch not exposed", r"no camera pitch", r"no pitch/off-nadir", r"no pitch field",
    r"no pitch", r"no scan angle", r"no camera angle", r"no off-nadir column", r"no angle",
    r"scan angle discarded", r"not an angle", r"no per-frame metadata", r"no QL, no point density, no scan angle",
    r"\(project name is in the item id\)", r"no point density", r"no flight altitude",
    r"no camera pitch/off-nadir or flight altitude", r"but no pitch/off-nadir", r"no EXIF pitch/off-nadir",
    r"no per-scene view angle", r"not scan angle", r"carry no angle", r"has no off-nadir column", r"but has no off-nadir column",
]
NONE_AFFIRM = (r"heading|compass|\bpitch\b|\bIMU\b|view angles?|view geometry|view direction|scan angle|"
               r"off-nadir|SOLAR_ZENITH")

ANGLE_RULES = [
    ("scan angle", r"ScanAngleRank|scan angle"),
    ("camera pitch", r"pitch|calibrated_sensor\.rotation"),
    ("camera heading", r"GPSImgDirection|\borientation\b|camera_orientation|heading|compass"),
    ("off-nadir", r"off_nadir|offNadir|OffNadir|off-nadir"),
    ("view zenith", r"ZENITH_ANGLE|\bVZA\b|zenith"),
    ("incidence", r"incidence|look_angle"),
]


def strip_negated(txt):
    for pat in NEGATED:
        txt = re.sub(pat, " ", txt)
    return txt


def classify(txt):
    """Return (location, angle_kind, ambiguous categories)."""
    t = txt.strip()
    if t.lower().startswith("none"):
        rest = t
        for pat in sorted(NONE_DENIALS, key=len, reverse=True):
            rest = re.sub(pat, " ", rest, flags=re.I)
        hits = sorted(set(m.group(0).lower() for m in re.finditer(NONE_AFFIRM, rest, flags=re.I)))
        return "none", "none", hits
    t = strip_negated(t)
    cats = [loc for loc, pat in LOCATION_RULES if re.search(pat, t)]
    kind_text = t
    for pat in sorted(NONE_DENIALS, key=len, reverse=True):
        kind_text = re.sub(pat, " ", kind_text, flags=re.I)
    kind = next((k for k, pat in ANGLE_RULES if re.search(pat, kind_text)), "none")
    if not cats:
        return "none", "none", ["no rule matched"]
    return cats[0], kind, (cats if len(cats) > 1 else [])


# Resolutions for ambiguous rows, decided by reading the row's notes / quality_fields.
# (candidate prefix) -> (location, angle_kind, reason)
RESOLUTIONS = [
    ("Sentinel-1 RTC", "sidecar file", "incidence",
     "text says per-pixel but notes: RTC item has only vv/vh; angle is the geolocationGrid in the GRD annotation XML"),
    ("HLS L30 v2.0", "per-pixel band", "view zenith",
     "VZA COG is the field; the CMR UMM scene mean is a second, coarser source of the same angle"),
    ("HLS S30 v2.0", "per-pixel band", "view zenith", "as HLS L30 (Planetary Computer)"),
    ("HLS L30 via", "per-pixel band", "view zenith",
     "VZA asset is gated by Earthdata login; notes say use the UMM record, which only holds the scene mean"),
    ("HLS S30 via", "per-pixel band", "view zenith", "as HLS L30 via CMR-STAC"),
    ("Landsat C2 L1", "item property", "off-nadir",
     "view:off_nadir is the primary field; per-pixel VZA assets and ANG.txt are extras"),
    ("3dep_pc:3dep-lidar-copc", "per-point dimension", "scan angle",
     "item property pc:schemas only advertises that the dimension exists; the value is per point"),
    ("uavsar_asf_search", "per-pixel band", "incidence",
     "*.inc incidence raster is the angle; the *.ann text is annotation beside it; contents not opened"),
    ("panoramax", "item property", "camera pitch",
     "properties.pers:pitch is the primary field; the exif copy is secondary"),
    ("EXIF GPS read", "sidecar file", "camera heading",
     "the row reads GPSImgDirection from EXIF; the Panoramax pitch is an aside about another source"),
    ("mapillary_api_v4", "item property", "camera heading",
     "text opens none, but quality_fields document compass_angle (heading); documented only, token-blocked"),
    ("kartaview", "none", "none", "heading was only in legacy v1 objects; nothing seen live, API now restricted"),
    ("bee_maps_hivemapper", "none", "none", "docs claim IMU per frame, unverified, no key"),
    ("bdd100k", "none", "none", "heading is the vehicle GPS track, per video, not an image field; host unreachable"),
    ("aviris", "none", "none", "heading is aircraft heading in a login-gated flight-line table, not a view angle"),
    ("emit_l2a", "none", "none", "only solar angles in the CMR record; view geometry unseen behind login"),
    ("pace_oci", "none", "none", "view angles would sit in the NetCDF swath, unopened behind login"),
    ("neon_aop", "none", "none", "point-cloud and flightline files unlisted (403), scan angle unchecked"),
    ("Sentinel Hub Catalog", "none", "none",
     "the catalog items carry no angle; S2 view angles live in the granule metadata, outside the catalog"),
    ("geograph", "none", "none", "view direction exists only on the photo page, absent from the feed"),
    ("bands/indices", "sidecar file", "view zenith",
     "workflow row spanning Landsat and S2; Landsat's item-property off_nadir is always <1 deg, so the informative "
     "angle is S2's granule-metadata XML"),
    ("period field", "sidecar file", "view zenith", "as the Q2 row"),
    ("qc filters", "sidecar file", "view zenith", "as the Q2 row"),
    ("observation.assets", "sidecar file", "view zenith", "as the Q2 row"),
]


def resolution_for(candidate):
    for prefix, loc, kind, why in RESOLUTIONS:
        if candidate.startswith(prefix):
            return loc, kind, why
    return None


# ---- loading ----------------------------------------------------------------------------

def load_lanes():
    frames = []
    for L in LANES:
        path = PROBES / L / f"{L}_probes.csv"
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        if list(df.columns) != COLS:
            sys.exit(f"{path}: unexpected columns {list(df.columns)}")
        df.insert(0, "lane", L)
        frames.append(df)
    return frames


def parse_hits(s):
    m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", s)
    return (int(m.group(1)), int(m.group(2))) if m else (pd.NA, pd.NA)


def fail_enum(df, col, allowed):
    bad = df[~df[col].isin(allowed)]
    if len(bad):
        print(bad[["lane", "gap", "candidate", col]].to_string())
        sys.exit(f"enum violation in {col}")


def build_probes(frames):
    df = pd.concat(frames, ignore_index=True)
    df["source_type"] = df.apply(normalise_source_type, axis=1)
    fail_enum(df, "source_type", SOURCE_TYPES)
    df["observation_unit"] = df["observation_unit"].str.strip().str.lower()
    fail_enum(df, "observation_unit", OBS_UNITS)
    hits = df["aoi_hits"].map(parse_hits)
    df["hits_num"] = pd.array([h[0] for h in hits], dtype="Int64")
    df["hits_den"] = pd.array([h[1] for h in hits], dtype="Int64")

    locs, kinds, ambiguous = [], [], []
    for _, r in df.iterrows():
        loc, kind, amb = classify(r["off_nadir_field"])
        res = resolution_for(r["candidate"])
        if amb:
            if res is None:
                print(r[["lane", "candidate", "off_nadir_field"]].to_string())
                sys.exit(f"unresolved ambiguity {amb} for {r['candidate']}")
            loc, kind, why = res
            ambiguous.append((r["lane"], r["candidate"], amb, loc, kind, why, r["off_nadir_field"], r["notes"]))
        locs.append(loc)
        kinds.append(kind)
    df["off_nadir_location"] = locs
    df["angle_kind"] = kinds
    fail_enum(df, "off_nadir_location", LOCATIONS)
    fail_enum(df, "angle_kind", ANGLE_KINDS)
    df = df.assign(_order=range(len(df))).sort_values(["gap", "lane", "_order"], kind="stable").drop(columns="_order")
    return df.reset_index(drop=True), ambiguous


# ---- off_nadir_fields -------------------------------------------------------------------

BACKFILL_COLLECTION = {"Sentinel-2 L2A (re-query": "sentinel-2-l2a", "Landsat C2 L2 (re-query": "landsat-c2-l2",
                       "Sentinel-1 RTC (re-query": "sentinel-1-rtc"}

# (candidate prefix, concise field name)
FIELD_NAMES = [
    ("Sentinel-2 L2A", "MTD_TL.xml Mean_Viewing_Incidence_Angle_List/ZENITH_ANGLE (13 bands)"),
    ("Landsat C2 L2", "view:off_nadir"),
    ("Sentinel-1 RTC", "GRD annotation/iw-vv.xml geolocationGrid/incidenceAngle"),
    ("Maxar", "view:off_nadir; view:incidence_angle"),
    ("Satellogic", "view:off_nadir"),
    ("Umbra", "view:incidence_angle"),
    ("Capella", "view:incidence_angle; capella:look_angle"),
    ("ICEYE", "view:off_nadir; view:incidence_angle"),
    ("Planet open STAC", "view:off_nadir"),
    ("HLS L30 v2.0", "VZA asset"),
    ("HLS S30 v2.0", "VZA asset"),
    ("HLS L30 via", "VZA asset; CMR UMM MEAN_VIEW_ZENITH_ANGLE"),
    ("HLS S30 via", "VZA asset; CMR UMM MEAN_VIEW_ZENITH_ANGLE"),
    ("Sentinel-2 L1C", "granule_metadata asset metadata.xml Mean_Viewing_Incidence_Angle_List/ZENITH_ANGLE"),
    ("Landsat C2 L1", "view:off_nadir; VZA/VAA assets; ANG.txt"),
    ("SkyFi", "offNadirAngle (ArchiveResponse); filter maxOffNadirAngle"),
    ("UP42", "per-host STAC property (incidence angle, off-nadir angle)"),
    ("3dep_pc:3dep-lidar-copc", "ScanAngleRank"),
    ("enmap_l2a", "enmap:acrossOffNadirAngle; enmap:alongOffNadirAngle"),
    ("desis_l2a", "desis:sceneIncidenceAngle"),
    ("planet_tanager", "view:off_nadir"),
    ("uavsar", "*.inc incidence raster; *.ann annotation"),
    ("panoramax", "properties.pers:pitch; properties.view:azimuth"),
    ("Panoramax API", "properties.pers:pitch; properties.view:azimuth"),
    ("mapillary_api_v4", "compass_angle"),
    ("drivebc", "orientation"),
    ("phenocam", "sitemetadata.camera_orientation"),
    ("wikimedia_commons", "metadata.GPSImgDirection"),
    ("nuscenes", "calibrated_sensor.rotation"),
]

# (candidate prefix, regex on off_nadir_field, group) -> sample_value, stated in the probe CSV
SAMPLE_VALUE = [
    ("Maxar", r"sample ([\d.]+) deg"),
    ("Satellogic", r"sample ([\d.]+) deg"),
    ("Umbra", r"view:incidence_angle \(([\d.]+)\)"),
    ("Capella", r"view:incidence_angle \(([\d.]+)\)"),
    ("ICEYE", r"view:off_nadir \(([\d.]+)\)"),
    ("Planet open STAC", r"view:off_nadir \(([\d.]+)\)"),
    ("HLS L30 v2.0", r"centroid ([\d.]+) deg"),
    ("HLS S30 v2.0", r"centroid ([\d.]+) deg"),
    ("Sentinel-2 L1C", r"sample ([\d.]+) deg"),
    ("Landsat C2 L1", r"sample ([\d.]+)\)"),
    ("SkyFi", r"example ([\d.]+)"),
    ("drivebc", r"e\.g\. '(\w+)'"),
    ("phenocam", r"e\.g\. '(\w+)'"),
]
# (candidate prefix, regex on off_nadir_field or notes) -> sample_range
SAMPLE_RANGE = [
    ("SkyFi", "off_nadir_field", r"range (-?\d+\.\.-?\d+)"),
    ("planet_tanager", "notes", r"off-nadir range in set ([\d.]+-[\d.]+)"),
    ("panoramax", "notes", r"stress_city_toronto_full: \d+/\d+ nonzero \{(-\d+):.*?(\d+): \d+\} dated"),
]
NOTES = [
    ("Sentinel-2 L2A", "Mean of 13 per-band zenith angles, per granule; range over the 15 POC scenes"),
    ("Landsat C2 L2", "Range over the 15 POC scenes"),
    ("Sentinel-1 RTC", "Incidence at the AOI centroid from the GRD annotation grid, not on the RTC item; range over 15 POC scenes"),
    ("Maxar", "Also view:incidence_angle 43.7 deg; Maxar ARD tile"),
    ("Satellogic", "In {item}_metadata.json; view:azimuth and sun angles alongside"),
    ("Umbra", "Incidence only; no off-nadir field"),
    ("Capella", "capella:look_angle 33.5 deg is the off-nadir equivalent; sample item CAPELLA_C03_SP_GEO_HH_20210408172422"),
    ("ICEYE", "view:incidence_angle 22.734908 deg also present"),
    ("Planet open STAC", "Sample is a Tanager-1 scene (other hit 12.2 deg); SkySat/PlanetScope not hit"),
    ("HLS L30 v2.0", "Per-pixel COG, scale 0.01 deg; value at the farm_sk_quarter centroid; scene mean 3.17 deg from CMR UMM MEAN_VIEW_ZENITH_ANGLE"),
    ("HLS S30 v2.0", "Per-pixel COG, scale 0.01 deg; value at the farm_sk_quarter centroid; items carry only view:azimuth"),
    ("HLS L30 via", "VZA href needs Earthdata login; scene mean public in the CMR UMM record; STAC item properties hold only eo:cloud_cover"),
    ("HLS S30 via", "VZA href needs Earthdata login; scene mean public in the CMR UMM record; STAC item properties hold only eo:cloud_cover"),
    ("Sentinel-2 L1C", "Sidecar over https; sample is the mean of 13 bands; not in item properties"),
    ("Landsat C2 L1", "Sample 0 deg"),
    ("SkyFi", "Schema range; request filter maxOffNadirAngle spans 0..50"),
    ("UP42", "Documented per collection (Pleiades: incidence 5-50 deg, off-nadir 30 deg); name not verifiable without a token"),
    ("3dep_pc:3dep-lidar-copc", "Per-point LAS dimension in the COPC file; the eight derived 3DEP rasters carry no angle (scan angle discarded)"),
    ("enmap_l2a", "Signed degrees; the only hyperspectral source with off-nadir item properties"),
    ("desis_l2a", "Named incidence, not off-nadir; plus desis:sceneAzimuthAngle"),
    ("planet_tanager", "Also view:azimuth; range over 153 scenes in the static catalogue"),
    ("uavsar", "Listed per scene in the ASF file list; contents not opened (Earthdata login)"),
    ("panoramax", "Heading in view:azimuth; exif copies Xmp.Camera.Pitch / Xmp.GPano.PosePitchDegrees"),
    ("Panoramax API", "Pitch 0 on every Toronto core item; non-zero on 202 of 999 in the Toronto stress extent"),
    ("mapillary_api_v4", "Documented heading only, no pitch; token-blocked, not verified live"),
    ("drivebc", "Cardinal compass facing; no pitch"),
    ("phenocam", "Cardinal compass facing; no pitch"),
    ("wikimedia_commons", "EXIF heading when present (9 of 31 sampled files); no pitch"),
    ("nuscenes", "Camera extrinsics quaternion incl. pitch; docs only, not verified live, registration needed"),
]
SOURCE_NAME = [("3dep_pc:3dep-lidar-copc", "3DEP lidar COPC (Planetary Computer)"),
               ("Panoramax API", "panoramax")]


def lookup(table, candidate):
    for entry in table:
        if candidate.startswith(entry[0]):
            return entry
    return None


def sentinel_backfill():
    bf = pd.read_csv(PROBES / "A" / "scene_qc_backfill.csv")
    g = bf.groupby("collection")["off_nadir_deg"].agg(["min", "max", "count"])
    return {c: (f"{r['min']:.1f}-{r['max']:.1f}", f"{r['min']:.1f}", int(r["count"])) for c, r in g.iterrows()}


def clean_number(s):
    try:
        return f"{float(s):.4g}" if len(s) > 8 else s
    except ValueError:
        return s


def build_fields(df):
    backfill = sentinel_backfill()
    rows = []
    for _, r in df.iterrows():
        if r["off_nadir_location"] == "none" or r["source_type"] in ("model", "registry") or r["lane"] == "F":
            continue
        cand = r["candidate"]
        name = (lookup(SOURCE_NAME, cand) or (None, cand))[1]
        field = (lookup(FIELD_NAMES, cand) or (None, r["off_nadir_field"]))[1]
        sample_value, sample_range = "", ""
        sv = lookup(SAMPLE_VALUE, cand)
        if sv:
            m = re.search(sv[1], r["off_nadir_field"])
            if m:
                sample_value = clean_number(m.group(1))
        sr = lookup(SAMPLE_RANGE, cand)
        if sr:
            m = re.search(sr[2], r[sr[1]])
            if m:
                sample_range = m.group(1) if m.lastindex == 1 else f"{m.group(1)}..{m.group(m.lastindex)}"
        for prefix, coll in BACKFILL_COLLECTION.items():
            if cand.startswith(prefix):
                rng, first_min, _ = backfill[coll]
                sample_range = rng
                if coll == "landsat-c2-l2":
                    sample_value = first_min
        note = (lookup(NOTES, cand) or (None, ""))[1]
        rows.append(dict(source=name, source_type=r["source_type"], gap=r["gap"], angle_kind=r["angle_kind"],
                         field=field, location=r["off_nadir_location"], sample_value=sample_value,
                         sample_range=sample_range, note=note))
    out = pd.DataFrame(rows)
    merged = []
    for name, grp in out.groupby("source", sort=False):
        first = grp.iloc[0].copy()
        first["gap"] = "; ".join(sorted(set(grp["gap"])))
        for col in ("sample_value", "sample_range", "note"):
            first[col] = next((v for v in grp[col] if v), "")
        merged.append(first)
    res = pd.DataFrame(merged)
    res["_g"] = res["gap"].str.split("; ").str[0]
    res = res.sort_values("_g", kind="stable").drop(columns="_g")
    return res.reset_index(drop=True)


def main():
    frames = load_lanes()
    df, ambiguous = build_probes(frames)
    expected = sum(len(f) for f in frames)
    assert len(df) == expected, (len(df), expected)

    print("AMBIGUOUS ROWS (matched categories -> resolution):")
    for lane, cand, amb, loc, kind, why, field, notes in ambiguous:
        print(f"  [{lane}] {cand}\n      matched: {amb}\n      -> {loc} / {kind}: {why}")
    print(f"  ({len(ambiguous)} rows)\n")

    df.to_csv(REPORTS / "gap_source_probes.csv", index=False)
    fields = build_fields(df)
    fields.to_csv(REPORTS / "off_nadir_fields.csv", index=False)

    print(f"rows: {len(df)} (sum of lane rows {expected}; per lane "
          f"{ {L: len(f) for L, f in zip(LANES, frames)} })")
    for col in ("source_type", "observation_unit", "off_nadir_location", "angle_kind"):
        print(f"\n{col}\n{df[col].value_counts().to_string()}")
    print(f"\noff_nadir_fields.csv ({len(fields)} rows)")
    with pd.option_context("display.max_colwidth", 70, "display.width", 250, "display.max_columns", 20):
        print(fields.to_string())


if __name__ == "__main__":
    main()

"""Compare the probed-feature listing against the fresh poc_values.csv of the five probe lanes.

Writes recheck_status.csv next to this file: one row per listed feature, with how many AOIs the
listing claims, how many the re-run read again, and ok / fixed / failing. FIXED holds the features
whose lane script had to be repaired before they read again; REASONS holds the diagnosis for a
feature that still reads nothing.
"""
import csv
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LANES = ["SAT", "AIR", "HYP", "REC", "CAM"]

_WM = ("CAM poc.py wikimedia_tile treated HTTP 200 with error cirrussearch-too-busy-error as fatal, so city_montreal_core "
       "(and, in this run, stress_city_toronto_full) dropped out; now retries with backoff and all 15 AOIs read")
FIXED = {("wikimedia_commons", "wikimedia_photo_n"): _WM, ("wikimedia_commons", "wikimedia_camera_heading_deg"): _WM}
REASONS = {}


def main():
    listed = pd.read_csv(ROOT / "reports" / "probed_features.csv")
    fresh, lane_of = {}, {}
    for lane in LANES:
        v = pd.read_csv(ROOT / "reports" / "probes" / lane / "poc" / "poc_values.csv", dtype=str)
        v = v[v["value"].notna() & (v["value"].str.strip() != "")]
        for key, n in v.groupby(["source", "feature"]).aoi_id.nunique().items():
            fresh[key] = n
        old = pd.read_csv(ROOT / "reports" / "probes" / lane / "poc" / "poc_values.before_recheck.csv", dtype=str)
        for key in set(zip(old.source, old.feature)):
            lane_of[key] = lane
    rows = []
    for r in listed.itertuples():
        key = (r.source, r.feature)
        n = int(fresh.get(key, 0))
        reason = ""
        if n == 0:
            status = "failing"
            reason = REASONS.get(key, "no fresh value at any AOI")
        elif key in FIXED:
            status, reason = "fixed", FIXED[key]
        else:
            status = "ok"
        if n and n * 2 < r.n_aois:
            reason = (reason + "; " if reason else "") + f"FLAG: AOI count fell by more than half ({r.n_aois} -> {n})"
        rows.append(dict(lane=lane_of.get(key, ""), source=r.source, feature=r.feature, n_aois_listed=r.n_aois,
                         n_aois_fresh=n, status=status, reason=reason))
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "recheck_status.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    print(out.status.value_counts().to_string())
    drift = out[out.n_aois_fresh != out.n_aois_listed]
    print(drift.to_string())


if __name__ == "__main__":
    main()

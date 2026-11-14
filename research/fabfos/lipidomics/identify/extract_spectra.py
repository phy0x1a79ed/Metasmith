"""T3 -- pull MS/MS for the hit features straight out of the raw runs.

This is the step that goes back to the instrument data rather than trusting the
facility's summary of it. It is deliberately independent of the earlier MS-DIAL
run, which found only 106 POS / 37 NEG features and so cannot be a source here:
the mzML carry every MS2 scan the instrument acquired regardless of what any
peak-picker later kept.

Method: for each feature, open the mzML of the samples where it is most
abundant, keep every MS2 scan whose precursor matches the feature's measured m/z
and retention time, and merge those scans into one consensus spectrum. Each scan
is normalised to its own base peak before merging so a single intense scan
cannot dominate, and fragments seen in only one scan are dropped as noise when
there are enough scans to judge.

Polarity is taken from the resolved adduct, and only that polarity's files are
opened -- searching a negative-mode feature against positive-mode runs returns
confident nonsense.

Requires pyteomics, which lives in the `lipidomics` env and not in `p312`.
Run:  mamba run -n lipidomics python -m identify.extract_spectra  (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import json
import sys
import time
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path

import pandas as pd
from pyteomics import mzml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

PRECURSOR_TOL_DA = 0.05
RT_TOL_MIN = 0.30
SAMPLES_PER_FEATURE = 2
# A fragment must be seen more than once to count as signal. This is an absolute
# count, not a fraction of scans: PASEF acquires MS2 at varying collision
# energies, so a fragment genuinely present may appear in a minority of scans.
# A proportional threshold punished exactly the features with the most data --
# one feature with 107 scans survived with a single peak while a 4-scan feature
# kept 120.
MIN_SCAN_COUNT = 2
REL_INTENSITY_FLOOR = 0.5   # % of base peak
MAX_PEAKS = 120
BIN_DP = 2                # 0.01 Da merge bins, matched to a 0.05 Da search tol
MAX_PEAKS_PER_SCAN = 200  # bounds the persisted raw scans
# At 29 features the persisted scans were a few MB; at 1862 they are not. A
# consensus is saturated long before 40 scans, so this bounds memory without
# costing spectral quality. Features that hit the cap are counted and reported --
# a truncation nobody is told about reads as full coverage.
MAX_SCANS_PER_FEATURE = 40


def _mzml_for(polarity: str, run: str) -> Path | None:
    for p in common.MZML_DIR[polarity].glob("*.mzML"):
        if p.stem.endswith(f"_{run}"):
            return p
    return None


def _rt_minutes(spectrum: dict) -> float | None:
    try:
        t = spectrum["scanList"]["scan"][0]["scan start time"]
    except (KeyError, IndexError):
        return None
    unit = getattr(t, "unit_info", None)
    return float(t) / 60.0 if unit == "second" else float(t)


def _precursor_mz(spectrum: dict) -> float | None:
    try:
        return float(
            spectrum["precursorList"]["precursor"][0]
            ["selectedIonList"]["selectedIon"][0]["selected ion m/z"]
        )
    except (KeyError, IndexError):
        return None


def plan_scans(manifest: pd.DataFrame, runs: dict) -> tuple[dict[Path, list[dict]], list[str]]:
    """Group the work by file so each mzML is opened exactly once."""
    jobs: dict[Path, list[dict]] = defaultdict(list)
    skipped = []
    for _, f in manifest.iterrows():
        if not f.has_msms or not isinstance(f.polarity, str):
            skipped.append(f.feature_id)
            continue
        for sample in str(f.target_samples).split(";")[:SAMPLES_PER_FEATURE]:
            run = runs.get(sample, {}).get(f.polarity)
            if not run:
                continue
            path = _mzml_for(f.polarity, run)
            if path is None:
                continue
            jobs[path].append(
                {"feature_id": f.feature_id, "mz": float(f.mz),
                 "rt": float(f.rt), "sample": sample}
            )
    return jobs, skipped


def _consensus(scans: list[list[tuple[float, float]]]) -> list[list[float]]:
    """Merge replicate MS2 scans of one precursor into a single spectrum.

    Each scan is normalised to its own base peak before merging, so one intense
    scan cannot dominate. A bin must be seen in at least MIN_SCAN_COUNT scans to
    survive; with a single scan there is nothing to corroborate against, so the
    filter is skipped and the spectrum is kept as-is.
    """
    if not scans:
        return []
    binned: dict[float, list[float]] = defaultdict(list)
    for peaks in scans:
        base = max((i for _, i in peaks), default=0.0)
        if base <= 0:
            continue
        for mz, inten in peaks:
            binned[round(mz, BIN_DP)].append(inten / base * 100.0)
    if not binned:
        return []

    threshold = MIN_SCAN_COUNT if len(scans) >= MIN_SCAN_COUNT else 1
    merged = [
        (mz, sum(v) / len(v))  # mean over the scans that saw it, not over all
        for mz, v in binned.items()
        if len(v) >= threshold
    ]
    if not merged:
        merged = [(mz, sum(v) / len(v)) for mz, v in binned.items()]

    top = max(i for _, i in merged)
    merged = [(mz, i) for mz, i in merged if i / top * 100.0 >= REL_INTENSITY_FLOOR]
    merged.sort(key=lambda x: x[1], reverse=True)
    merged = merged[:MAX_PEAKS]
    top = max(i for _, i in merged)
    return sorted([[round(mz, 4), round(i / top * 100.0, 3)] for mz, i in merged])


RAW_SCANS = "raw_scans.json"

# The 29-hit lane and the whole-table lane write to different files. The published
# identification outputs are derived from the former, so the latter must never
# land on top of it.
LANES = {
    "hits": {"manifest": "hit_manifest.csv", "prefix": ""},
    "full": {"manifest": "full_manifest.csv", "prefix": "full_"},
}


def _scan_files(manifest: pd.DataFrame, runs: dict) -> tuple[dict, dict]:
    jobs, skipped = plan_scans(manifest, runs)
    print(f"files to scan: {len(jobs)}   "
          f"(features with no MS/MS or no polarity, skipped: {len(skipped)})")
    collected: dict[str, list] = defaultdict(list)
    provenance: dict[str, list[str]] = defaultdict(list)
    capped: set[str] = set()

    for n, (path, targets) in enumerate(sorted(jobs.items()), 1):
        t0 = time.time()
        n_hit = 0
        # Sort targets by precursor m/z once per file so each MS2 spectrum can
        # bisect to the handful inside its tolerance window instead of walking
        # every target. At 29 targets the linear scan was free; at ~1900 it is
        # the difference between minutes and hours.
        targets = sorted(targets, key=lambda t: t["mz"])
        tmz = [t["mz"] for t in targets]
        with mzml.read(str(path), use_index=False) as reader:
            for spec in reader:
                if spec.get("ms level") != 2:
                    continue
                pmz = _precursor_mz(spec)
                if pmz is None:
                    continue
                lo = bisect_left(tmz, pmz - PRECURSOR_TOL_DA)
                hi = bisect_right(tmz, pmz + PRECURSOR_TOL_DA)
                if lo == hi:
                    continue
                rt = _rt_minutes(spec)
                if rt is None:
                    continue
                peaks = None
                for t in targets[lo:hi]:
                    if abs(rt - t["rt"]) > RT_TOL_MIN:
                        continue
                    if t["feature_id"] in capped:
                        continue
                    if peaks is None:
                        mzs = spec.get("m/z array")
                        ints = spec.get("intensity array")
                        if mzs is None or len(mzs) == 0:
                            break
                        peaks = [
                            [round(m, 5), round(i, 2)]
                            for m, i in sorted(
                                zip(map(float, mzs), map(float, ints)),
                                key=lambda p: p[1], reverse=True,
                            )[:MAX_PEAKS_PER_SCAN]
                        ]
                    collected[t["feature_id"]].append(peaks)
                    provenance[t["feature_id"]].append(f"{t['sample']}:{path.stem}")
                    n_hit += 1
                    if len(collected[t["feature_id"]]) >= MAX_SCANS_PER_FEATURE:
                        capped.add(t["feature_id"])
        print(f"  [{n:3d}/{len(jobs)}] {path.name[:54]:<54} "
              f"{len(targets):4d} target(s) -> {n_hit:5d} scans  {time.time() - t0:.0f}s",
              flush=True)
    if capped:
        print(f"\n  {len(capped)} features hit the {MAX_SCANS_PER_FEATURE}-scan cap "
              "(consensus unaffected; later scans discarded)")
    return collected, provenance


def run(reuse: bool = False, lane: str = "hits") -> dict:
    common.ensure_dirs()
    cfg = LANES[lane]
    pre = cfg["prefix"]
    manifest = pd.read_csv(common.IDENT_DIR / cfg["manifest"])
    runs = json.loads((common.IDENT_DIR / "sample_runs.json").read_text())

    raw_path = common.SPECTRA_DIR / (pre + RAW_SCANS)
    if reuse and raw_path.exists():
        # Re-derive the consensus from persisted scans. Retuning the merge rule
        # should not cost another pass over 30 GB of mzML.
        blob = json.loads(raw_path.read_text())
        collected = {k: v["scans"] for k, v in blob.items()}
        provenance = {k: v["sources"] for k, v in blob.items()}
        print(f"reusing persisted scans for {len(collected)} features ({raw_path})")
    else:
        collected, provenance = _scan_files(manifest, runs)
        raw_path.write_text(json.dumps(
            {fid: {"scans": scans, "sources": provenance[fid]}
             for fid, scans in collected.items()}
        ))

    out = {}
    for fid, scans in collected.items():
        peaks = _consensus(scans)
        if not peaks:
            continue
        out[fid] = {
            "feature_id": fid,
            "n_scans": len(scans),
            "n_peaks": len(peaks),
            "peaks": peaks,
            "sources": sorted(set(provenance[fid])),
        }

    (common.SPECTRA_DIR / (pre + "consensus_ms2.json")).write_text(
        json.dumps(out, indent=1))
    _write_msp(manifest, out, pre)

    want = int(manifest.has_msms.sum())
    print(f"\nMS/MS extraction  (lane: {lane})")
    print(f"  features flagged as having MS/MS   {want}")
    print(f"  features with a consensus spectrum {len(out)}")
    missed = sorted(set(manifest[manifest.has_msms].feature_id) - set(out))
    if missed:
        # These are indeterminate downstream, not negative: the instrument says it
        # fragmented them, and we failed to find the scans.
        print(f"  no scans recovered for             {len(missed)}")
        if len(missed) <= 40:
            print(f"    {', '.join(missed)}")
    if lane == "hits":
        for fid, s in sorted(out.items()):
            mark = "  <- control" if fid in common.CONTROL_FEATURES else ""
            print(f"    {fid}  {s['n_scans']:4d} scans -> {s['n_peaks']:3d} peaks{mark}")
    else:
        ns = pd.Series([s["n_scans"] for s in out.values()])
        np_ = pd.Series([s["n_peaks"] for s in out.values()])
        print(f"  scans per feature   median {ns.median():.0f}  "
              f"q1 {ns.quantile(.25):.0f}  q3 {ns.quantile(.75):.0f}  max {ns.max()}")
        print(f"  peaks per consensus median {np_.median():.0f}  "
              f"q1 {np_.quantile(.25):.0f}  q3 {np_.quantile(.75):.0f}")
        for fid in sorted(common.CONTROL_FEATURES):
            s = out.get(fid)
            print(f"    control {fid}: "
                  + (f"{s['n_scans']} scans -> {s['n_peaks']} peaks" if s
                     else "NO SPECTRUM"))
    return out


def _write_msp(manifest: pd.DataFrame, spectra: dict, prefix: str = "") -> None:
    m = manifest.set_index("feature_id")
    lines = []
    for fid, s in sorted(spectra.items()):
        f = m.loc[fid]
        lines += [
            f"NAME: {fid}",
            f"PRECURSORMZ: {f.mz}",
            f"PRECURSORTYPE: {f.adduct}",
            f"RETENTIONTIME: {f.rt}",
            f"IONMODE: {'Positive' if f.polarity == 'pos' else 'Negative'}",
            f"COMMENT: scans={s['n_scans']} ccs={f.ccs}",
            f"Num Peaks: {len(s['peaks'])}",
        ]
        lines += [f"{mz}\t{i}" for mz, i in s["peaks"]]
        lines.append("")
    (common.SPECTRA_DIR / (prefix + "consensus_ms2.msp")).write_text("\n".join(lines))


if __name__ == "__main__":
    run(reuse="--reuse" in sys.argv,
        lane="full" if "--full" in sys.argv else "hits")

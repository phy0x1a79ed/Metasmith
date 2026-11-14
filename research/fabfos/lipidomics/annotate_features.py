"""Post-MS-DIAL lipid annotation via matchms.

Workaround for MS-DIAL 5.5 Linux Console bug #733 — the Console silently
skips MSP library loading on Linux, so every feature comes out as "Unknown".
This script loads the same MSP MS-DIAL would have used and does a per-feature
cosine match against MS/MS spectra in the alignment matrix.

Input:  data/fabfos/runs/scadc_lipidomics/processed/{pol}/aligned_features_{pol}.csv
Output: data/fabfos/runs/scadc_lipidomics/processed/{pol}/aligned_features_{pol}.annotated.csv
        — same columns + `lipid_name`, `match_score`, `match_n_peaks` filled.

Run: mamba run -n lipidomics python research/fabfos/lipidomics/annotate_features.py {pos|neg}
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from matchms import Spectrum
from matchms.filtering import default_filters, normalize_intensities
from matchms.importing import load_from_msp
from matchms.similarity import CosineGreedy

PROJECT = Path(__file__).resolve().parents[3]
PROCESSED = PROJECT / "data/fabfos/runs/scadc_lipidomics/processed"
MSP_DIR = PROJECT / "lib/msdial/lipidblast"

MZ_TOL = 0.01    # Da, MS1 tolerance for narrowing library to candidate precursors
SCORE_CUT = 0.6  # cosine score cutoff
MIN_PEAKS = 3    # min matched peaks


def _parse_msms_spectrum(s: str) -> np.ndarray:
    """MS-DIAL 'MS/MS spectrum' column is space-separated `mz:intensity` pairs."""
    if not isinstance(s, str) or not s.strip() or s.strip().lower() in {"null", "nan"}:
        return np.empty((0, 2))
    pairs = []
    for tok in s.split():
        if ":" not in tok:
            continue
        mz, inten = tok.split(":", 1)
        try:
            pairs.append((float(mz), float(inten)))
        except ValueError:
            continue
    if not pairs:
        return np.empty((0, 2))
    return np.array(pairs, dtype=float)


def _load_library(msp_path: Path) -> list[Spectrum]:
    print(f"loading MSP library: {msp_path.name}", file=sys.stderr)
    specs = []
    for s in load_from_msp(str(msp_path)):
        if s is None:
            continue
        s = default_filters(s)
        s = normalize_intensities(s)
        if s is None or len(s.peaks.mz) < MIN_PEAKS:
            continue
        specs.append(s)
    print(f"loaded {len(specs)} reference spectra", file=sys.stderr)
    return specs


def annotate(polarity: str) -> int:
    csv = PROCESSED / polarity / f"aligned_features_{polarity}.csv"
    if not csv.exists():
        alt = PROCESSED / f"{polarity}_smoke" / f"aligned_features_{polarity}.csv"
        if alt.exists():
            csv = alt
        else:
            raise FileNotFoundError(f"no MS-DIAL output at {csv} (or smoke {alt})")

    df = pd.read_csv(csv, sep="\t", low_memory=False)
    # skip leading metadata rows
    while not str(df.iloc[0, 0]).strip().lower().startswith("alignment id"):
        df = df.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.iloc[0]]
    df = df.iloc[1:].reset_index(drop=True)

    msp = MSP_DIR / f"MSDIAL-TandemMassSpectralAtlas-VS69-{'Pos' if polarity == 'pos' else 'Neg'}.msp"
    library = _load_library(msp)
    sim = CosineGreedy(tolerance=0.05)

    out_name, out_score, out_n = [], [], []
    for i, row in df.iterrows():
        msms_str = row.get("MS/MS spectrum", "") or ""
        peaks = _parse_msms_spectrum(msms_str)
        if peaks.shape[0] < MIN_PEAKS:
            out_name.append(None); out_score.append(None); out_n.append(None); continue

        try:
            prec_mz = float(row["Average Mz"])
        except (ValueError, TypeError):
            out_name.append(None); out_score.append(None); out_n.append(None); continue

        order = peaks[:, 0].argsort()
        query = Spectrum(mz=peaks[order, 0], intensities=peaks[order, 1],
                         metadata={"precursor_mz": prec_mz})
        query = normalize_intensities(default_filters(query))
        if query is None:
            out_name.append(None); out_score.append(None); out_n.append(None); continue

        best_score, best_n, best_name = 0.0, 0, None
        for ref in library:
            ref_mz = ref.metadata.get("precursor_mz")
            if ref_mz is None or abs(ref_mz - prec_mz) > MZ_TOL:
                continue
            res = sim.pair(query, ref)
            score = float(res["score"])
            n = int(res["matches"])
            if score > best_score and n >= MIN_PEAKS:
                best_score, best_n = score, n
                best_name = ref.metadata.get("compound_name") or ref.metadata.get("name")

        if best_score >= SCORE_CUT:
            out_name.append(best_name); out_score.append(round(best_score, 3)); out_n.append(best_n)
        else:
            out_name.append(None); out_score.append(round(best_score, 3) if best_score else None); out_n.append(best_n or None)

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(df)} features scored, {sum(1 for x in out_name if x)} annotated", file=sys.stderr)

    df["lipid_name"] = [n or "Unknown" for n in out_name]
    df["match_score"] = out_score
    df["match_n_peaks"] = out_n

    out = csv.with_suffix(".annotated.csv")
    df.to_csv(out, sep="\t", index=False)
    n_ann = sum(1 for x in out_name if x)
    print(f"wrote {out} ({n_ann}/{len(df)} annotated)")
    return 0


if __name__ == "__main__":
    pol = sys.argv[1] if len(sys.argv) > 1 else "pos"
    raise SystemExit(annotate(pol))

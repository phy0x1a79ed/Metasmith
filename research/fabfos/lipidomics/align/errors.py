"""Fit the read-to-read error model per observation from QC replicate pairs."""
import itertools
import json

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from . import load

OUT = load.ROOT / "data/fabfos/runs/scadc_feature_tables_v1"
CUDA_MZ = {"POS": 341.2799, "NEG": 339.2653}
WINDOW = np.array([50.0, 0.3, 10.0])  # ppm, min, mobility %
DIMS = ["ppm", "rt", "mob_pct"]
BG_SHIFT = 1.0
RADIUS = 20.0  # in sigma units, for the real-vs-background comparison
# Beyond ~12 sigma the QC excess is mobility conformers, not measurement error.
MAX_D = 12.0


def coords(reads: pd.DataFrame, offsets: pd.DataFrame | None = None) -> np.ndarray:
    x = np.column_stack([np.log(reads.mz) * 1e6, reads.rt_aligned, np.log(reads.mobility) * 100])
    if offsets is not None:
        x -= offsets.loc[reads.injection].to_numpy()
    return x


def cuda_rt(reads: pd.DataFrame, polarity: str) -> pd.Series:
    t = CUDA_MZ[polarity]
    c = reads[(abs(reads.mz - t) / t * 1e6 < 10) & reads.rt.between(0.6, 1.0)]
    return c.sort_values("height").groupby("injection").rt.last()


def align_rt(reads: pd.DataFrame, polarity: str) -> pd.DataFrame:
    rt = cuda_rt(reads, polarity)
    missing = set(reads.injection) - set(rt.index)
    if missing:
        raise SystemExit(f"no CUDA read in {sorted(missing)}")
    return reads.assign(rt_aligned=reads.rt - reads.injection.map(rt - rt.median()))


def mutual_nearest(a: np.ndarray, b: np.ndarray, scale: np.ndarray, radius: float) -> np.ndarray:
    ta, tb = cKDTree(a / scale), cKDTree(b / scale)
    dab, iab = tb.query(a / scale, distance_upper_bound=radius)
    _, iba = ta.query(b / scale, distance_upper_bound=radius)
    ia = np.flatnonzero(np.isfinite(dab))
    ib = iab[ia]
    keep = iba[ib] == ia
    return np.column_stack([ia[keep], ib[keep]])


def pair_deltas(reads, offsets, scale, radius, rt_shift=0.0) -> dict:
    out = {}
    for x, y in itertools.combinations(sorted(reads.injection.unique()), 2):
        a = coords(reads[reads.injection == x], offsets)
        b = coords(reads[reads.injection == y], offsets)
        b[:, 1] += rt_shift
        p = mutual_nearest(a, b, scale, radius)
        out[x, y] = b[p[:, 1]] - a[p[:, 0]]
    return out


def solve_offsets(deltas: dict, injections: list) -> pd.DataFrame:
    idx = {k: i for i, k in enumerate(injections)}
    A = np.zeros((len(deltas) + 1, len(injections)))
    B = np.zeros((len(deltas) + 1, 3))
    for r, ((x, y), d) in enumerate(deltas.items()):
        A[r, idx[y]], A[r, idx[x]] = 1, -1
        B[r] = np.median(d, axis=0)
    A[-1] = 1
    return pd.DataFrame(np.linalg.lstsq(A, B, rcond=None)[0], index=injections, columns=DIMS)


def robust_sigma(d: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(d, [5, 95], axis=0)
    return (hi - lo) / 3.29


def equal_density_cutoff(real: np.ndarray, bg: np.ndarray) -> float:
    edges = np.arange(0, RADIUS + 0.25, 0.25)
    hr = np.convolve(np.histogram(real, edges)[0], np.ones(3) / 3, "same")
    hb = np.convolve(np.histogram(bg, edges)[0], np.ones(3) / 3, "same")
    peak = int(np.argmax(hr))
    cross = np.flatnonzero(hb[peak:] >= hr[peak:])
    return float(edges[peak + cross[0]]) ** 2 if len(cross) else RADIUS ** 2


def fit(observation: str, inj: pd.DataFrame) -> dict:
    polarity = load.OBSERVATIONS[observation][1]
    reads = align_rt(load.ions(inj, observation), polarity)
    qc_ids = sorted(inj[(inj.observation == observation) & (inj.sample_type == "qc")].injection)
    qc = reads[reads.injection.isin(qc_ids)]

    offsets = pd.DataFrame(0.0, index=qc_ids, columns=DIMS)
    scale, radius = WINDOW, np.sqrt(3)
    for _ in range(4):
        deltas = pair_deltas(qc, offsets, scale, radius)
        offsets += solve_offsets(deltas, qc_ids)
        sigma = robust_sigma(np.vstack(list(pair_deltas(qc, offsets, scale, radius).values())))
        scale = np.minimum(scale, 6 * sigma)

    real = np.vstack(list(pair_deltas(qc, offsets, sigma, RADIUS).values()))
    bg = np.vstack(list(pair_deltas(qc, offsets, sigma, RADIUS, BG_SHIFT).values()))
    d_real = np.sqrt(((real / sigma) ** 2).sum(1))
    d_bg = np.sqrt(((bg / sigma) ** 2).sum(1))
    crossing = equal_density_cutoff(d_real, d_bg)
    cutoff = min(crossing, MAX_D ** 2)
    n_under = (d_real ** 2 <= cutoff).sum()

    return {
        "observation": observation,
        "sigma": dict(zip(DIMS, sigma.round(5).tolist())),
        "d2_cutoff": round(cutoff, 2),
        "d2_equal_density": round(crossing, 2),
        "qc_pair_match_frac": round(float(n_under / len(list(itertools.combinations(qc_ids, 2))) / qc.groupby("injection").size().mean()), 4),
        "bg_to_real_under_cutoff": round(float((d_bg ** 2 <= cutoff).sum() / n_under), 4),
        "qc_offset_range": dict(zip(DIMS, np.ptp(offsets.to_numpy(), axis=0).round(4).tolist())),
        "cuda_rt_range": round(float(np.ptp(cuda_rt(reads, polarity))), 4),
    }


if __name__ == "__main__":
    inj = load.injections()
    for obs in load.OBSERVATIONS:
        m = fit(obs, inj)
        (OUT / obs).mkdir(parents=True, exist_ok=True)
        (OUT / obs / "error_model.json").write_text(json.dumps(m, indent=1))
        print(json.dumps(m))

"""Pairwise mutual-information distances between samples over each pair's own detected species, embedded by
weighted SMACOF with bootstrap clouds.

Run alone to recompute from the saved feature tables."""
import json
import sys

import numpy as np
import pandas as pd
from scipy.linalg import orthogonal_procrustes
from scipy.stats import kendalltau, rankdata, spearmanr

from . import load

K = 4
N_NULL = 200
N_BOOT = 200
CLOUD_CHI2 = 5.991  # 95% ellipse of a 2-D normal


def floors(x: np.ndarray) -> np.ndarray:
    return np.array([np.percentile(c[c > 0], 1) for c in x.T])


def codes(v: np.ndarray, above: np.ndarray) -> np.ndarray:
    # 0 = below the pair floor; 1..K = within-pair quantile of the measured values
    c = np.zeros(len(v), int)
    n = above.sum()
    if n:
        c[above] = 1 + np.minimum((rankdata(v[above]) - 1) * K // n, K - 1).astype(int)
    return c


def mi(tab: np.ndarray):
    """MI and both marginal entropies of (..., (K+1)**2) joint counts."""
    p = tab.reshape(*tab.shape[:-1], K + 1, K + 1)
    p = p / p.sum((-1, -2), keepdims=True)
    pi, pj = p.sum(-1), p.sum(-2)
    with np.errstate(divide="ignore", invalid="ignore"):
        info = np.where(p > 0, p * np.log(p / (pi[..., :, None] * pj[..., None, :])), 0).sum((-1, -2))
        h = lambda q: -np.where(q > 0, q * np.log(q), 0).sum(-1)
    return info, h(pi), h(pj)


def pairs(x: np.ndarray, rng) -> dict:
    n_sp, n = x.shape
    f = floors(x)
    boot = rng.multinomial(n_sp, np.full(n_sp, 1 / n_sp), size=N_BOOT).astype(float)
    m = (K + 1) ** 2
    d, db, tau, support = (np.zeros((n, n)), np.zeros((N_BOOT, n, n)), np.zeros((n, n)), np.zeros((n, n), int))
    for i in range(n):
        for j in range(i + 1, n):
            floor = max(f[i], f[j])
            ai, aj = x[:, i] >= floor, x[:, j] >= floor
            keep = ai | aj
            ci, cj = codes(x[keep, i], ai[keep]), codes(x[keep, j], aj[keep])
            joint = ci * (K + 1) + cj
            perm = np.argsort(rng.random((N_NULL, keep.sum())), axis=1)
            null = (ci * (K + 1) + cj[perm]) + m * np.arange(N_NULL)[:, None]
            null_mi = mi(np.bincount(null.ravel(), minlength=N_NULL * m).reshape(N_NULL, m))[0].mean()
            onehot = np.eye(m)[joint]
            for out, tab in ((d, np.bincount(joint, minlength=m)[None]), (db, boot[:, keep] @ onehot)):
                info, hi, hj = mi(tab)
                dist = np.clip(1 - (info - null_mi) / np.sqrt(hi * hj), 0, 1)
                if out is d:
                    d[i, j] = d[j, i] = dist[0]
                else:
                    db[:, i, j] = db[:, j, i] = dist
            vi, vj = np.where(ai[keep], x[keep, i], 0), np.where(aj[keep], x[keep, j], 0)
            tau[i, j] = tau[j, i] = (1 - kendalltau(vi, vj).statistic) / 2
            support[i, j] = support[j, i] = keep.sum()
    return {"d": d, "boot": db, "tau": tau, "support": support}


def classical(d: np.ndarray) -> np.ndarray:
    n = len(d)
    j = np.eye(n) - 1 / n
    w, v = np.linalg.eigh(-j @ (d ** 2) @ j / 2)
    top = np.argsort(w)[::-1][:2]
    return v[:, top] * np.sqrt(np.maximum(w[top], 0))


def smacof(d: np.ndarray, w: np.ndarray, x: np.ndarray, iters: int = 500, tol: float = 1e-7):
    v = -w.copy()
    np.fill_diagonal(v, 0)
    np.fill_diagonal(v, -v.sum(1))
    vp = np.linalg.pinv(v)
    iu = np.triu_indices(len(d), 1)
    last = np.inf
    for _ in range(iters):
        dx = np.linalg.norm(x[:, None] - x[None], axis=2)
        stress = (w * (d - dx) ** 2)[iu].sum() / (w * d ** 2)[iu].sum()
        if last - stress < tol:
            break
        last = stress
        b = -np.where(dx > 0, w * d / np.where(dx > 0, dx, 1), 0)
        np.fill_diagonal(b, 0)
        np.fill_diagonal(b, -b.sum(1))
        x = vp @ b @ x
    return x - x.mean(0), float(stress)


def embed(p: dict) -> dict:
    var = p["boot"].var(0)
    off = ~np.eye(len(var), dtype=bool)
    var = np.maximum(var, np.median(var[off]) * 0.01)
    w = np.where(off, 1 / var, 0)
    w /= w[off].mean()
    ref, stress = smacof(p["d"], w, classical(p["d"]))
    clouds = []
    for db in p["boot"]:
        y, _ = smacof(db, w, ref)
        r, _ = orthogonal_procrustes(y, ref)
        clouds.append(y @ r)
    return {"xy": ref, "clouds": np.array(clouds), "stress": stress}


def run(tables: dict, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    rows, checks = [], {}
    for obs, (inj, scaled) in tables.items():
        smp = inj[inj.sample_type == "sample"].sort_values(["strain", "treatment", "replicate"])
        ids = smp.sample_id.tolist()
        x = scaled[ids].to_numpy()
        x = x[(x > 0).any(axis=1)]
        p = pairs(x, rng)
        e = embed(p)
        cov = np.array([np.cov(e["clouds"][:, k].T) for k in range(len(ids))])
        rows.append(smp[["sample_id", "strain", "treatment", "replicate", "size_factor"]].assign(
            observation=obs, x=e["xy"][:, 0], y=e["xy"][:, 1],
            cxx=cov[:, 0, 0], cxy=cov[:, 0, 1], cyy=cov[:, 1, 1]))
        iu = np.triu_indices(len(ids), 1)
        cond = smp.strain.str.cat(smp.treatment).to_numpy()
        same = (cond[:, None] == cond[None])[iu]
        area = np.sqrt(np.linalg.det(cov))
        checks[obs] = {
            "support": [int(p["support"][iu].min()), int(p["support"][iu].max())],
            "d_range": [round(float(p["d"][iu].min()), 3), round(float(p["d"][iu].max()), 3)],
            "d_replicates": round(float(p["d"][iu][same].mean()), 3),
            "d_between": round(float(p["d"][iu][~same].mean()), 3),
            "rho_mi_kendall": round(float(spearmanr(p["d"][iu], p["tau"][iu]).statistic), 3),
            "rho_support_sd": round(float(spearmanr(p["support"][iu], p["boot"].std(0)[iu]).statistic), 3),
            "rho_cloud_size_factor": round(float(spearmanr(area, smp.size_factor).statistic), 3),
            "stress": round(e["stress"], 4),
        }
        print(obs, checks[obs], file=sys.stderr, flush=True)
    load.save(pd.concat(rows), load.OUT / "mi.parquet")
    return checks


if __name__ == "__main__":
    from .ordinate import from_disk
    frames = from_disk()
    if len(sys.argv) > 1:
        frames = {o: frames[o] for o in sys.argv[1:]}
    checks = json.loads((load.OUT / "checks.json").read_text())
    for obs, c in run(frames).items():
        checks[obs]["mi"] = c
    load.save(checks, load.OUT / "checks.json")

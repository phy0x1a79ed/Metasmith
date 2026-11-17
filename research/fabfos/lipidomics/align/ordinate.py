"""PCA and UMAP of each observation's 24 samples under three CLR zero-handling variants, plus the check report."""
import warnings

import numpy as np
import pandas as pd
import umap
from scipy.spatial import procrustes
from sklearn.decomposition import PCA

from . import load

VARIANTS = {"A": "floor-CLR", "B": "core-only CLR", "C": "multiplicative-replacement CLR"}
SEEDS = (0, 1, 2)
N_NEIGHBORS = 5
FOCUS = "PCC1_ctrl_r2"
MIN_CORE = 50


def clr(logx: np.ndarray, ref_cols=None) -> np.ndarray:
    ref = logx if ref_cols is None else logx[:, ref_cols]
    return logx - ref.mean(axis=1, keepdims=True)


def variants(scaled: pd.DataFrame, s: pd.Series) -> tuple[dict, int]:
    raw = scaled * s
    raw = raw[(raw > 0).any(axis=1)]
    core = (raw > 0).all(axis=1).to_numpy()

    floors = raw.apply(lambda c: np.percentile(c[c > 0], 1)) / s
    a = np.log(np.maximum((raw / s).to_numpy(), floors.max())).T

    b = np.log(raw[core].to_numpy()).T

    p = (raw / raw.sum()).to_numpy()
    delta = 0.5 * np.where(p > 0, p, np.inf).min(axis=0)
    nz = p > 0
    p = np.where(nz, p * (1 - (~nz).sum(axis=0) * delta), delta)
    c = np.log(p).T

    return {"A": clr(a, core), "B": clr(b), "C": clr(c)}, int(core.sum())


def embed(x: np.ndarray, seed: int) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return umap.UMAP(n_neighbors=N_NEIGHBORS, random_state=seed).fit_transform(x)


def focus_report(x: np.ndarray, ids: list) -> dict:
    d = np.linalg.norm(x[:, None] - x[None], axis=2)
    i = ids.index(FOCUS)
    order = [ids[j] for j in np.argsort(d[i]) if j != i]
    mean_to = {g: float(np.mean([d[i, ids.index(f"{g}_r{r}")] for r in (1, 2, 3) if f"{g}_r{r}" != FOCUS]))
               for g in ("PCC1_ctrl", "EPI300_ctrl")}
    return {"nearest": order[:3], "mean_dist": {k: round(v, 2) for k, v in mean_to.items()},
            "closer_to": min(mean_to, key=mean_to.get)}


def run(tables: dict) -> dict:
    coords, checks = [], {}
    for obs, (inj, scaled) in tables.items():
        smp = inj[inj.sample_type == "sample"].sort_values(["strain", "treatment", "replicate"])
        ids = smp.sample_id.tolist()
        xs, n_core = variants(scaled[ids], smp.set_index("sample_id").size_factor[ids])
        ck = {"core": n_core, "core_flag": n_core < MIN_CORE, "variants": {}}
        pcs = {}
        for v, x in xs.items():
            pca = PCA(n_components=2, svd_solver="full").fit(x)
            pcs[v] = pca.transform(x)
            ums = [embed(x, sd) for sd in SEEDS]
            for method, xy in (("PCA", pcs[v]), ("UMAP", ums[0])):
                coords.append(smp[["sample_id", "strain", "strain_recorded", "treatment", "replicate"]]
                              .assign(observation=obs, variant=v, method=method, x=xy[:, 0], y=xy[:, 1]))
            ck["variants"][v] = {
                "n_features": x.shape[1],
                "pca_var": [round(float(e), 4) for e in pca.explained_variance_ratio_],
                "focus": focus_report(x, ids),
                "umap_seed_disparity": [round(float(procrustes(ums[0], u)[2]), 3) for u in ums[1:]],
            }
        ck["procrustes_pca"] = {f"{a}-{b}": round(float(procrustes(pcs[a], pcs[b])[2]), 3)
                                for a, b in (("A", "B"), ("A", "C"), ("B", "C"))}
        checks[obs] = ck
    load.save(pd.concat(coords), load.OUT / "ordination.parquet")
    return checks

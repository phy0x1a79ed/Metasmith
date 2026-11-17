"""Match ion reads across one observation's injections into species and write the raw abundance table."""
import itertools

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import min_weight_full_bipartite_matching
from scipy.spatial import cKDTree
from sklearn.metrics import adjusted_rand_score

from . import errors, load

MAX_ITER = 10
CONVERGED = 0.005


class Matcher:
    def __init__(self, reads: pd.DataFrame, sigma: np.ndarray, cutoff: float):
        self.reads = reads.reset_index(drop=True)
        self.sigma, self.cutoff = sigma, cutoff
        self.injections = self.reads.injection.value_counts().index.tolist()
        self.rows = {i: np.flatnonzero(self.reads.injection == i) for i in self.injections}
        self.raw = errors.coords(self.reads) / sigma
        self.offsets = pd.DataFrame(0.0, index=self.injections, columns=errors.DIMS)
        self.species = np.full(len(self.reads), -1)

    def x(self, rows):
        inj = self.reads.injection.values[rows]
        return self.raw[rows] - self.offsets.loc[inj].to_numpy() / self.sigma

    def assign(self, rows, centroids):
        """One-to-one reads -> centroids; each read may instead open a new species at cost `cutoff`."""
        x = self.x(rows)
        n, m = len(rows), len(centroids)
        cand = cKDTree(centroids).query_ball_point(x, np.sqrt(self.cutoff)) if m else [[] for _ in rows]
        r = np.repeat(np.arange(n), [len(c) for c in cand])
        c = np.concatenate([np.asarray(c, int) for c in cand]) if len(r) else np.zeros(0, int)
        w = ((x[r] - centroids[c]) ** 2).sum(1) + 1e-9
        g = csr_matrix((np.r_[w, np.full(n, self.cutoff)], (np.r_[r, np.arange(n)], np.r_[c, m + np.arange(n)])),
                       shape=(n, m + n))
        row, col = min_weight_full_bipartite_matching(g)
        assert (row == np.arange(n)).all()
        new = col >= m
        out = col.copy()
        out[new] = m + np.arange(new.sum())
        return out, x[new]

    def sweep(self, centroids):
        species = np.full(len(self.reads), -1)
        for inj in self.injections:
            rows = self.rows[inj]
            col, opened = self.assign(rows, centroids)
            species[rows] = col
            centroids = np.vstack([centroids, opened]) if len(opened) else centroids
        return species

    def refit(self):
        x = self.x(np.arange(len(self.reads)))
        df = pd.DataFrame(x, columns=errors.DIMS).assign(s=self.species, inj=self.reads.injection.values)
        cen = df.groupby("s")[errors.DIMS].median()
        resid = df[errors.DIMS] - cen.loc[df.s].to_numpy()
        multi = df.s.map(df.s.value_counts()) >= 3
        shift = resid[multi].groupby(df.inj[multi]).median() * self.sigma
        shift -= shift.mean()
        self.offsets = self.offsets.add(shift, fill_value=0)
        return cen

    def relabel(self, species):
        _, self.species = np.unique(species, return_inverse=True)

    def run(self):
        self.relabel(self.sweep(np.zeros((0, 3))))
        history = []
        for _ in range(MAX_ITER):
            cen = self.refit()
            prev = self.species.copy()
            self.relabel(self.sweep(cen.to_numpy()))
            history.append(1 - adjusted_rand_score(prev, self.species))
            if history[-1] < CONVERGED:
                break
        merged = self.merge_split()
        self.refit()
        self.relabel(self.sweep(self.refit().to_numpy()))
        return {"iterations": len(history), "change_by_iter": [round(h, 5) for h in history], "merged": merged}

    def merge_split(self):
        """Merge centroid pairs inside the cutoff that never share an injection (MZmine split peaks)."""
        cen = self.refit()
        present = pd.crosstab(self.species, self.reads.injection.values).astype(bool)
        pairs = cKDTree(cen.to_numpy()).query_pairs(np.sqrt(self.cutoff), output_type="ndarray")
        d = ((cen.to_numpy()[pairs[:, 0]] - cen.to_numpy()[pairs[:, 1]]) ** 2).sum(1)
        parent = np.arange(len(cen))
        members = {i: present.iloc[i].to_numpy() for i in range(len(cen))}

        def root(i):
            while parent[i] != i:
                i = parent[i]
            return i

        n = 0
        for a, b in pairs[np.argsort(d)]:
            ra, rb = root(a), root(b)
            if ra != rb and not (members[ra] & members[rb]).any():
                parent[rb] = ra
                members[ra] = members[ra] | members[rb]
                n += 1
        self.relabel(np.array([root(s) for s in self.species]))
        return n


def build(reads: pd.DataFrame, model: dict) -> tuple[Matcher, dict]:
    m = Matcher(reads, np.array([model["sigma"][k] for k in errors.DIMS]), model["d2_cutoff"])
    return m, m.run()


def species_table(m: Matcher, observation: str):
    x = m.x(np.arange(len(m.reads))) * m.sigma
    df = pd.DataFrame(x, columns=["lmz", "rt", "lmob"]).assign(species=m.species)
    cen = df.groupby("species").agg(lmz=("lmz", "median"), rt=("rt", "median"), lmob=("lmob", "median"),
                                    n_reads=("rt", "size"))
    order = cen.lmz.sort_values().index
    sid = pd.Series([f"{observation}_{i:05d}" for i in range(len(order))], index=order)
    sp = pd.DataFrame({"species_id": sid.loc[cen.index].values, "mz": np.exp(cen.lmz.values / 1e6),
                       "rt": cen.rt.values, "mobility": np.exp(cen.lmob.values / 100), "n_reads": cen.n_reads.values})
    resid = (df[["lmz", "rt", "lmob"]] - cen.loc[df.species, ["lmz", "rt", "lmob"]].to_numpy()).to_numpy()
    reads = m.reads[["injection", "ion_id", "mz", "rt", "mobility", "height", "area"]].assign(
        species_id=sid.loc[m.species].values, d2=((resid / m.sigma) ** 2).sum(1))
    return sp.sort_values("species_id").reset_index(drop=True), reads, resid


def checks(m, observation, o, sp, reads, resid, log):
    kind = reads.injection.map(o.set_index("injection").sample_type)
    multi = (reads.species_id.map(sp.set_index("species_id").n_reads) >= 3).values
    spread = {k: dict(zip(errors.DIMS, errors.robust_sigma(resid[(kind == k).values & multi]).round(5).tolist()))
              for k in ("qc", "sample")}
    near = sp[load.cuda_mask(sp, load.OBSERVATIONS[observation][1])].species_id
    cuda = reads[reads.species_id.isin(near)].groupby("species_id").injection.nunique()
    qc_ids = o[o.sample_type == "qc"].injection.tolist()
    qsets = {i: set(reads.species_id[reads.injection == i]) for i in qc_ids}
    pair = [len(qsets[a] & qsets[b]) / np.mean([len(qsets[a]), len(qsets[b])])
            for a, b in itertools.combinations(qc_ids, 2)]
    return {
        **log,
        "injections": o.sample_type.value_counts().to_dict(),
        "n_species": len(sp),
        "duplicate_read_per_injection": int(reads.duplicated(["injection", "species_id"]).sum()),
        "cuda_species_detected_in": cuda.to_dict(),
        "n_injections": int(reads.injection.nunique()),
        "qc_pair_shared_frac": round(float(np.mean(pair)), 4),
        "resid_sigma": spread,
        "offset_range": dict(zip(errors.DIMS, np.ptp(m.offsets.to_numpy(), axis=0).round(4).tolist())),
    }


def write(observation: str, o: pd.DataFrame, reads: pd.DataFrame, model: dict):
    m, log = build(reads, model)
    sp, read_map, resid = species_table(m, observation)
    oi = o.set_index("injection")
    raw = read_map.pivot_table(index="species_id", columns="injection", values="area", aggfunc="sum", fill_value=0)
    raw = raw.reindex(index=sp.species_id, columns=oi.index, fill_value=0).rename(columns=oi.sample_id)
    inj = o[["injection", "sample_id", "sample_type", "strain", "strain_recorded", "treatment", "replicate",
             "run_id", "filename"]].merge(m.offsets.rename_axis("injection").reset_index(), on="injection")
    out = load.OUT / observation
    load.save(raw.reset_index(), out / "abundance_raw.parquet")
    load.save(read_map, out / "read_map.parquet")
    load.save(sp, out / "species.parquet")
    return inj, sp, read_map, raw, checks(m, observation, o, sp, read_map, resid, log)

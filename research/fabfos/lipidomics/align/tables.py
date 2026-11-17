"""Blank-filter each observation's species, write relative and size-factor-scaled tables, and the per-species feature file with pooled MS2."""
import numpy as np
import pandas as pd

from . import load

BLANK_RATIO = 3.0
MS2_PPM = 10.0


def size_factors(kept: pd.DataFrame, qc_cols) -> pd.Series:
    qc = kept[qc_cols].where(kept[qc_cols] > 0)
    ref = qc.median(axis=1).where(qc.notna().sum(axis=1) >= 2)
    ratio = kept.div(ref, axis=0).where(kept > 0)
    return ratio.median()


def pool_ms2(spectra: pd.DataFrame) -> dict:
    peaks = []
    for k, s in enumerate(spectra.itertuples()):
        mz, it = np.asarray(s.mz, float), np.asarray(s.intensity, float)
        if len(mz) and it.max() > 0:
            peaks.append(np.c_[mz, it / it.max(), np.full(len(mz), k)])
    if not peaks:
        return {"ms2_mz": [], "ms2_intensity": [], "ms2_n_reads": []}
    p = np.vstack(peaks)
    p = p[np.argsort(p[:, 0])]
    start = np.r_[True, np.diff(np.log(p[:, 0])) * 1e6 > MS2_PPM]
    grp = np.cumsum(start) - 1
    df = pd.DataFrame({"g": grp, "mz": p[:, 0], "i": p[:, 1], "read": p[:, 2]})
    df["w"] = df.mz * df.i
    agg = df.groupby("g").agg(w=("w", "sum"), isum=("i", "sum"), i=("i", "max"), n=("read", "nunique"))
    agg = agg[agg.n >= min(2, len(spectra))]
    return {"ms2_mz": (agg.w / agg.isum).round(5).tolist(), "ms2_intensity": agg.i.round(4).tolist(),
            "ms2_n_reads": agg.n.astype(int).tolist()}


def features(obs, all_inj, ions, sp, reads, raw, groups):
    ions = ions[["injection", "ion_id", "ccs", "charge", "isotopes"]]
    r = reads.merge(ions, on=["injection", "ion_id"], how="left").merge(sp[["species_id", "mz", "rt", "mobility"]],
                                                                     on="species_id", suffixes=("", "_c"))
    r["d_ppm"] = np.log(r.mz / r.mz_c) * 1e6
    r["d_rt"] = r.rt - r.rt_c
    r["d_mob"] = np.log(r.mobility / r.mobility_c) * 100
    r["isotopes"] = pd.to_numeric(r.isotopes, errors="coerce")
    g = r.groupby("species_id")
    f = sp.set_index("species_id").join(pd.DataFrame({
        "ccs": g.ccs.median(),
        "sd_ppm": g.d_ppm.std(), "sd_rt": g.d_rt.std(), "sd_mob_pct": g.d_mob.std(),
        "charge": g.charge.agg(lambda c: c.mode().iloc[0] if c.notna().any() else pd.NA).astype("Int8"),
        "isotopes": g.isotopes.median(),
    }))
    for name, cols in groups.items():
        f[f"n_{name}"] = (raw[cols] > 0).sum(axis=1)
    f["mean_sample"] = raw[groups["sample"]].mean(axis=1)
    f["mean_blank"] = raw[groups["blank"]].mean(axis=1)
    f["blank_ratio"] = f.mean_sample / f.mean_blank.replace(0, np.nan)
    f["kept"] = f.blank_ratio.isna() & (f.mean_sample > 0) | (f.blank_ratio >= BLANK_RATIO)

    ms2 = load.reads("ms2", all_inj, obs).merge(reads[["injection", "ion_id", "species_id"]], on=["injection", "ion_id"])
    pooled = {}
    for sid, s in ms2.groupby("species_id"):
        pooled[sid] = {**pool_ms2(s), "ms2_reads": (s.injection + ":" + s.ion_id.astype(str)).tolist(),
                       "ms2_collision_energy": sorted(set(s.collision_energy.dropna()))}
    pooled = pd.DataFrame.from_dict(pooled, orient="index")
    return f.join(pooled).reset_index()


def write(obs: str, all_inj, ions, inj, sp, reads, raw):
    by = inj.groupby("sample_type").sample_id.apply(list)
    groups = {t: by[t] for t in ("sample", "qc", "blank")}
    f = features(obs, all_inj, ions, sp, reads, raw, groups)

    kept = raw.loc[f.species_id[f.kept], groups["sample"] + groups["qc"]]
    rel = kept / kept.sum()
    s = size_factors(kept, groups["qc"])
    scaled = kept / s
    inj = inj.assign(size_factor=inj.sample_id.map(s))

    d = load.OUT / obs
    load.save(f, d / "features.parquet")
    load.save(rel.reset_index(), d / "abundance_rel.parquet")
    load.save(scaled.reset_index(), d / "abundance_scaled.parquet")
    load.save(inj, d / "injections.parquet")

    smp = s[groups["sample"]]
    chk = {"species_raw": len(f), "species_kept": int(f.kept.sum()),
           "blank_only_or_low_ratio": int((~f.kept).sum()),
           "kept_with_ms2": int(f.loc[f.kept, "ms2_mz"].map(lambda m: isinstance(m, list) and len(m) > 0).sum()),
           "size_factor_range_samples": [round(float(smp.min()), 3), round(float(smp.max()), 3)],
           "size_factor_range_qc": [round(float(s[groups["qc"]].min()), 3), round(float(s[groups["qc"]].max()), 3)],
           "rel_column_sums_ok": bool(np.allclose(rel.sum(), 1))}
    return inj, scaled, chk

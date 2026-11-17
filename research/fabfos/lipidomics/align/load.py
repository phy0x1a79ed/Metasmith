"""Load the per-injection Parquet set with the one strain rename, and check the design per observation."""
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[4]
PARQUET = ROOT / "data/fabfos/runs/scadc_mzmine_parquet_v1"
STRAIN = {"Epi300": "EPI300", "ESi300": "EPI300", "EpCC1": "EpCC1", "ESCC1": "EpCC1",
          "Clone1": "Clone1", "Clone2": "Clone2"}
OBSERVATIONS = {"pel_pos": ("P", "POS"), "pel_neg": ("P", "NEG"),
                "sup_pos": ("S", "POS"), "sup_neg": ("S", "NEG")}
LABEL = {"pel_pos": "pel+", "pel_neg": "pel−", "sup_pos": "sup+", "sup_neg": "sup−"}
N_BLANKS = {"P": 4, "S": 8}


def injections() -> pd.DataFrame:
    inj = pd.read_parquet(PARQUET / "injections.parquet")
    inj["strain_recorded"] = inj.strain
    inj["strain"] = inj.strain.map(STRAIN)
    unmapped = inj[inj.strain_recorded.notna() & inj.strain.isna()]
    if len(unmapped):
        raise SystemExit(f"strain labels with no rename: {sorted(unmapped.strain_recorded.unique())}")
    obs_of = {v: k for k, v in OBSERVATIONS.items()}
    inj["observation"] = [obs_of[(f, p)] for f, p in zip(inj.fraction, inj.polarity)]
    inj["sample_id"] = inj.apply(_sample_id, axis=1)
    _check_design(inj)
    return inj


def _sample_id(r) -> str:
    if r.sample_type == "sample":
        return f"{r.strain}_{r.treatment}_r{r.replicate}"
    if r.sample_type == "qc":
        return f"QC_r{r.replicate}"
    return f"blank_{r.treatment}_r{r.replicate}"


def _check_design(inj: pd.DataFrame):
    bad = []
    for obs, (frac, _) in OBSERVATIONS.items():
        o = inj[inj.observation == obs]
        s = o[o.sample_type == "sample"]
        reps = s.groupby(["strain", "treatment"]).replicate.apply(lambda r: sorted(r)) 
        if len(reps) != 8 or any(r != [1, 2, 3] for r in reps):
            bad.append(f"{obs}: conditions/replicates {reps.to_dict()}")
        if (o.sample_type == "qc").sum() != 4:
            bad.append(f"{obs}: {(o.sample_type == 'qc').sum()} QCs")
        if (o.sample_type == "blank").sum() != N_BLANKS[frac]:
            bad.append(f"{obs}: {(o.sample_type == 'blank').sum()} blanks")
        if o.sample_id.duplicated().any():
            bad.append(f"{obs}: duplicate sample_id {o.sample_id[o.sample_id.duplicated()].tolist()}")
    if bad:
        raise SystemExit("design check failed:\n  " + "\n  ".join(bad))


def _read(kind: str, inj: pd.DataFrame, observation: str) -> pd.DataFrame:
    o = inj[inj.observation == observation]
    pol = OBSERVATIONS[observation][1]
    t = ds.dataset(PARQUET / kind, partitioning="hive").to_table(
        filter=(ds.field("polarity") == pol) & ds.field("injection").isin(o.injection.tolist()))
    return t.to_pandas().drop(columns="polarity").astype({"injection": str})


def ions(inj: pd.DataFrame, observation: str) -> pd.DataFrame:
    return _read("ions", inj, observation)


def ms2(inj: pd.DataFrame, observation: str) -> pd.DataFrame:
    return _read("ms2", inj, observation)


if __name__ == "__main__":
    inj = injections()
    s = inj[inj.sample_type == "sample"]
    print("rename (recorded -> used), by fraction:")
    print(s.groupby(["strain_recorded", "strain", "fraction"]).size().rename("injections").to_string())
    print("\ninjections per observation:")
    print(inj.groupby(["observation", "sample_type"]).size().unstack().to_string())
    for obs in OBSERVATIONS:
        print(obs, len(ions(inj, obs)), "reads", len(ms2(inj, obs)), "MS2")

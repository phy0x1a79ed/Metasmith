"""MS2Lipid subclass prediction over every consensus MS/MS spectrum, both polarities.

MS2Lipid (Sakamoto, Tsugawa et al., *Metabolites* 2024, 14(11):602,
doi 10.3390/metabo14110602; MIT) predicts among 97 lipid subclasses from an MS/MS
spectrum plus its precursor m/z, using the *same* published model in either ion
mode. That is the property this lane is built on: one method, two polarities, a
citation instead of an in-house fit.

Input is already on disk -- `spectra/full_consensus_ms2.json` (1769 consensus
spectra) and `full_manifest.csv` (precursor m/z, resolved adduct, polarity).
Nothing is re-extracted from mzML.

Writes `identification/ms2lipid_predictions.csv`, one row per spectrum-bearing
feature. It carries the winning subclass, its probability, the full candidate
string, and the citation -- the citation travels in the table, not only in prose.

Env: ms2lipid.  Run:  mamba run -n ms2lipid python research/fabfos/lipidomics/identify/ms2lipid_lane.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

CITATION = "Sakamoto et al. Metabolites 2024;14(11):602 doi:10.3390/metabo14110602 (MS2Lipid v0.1.8)"

# The Zenodo record the package fetches at run time, pinned and cached here so a
# run is reproducible and offline. Left unpinned, `predclass` shells out to
# `zenodo_get` on EVERY call and drops model_data.zip into the current working
# directory -- see `predict()` for why we bypass that path.
ZENODO_DOI = "10.5281/zenodo.13893001"
MODEL_DIR = common.CACHE_DIR / "ms2lipid"      # contains model_data/{positive,negative}/

SPECTRA_JSON = common.SPECTRA_DIR / "full_consensus_ms2.json"
OUT_CSV = common.IDENT_DIR / "ms2lipid_predictions.csv"

# Minimum peaks in the consensus spectrum for a feature to be offered to the model.
# 1 keeps every spectrum-bearing feature (81.1% of the table); 3 and 5 cost 98 and
# 188 features respectively. Kept at 1 deliberately: two of the three blind
# controls carry 13 and 7 peaks, and a floor of 5 would drop one of them silently.
# The peak count rides along in the output so the floor can be re-cut downstream
# without re-running the model.
MIN_PEAKS = 1

# MS2Lipid is closed-world over its 97 subclasses: handed a non-lipid it still
# returns a subclass. Nothing here abstains on that basis -- the probability
# column is exported raw and the floor is applied by the consumer
# (`membrane_ms2.py`), so changing the floor never means re-running the model.
POLARITY_IONMODE = {"pos": "positive", "neg": "negative"}


def spectrum_string(peaks: list[list[float]], precursor: float) -> str:
    """MS2Lipid's spectrum encoding: space-separated `mz:intensity` pairs.

    Undocumented on PyPI and GitHub; read off `__wide_spectrum` in the installed
    package. Peaks are binned to integer m/z and max-normalised inside the model,
    so no rounding or scaling is done here.

    Peaks **above the precursor are dropped**, and that is not cosmetic. Our
    consensus spectra keep them -- 27.3% of all peaks, in 1367 of 1769 features --
    because DDA-PASEF co-isolates neighbours in a wide window and the consensus
    builder never truncated at the precursor. MS2Lipid's neutral-loss encoder
    assumes it can only ever see losses, so a fragment above the precursor makes
    it create a positive column that collides with the fragment table and
    silently corrupts the design matrix (it surfaces as a feature-shape
    mismatch, 2060 columns where the model wants 1367). The model was trained on
    MS-DIAL-deconvoluted spectra, where those peaks are already gone; removing
    them puts our input in the distribution the published accuracy was measured
    on rather than outside it.
    """
    return " ".join(f"{mz}:{inten}" for mz, inten in peaks
                    if round(mz - precursor) <= 0)


def build_inputs() -> pd.DataFrame:
    """One row per spectrum-bearing feature, with the columns MS2Lipid wants."""
    spectra = json.loads(SPECTRA_JSON.read_text())
    man = pd.read_csv(common.IDENT_DIR / "full_manifest.csv")

    mz_by_id = man.set_index("feature_id").mz
    rows = []
    for fid, rec in spectra.items():
        peaks = rec.get("peaks") or []
        prec = mz_by_id.get(fid)
        if prec is None:
            continue
        s = spectrum_string(peaks, float(prec))
        rows.append({"feature_id": fid,
                     "n_peaks_raw": len(peaks),
                     "n_peaks_consensus": len(s.split()) if s else 0,
                     "n_scans": rec.get("n_scans"),
                     "MS/MS spectrum": s})
    spec = pd.DataFrame(rows)

    d = man[["feature_id", "mz", "rt", "polarity", "adduct", "is_control",
             "mean_bio_abundance"]].merge(spec, on="feature_id", how="inner")
    # The manifest m/z IS the deconvoluted precursor (it is what the adduct
    # arithmetic in common.py closes on), not the isolation-window centre.
    # MS2Lipid's accuracy is stated as sensitive to precursor accuracy, so this
    # distinction is the one that matters.
    d = d.rename(columns={"mz": "Average Mz"})
    d["Alignment ID"] = d.feature_id
    d = d[d.n_peaks_consensus >= MIN_PEAKS].reset_index(drop=True)

    # The model bins fragments into 1..1250 m/z and neutral losses into 0..-1250.
    # A spectrum with nothing inside BOTH windows makes an all-zero row and
    # crashes the package's max-normalisation. Features left with no peak at or
    # below the precursor, and features whose only peak is above m/z 1250, have
    # no model input at all and abstain rather than be handed a garbage row.
    keep = [in_model_window(pk, mz)
            for pk, mz in zip(d["MS/MS spectrum"], d["Average Mz"])]
    dropped = int(len(d) - sum(keep))
    if dropped:
        print(f"[abstain] {dropped} feature(s) have no peak inside the model's "
              f"m/z window: " + ",".join(d.feature_id[[not k for k in keep]]))
    return d[keep].reset_index(drop=True)


def in_model_window(spectrum: str, precursor: float) -> bool:
    """Does this spectrum survive MS2Lipid's binning with at least one peak?

    Mirrors `__wide_spectrum` / `__wide_neulloss`: fragments round into
    [1, 1250], neutral losses into [-1250, 0].
    """
    for pair in spectrum.split(" "):
        if ":" not in pair:
            continue
        mz = float(pair.rsplit(":", 1)[0])
        if round(mz) <= 1250 and round(mz - precursor) >= -1250:
            return True
    return False


def predict(d: pd.DataFrame, polarity: str) -> pd.DataFrame:
    """Run the published model over one polarity's spectra.

    Calls MS2Lipid's own table-building and prediction functions rather than
    `predclass`, for one reason only: `predclass` re-downloads the 3.3 MB Zenodo
    model on every invocation and writes the zip into the caller's cwd. The
    feature construction and the model are the package's, unmodified.
    """
    import ms2lipid.ms2lipid as M

    load_models = getattr(M, "__load_models")
    make_table = getattr(M, "__make_table")
    pred_class = getattr(M, "__pred_class")

    sub = d[d.polarity == polarity].reset_index(drop=True)
    if sub.empty:
        return pd.DataFrame()

    tmp = common.CACHE_DIR / f"ms2lipid_input_{polarity}.csv"
    sub[["MS/MS spectrum", "Average Mz", "Alignment ID"]].to_csv(tmp, index=False)

    model, model_column, replacement = load_models(
        str(MODEL_DIR), ionmode=POLARITY_IONMODE[polarity])
    df, df_data = make_table(str(tmp))
    # threshold=0 keeps every class in the candidate string, so the top
    # probability is always recoverable even when the model is unsure.
    out = pred_class(df, df_data, replacement, model_column, model, threshold=0)

    out = out.rename(columns={"ID": "feature_id"})
    top = out.predict_candidateclass.map(parse_top_prob)
    res = pd.DataFrame({
        "feature_id": out.feature_id.values,
        "ms2lipid_class": out.predict_1class.values,
        "ms2lipid_p": top.values,
        "ms2lipid_candidates": out.predict_candidateclass.map(top_n_candidates).values,
    })
    return sub[["feature_id", "polarity", "Average Mz", "rt", "adduct",
                "n_peaks_raw", "n_peaks_consensus", "n_scans", "is_control",
                "mean_bio_abundance"]].merge(res, on="feature_id", how="left")


def parse_top_prob(s: object) -> float | None:
    """First entry of MS2Lipid's `predict_candidateclass` string, as a fraction.

    The string is `CLASS:pp.p%,CLASS:pp.p%,...` sorted descending, so the head is
    the winning class's probability.
    """
    if not isinstance(s, str) or not s:
        return None
    head = s.split(",")[0]
    if ":" not in head:
        return None
    return float(head.rsplit(":", 1)[1].rstrip("%")) / 100.0


def top_n_candidates(s: object, n: int = 5) -> str:
    return ",".join(s.split(",")[:n]) if isinstance(s, str) else ""


def main() -> None:
    if not (MODEL_DIR / "model_data").is_dir():
        raise SystemExit(
            f"MS2Lipid model not cached at {MODEL_DIR}. Fetch it once with:\n"
            f"  cd {MODEL_DIR} && mamba run -n ms2lipid python -m zenodo_get {ZENODO_DOI}"
            f" && unzip -o model_data.zip")

    d = build_inputs()
    print(f"[input] {len(d)} spectrum-bearing features "
          f"(>= {MIN_PEAKS} peak): " + ", ".join(
              f"{p} {n}" for p, n in d.polarity.value_counts().items()))

    parts = [predict(d, p) for p in ("pos", "neg")]
    out = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    out["ms2lipid_citation"] = CITATION
    out["ms2lipid_zenodo"] = ZENODO_DOI
    out = out.rename(columns={"Average Mz": "mz"})
    out.to_csv(OUT_CSV, index=False)

    print(f"[write] {OUT_CSV}  ({len(out)} rows)")
    print("\n[top classes]")
    print(out.groupby("polarity").ms2lipid_class.value_counts().groupby(
        level=0).head(8).to_string())
    print("\n[probability distribution]")
    print(out.groupby("polarity").ms2lipid_p.describe().to_string())


if __name__ == "__main__":
    main()

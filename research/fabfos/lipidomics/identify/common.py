"""Paths, adduct arithmetic and small shared helpers for the identification lane.

Paths come from `lipidio` constants, never from literals — thirteen scripts in
this directory still carry the pre-reorganisation `data/fabfos/runs/scadc_lipidomics/` path and
silently write nowhere.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lipidio  # noqa: E402

PROJECT = lipidio.PROJECT
PROCESSED = lipidio.PROCESSED
METABOSCAPE_DIR = lipidio.METABOSCAPE_DIR

IDENT_DIR = PROCESSED / "identification"
CACHE_DIR = IDENT_DIR / "cache"
SPECTRA_DIR = IDENT_DIR / "spectra"

PUBLISH_DIR = PROJECT / ".awm/data/figures/publish/04_lipidomics/06_identification"
HITS_CSV = (
    PROJECT
    / ".awm/data/figures/publish/04_lipidomics/05_clone_response"
    / "clone_response_storey_hits.csv"
)
REFMET_DB = PROJECT / "data/fabfos/runs/scadc_lipidomics/refmet/refmet_db.csv"

MZML_DIR = {"pos": PROCESSED / "pos/mzml", "neg": PROCESSED / "neg/mzml"}

# The three features that already carry an identity. They are run blind through
# the same pipeline as the other 26; recovering them is the lane's positive
# control, so their known answers are recorded here and nowhere else.
CONTROL_FEATURES = {
    "F0021": {"name": "HBMP14:0_16:1_16:0", "class": "HBMP", "expect_level": 2},
    "F0025": {"name": "HBMP16:1_18:1_16:0", "class": "HBMP", "expect_level": 2},
    "F0161": {"name": "PS(18:3/16:0)", "class": "PS", "expect_level": 3},
}

ELECTRON = 0.000548580
PROTON = 1.007276467

# m/z = (M + delta) / charge. Deltas are electron-corrected.
ADDUCTS: dict[str, tuple[float, int]] = {
    "[M+H]+": (PROTON, 1),
    "[M+Na]+": (22.989769282 - ELECTRON, 1),
    "[M+K]+": (38.963706486 - ELECTRON, 1),
    "[M+NH4]+": (18.034374128 - ELECTRON, 1),
    "[M+H-H2O]+": (PROTON - 18.010564684, 1),
    "[M+2H]2+": (2 * PROTON, 2),
    "[M-H]-": (-PROTON, 1),
    "[M+Cl]-": (34.968852682 + ELECTRON, 1),
    "[M+CHOO]-": (44.997654657 + ELECTRON, 1),
    "[M+CH3COO]-": (59.013304721 + ELECTRON, 1),
    "[M-H-H2O]-": (-PROTON - 18.010564684, 1),
    "[M-2H]2-": (-2 * PROTON, 2),
    # MetaboScape spells two of these more than one way across the full table.
    # The 29 hits happened to use only the first spelling; over all 2180 features
    # the variants account for 27 otherwise-unresolvable adducts.
    "[M+HCOO]-": (44.997654657 + ELECTRON, 1),
    "[M+H+H]2+": (2 * PROTON, 2),
}

_RUN_RE = re.compile(r"^(?P<core>.*?)(?P<stem>\d*)_\[POS\](?P<pos>\d+)\.d_\[NEG\](?P<neg>\d+)\.d$")


def adduct_polarity(adduct: str) -> str:
    """'pos' or 'neg' from the trailing sign of an adduct string."""
    return "neg" if adduct.rstrip().endswith("-") else "pos"


def mz_for(neutral_mass: float, adduct: str) -> float | None:
    spec = ADDUCTS.get(adduct)
    if spec is None:
        return None
    delta, charge = spec
    return (neutral_mass + delta) / charge


def parse_ions(ions: object) -> list[str]:
    """Split MetaboScape's `Ions` cell into a deduplicated, order-preserving list.

    One hit repeats `[M-H]-` seven times in a single cell; another lists three
    distinct adducts. Both must come out clean.
    """
    if not isinstance(ions, str):
        return []
    out, seen = [], set()
    for tok in ions.split(","):
        tok = tok.strip()
        if tok and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def resolve_adduct(mz: float, neutral_mass: float, ions: list[str],
                   tol_da: float = 0.01) -> tuple[str | None, float | None]:
    """Pick which listed adduct actually produced the measured m/z.

    MetaboScape reports one measured m/z but may list several adducts for the
    feature; the neutral mass is its own deconvolution. Assuming protonation
    silently corrupts the formate and chloride adducts, where the neutral mass
    sits ~45 or ~35 Da below the measurement, so the adduct is resolved rather
    than assumed. Returns (adduct, error_in_da) or (None, None) if nothing in
    the list reproduces the measurement.
    """
    best, best_err = None, None
    for ad in ions:
        pred = mz_for(neutral_mass, ad)
        if pred is None:
            continue
        err = mz - pred
        if best_err is None or abs(err) < abs(best_err):
            best, best_err = ad, err
    if best_err is None or abs(best_err) > tol_da:
        return None, best_err
    return best, best_err


def parse_sample_runs(header: str) -> tuple[str, str] | None:
    """Recover the POS and NEG raw-run numbers from a MetaboScape sample header.

    Headers end `..._1_158_[POS]02.d_[NEG]76.d`, where the run number is split
    across the prefix and the bracketed suffix — POS 15802, NEG 15876 here. The
    split point moves between columns, so it is recovered rather than assumed.
    The reassembled number is the mzML filename stem.
    """
    m = _RUN_RE.match(str(header).strip())
    if not m:
        return None
    stem = m["stem"]
    return stem + m["pos"], stem + m["neg"]


def ppm(observed: float, reference: float) -> float:
    return (observed - reference) / reference * 1e6


# Every evidence stream emits rows in this shape so the merge in T4 is a concat
# rather than a reconciliation.
CANDIDATE_COLS = [
    "feature_id", "evidence_source", "candidate_name", "formula", "lipid_class",
    "super_class", "main_class", "sub_class", "exactmass", "ppm_error",
    "ms2_cosine", "ms2_matched_peaks", "external_ids", "notes",
]


def candidate_row(feature_id: str, evidence_source: str, **kw) -> dict:
    row = {c: None for c in CANDIDATE_COLS}
    row["feature_id"] = feature_id
    row["evidence_source"] = evidence_source
    unknown = set(kw) - set(CANDIDATE_COLS)
    if unknown:
        raise KeyError(f"not candidate columns: {sorted(unknown)}")
    row.update(kw)
    return row


def ensure_dirs() -> None:
    for d in (IDENT_DIR, CACHE_DIR, SPECTRA_DIR):
        d.mkdir(parents=True, exist_ok=True)

"""Shared loaders for the lipidomics feature table + sample metadata.

MS-DIAL 5 alignment exports use these columns:
  - feature-level: `Alignment ID`, `Average Rt(min)`, `Average Mz`,
    `Metabolite name`, `Adduct type`, `Average Mobility`, `Average CCS`
  - per-sample columns named with the sample basename (no suffix)

We also keep a fallback for the older MZmine 4 modular CSV format
(`<basename>:area` per-sample columns + lowercase feature columns) so legacy
smoke outputs still parse.

Column resolution is heuristic — preferred names first, substring fallback.
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[3]
PROCESSED = PROJECT / "data/fabfos/runs/scadc_lipidomics/processed"
META_CSV = PROJECT / "research/fabfos/lipidomics/metadata.csv"

# --- MetaboScape facility deliverable -------------------------------------------
# The MS facility's Bruker MetaboScape merged table (POS+NEG already merged per
# feature, annotated against MetaboBASE/NIST/HMDB/LipidBlast). This is the usable
# dataset — the autonomous MS-DIAL pipeline produced near-empty output.
METABOSCAPE_DIR = PROCESSED / "metaboscape"
METABOSCAPE_XLSX_CANDIDATES = [
    PROJECT / "data/fabfos/runs/scadc_lipidomics/facility/metaboscape_merged.xlsx",
    Path("/mnt/a/downloads/Lipidomics Meged Full list Jun 8.xlsx"),
]
# Feature-metadata columns carried from the xlsx (everything that is not a sample).
MS_FEATURE_COLS = [
    "name", "formula", "annotations", "mz", "rt", "ccs", "msms_score",
    "lipid_name", "lipid_class", "total_carbon", "total_db", "is_lipid",
]
MS_FEATURES_CLEAN = METABOSCAPE_DIR / "features_clean.csv"
MS_METADATA_BIO = METABOSCAPE_DIR / "metadata_bio.csv"

STRAINS = ("Epi300", "EpCC1", "ESi300", "ESCC1", "Clone1", "Clone2")

# Sample-header "core" = everything before the `_[POS]…d_[NEG]…d` suffix; it ends
# in `…_1_{run}`. These mirror build_metadata.py but match the core (no `.d`).
_MS_SAMPLE_RE = re.compile(
    rf"^(?P<strain>{'|'.join(STRAINS)})_(?P<tol>Tol_)?(?P<fraction>[PS])_(?P<rep>[123])_"
    rf"(?P<plate>P\d+-[A-Z]-\d+)_1_(?P<run>\d+)$"
)
_MS_QC_RE = re.compile(
    r"^QC\s?(?P<idx>\d+)\s(?P<tag>SN|P)_(?P<plate>P\d+-[A-Z]-\d+)_1_(?P<run>\d+)$"
)
_MS_BLANK_RE = re.compile(
    r"^Blank (?P<idx>\d+)(?: (?P<tag>P|Tol))?_(?P<plate>P\d+-[A-Z]-\d+)_1_(?P<run>\d+)$"
)


def parse_metaboscape_header(header: str) -> dict | None:
    """Parse one MetaboScape sample-column header into a metadata row.

    Returns dict(sample_basename, polarity, sample_type, strain, treatment,
    fraction, replicate) or None if the header is not a recognized sample.
    `sample_basename` is a stable, human-readable key unique across the 66
    columns; `polarity` is always "merged" (POS+NEG are merged per feature).
    """
    core = header.split("_[POS]")[0].strip()
    if m := _MS_SAMPLE_RE.match(core):
        treat = "tol" if m["tol"] else "ctrl"
        return dict(
            sample_basename=f"{m['strain']}_{treat}_{m['fraction']}_{m['rep']}",
            polarity="merged",
            sample_type="sample",
            strain=m["strain"],
            treatment=treat,
            fraction=m["fraction"],
            replicate=int(m["rep"]),
        )
    if m := _MS_QC_RE.match(core):
        frac = "S" if m["tag"] == "SN" else "P"
        return dict(
            sample_basename=f"QC_{frac}_{m['idx']}",
            polarity="merged",
            sample_type="qc",
            strain=None,
            treatment=None,
            fraction=frac,
            replicate=int(m["idx"]),
        )
    if m := _MS_BLANK_RE.match(core):
        tag = m["tag"]
        frac = "P" if tag == "P" else "S"
        treat = "tol" if tag == "Tol" else "ctrl"
        return dict(
            sample_basename=f"Blank_{frac}_{treat}_{m['idx']}",
            polarity="merged",
            sample_type="blank",
            strain=None,
            treatment=treat,
            fraction=frac,
            replicate=int(m["idx"]),
        )
    return None


def _metaboscape_xlsx() -> Path:
    for p in METABOSCAPE_XLSX_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"MetaboScape xlsx not found at any of: {METABOSCAPE_XLSX_CANDIDATES}"
    )


def load_metaboscape(path: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read the facility xlsx (sheet `Clean`).

    Returns (features_meta, abundance_all, sample_meta):
      - features_meta: one row per feature (id `F0001`…), columns = MS_FEATURE_COLS.
      - abundance_all: rows=feature_id × cols=all 66 sample keys (raw intensity,
        gap-filled — 0 means below-detection, not missing).
      - sample_meta: one row per sample column (the 66), parsed via
        parse_metaboscape_header.
    """
    import openpyxl

    path = path or _metaboscape_xlsx()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Clean"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))  # row 2 = header
    header = rows[0]
    data = rows[1:]

    n_meta = 14  # c0..c13 are feature metadata; c14.. are samples
    sample_headers = list(header[n_meta:])
    sample_meta_rows, key_for_col, seen = [], [], set()
    for h in sample_headers:
        parsed = parse_metaboscape_header(str(h))
        if parsed is None:
            raise ValueError(f"unparsed MetaboScape sample header: {h!r}")
        key = parsed["sample_basename"]
        if key in seen:
            raise ValueError(f"duplicate sample key {key!r} from header {h!r}")
        seen.add(key)
        key_for_col.append(key)
        sample_meta_rows.append(parsed)
    sample_meta = pd.DataFrame(sample_meta_rows)

    feat_records, abund_records, ids = [], [], []
    for i, row in enumerate(data):
        fid = f"F{i + 1:04d}"
        ids.append(fid)
        name = row[0]
        sh = parse_shorthand(name)
        ann = row[2]
        feat_records.append({
            "name": name,
            "formula": row[1],
            "annotations": ann,
            "mz": row[7],
            "rt": row[4],
            "ccs": row[5],
            "msms_score": row[13],
            "lipid_name": name,
            "lipid_class": sh["lipid_class"],
            "total_carbon": sh["total_carbon"],
            "total_db": sh["total_db"],
            "is_lipid": bool(sh["lipid_class"]) or (isinstance(ann, str) and "Lipid Species" in ann),
        })
        abund_records.append([row[n_meta + j] for j in range(len(sample_headers))])

    feats = pd.DataFrame(feat_records, index=ids)
    feats.index.name = "feature_id"
    abund = pd.DataFrame(abund_records, index=ids, columns=key_for_col)
    abund = abund.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    abund.index.name = "feature_id"
    return feats, abund, sample_meta


def load_metadata(source: str = "msdial") -> pd.DataFrame:
    if source == "metaboscape":
        return pd.read_csv(MS_METADATA_BIO)
    md = pd.read_csv(META_CSV)
    md["sample_basename"] = md["filename"].str.removesuffix(".d")
    return md


def _first_matching(df: pd.DataFrame, preferred: list[str], substrings: list[str] = ()) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for name in preferred:
        if name.lower() in cols_lower:
            return cols_lower[name.lower()]
    for sub in substrings:
        for c in df.columns:
            if sub.lower() in c.lower():
                return c
    return None


def _annotation_column(df: pd.DataFrame) -> str | None:
    return _first_matching(
        df,
        preferred=["Metabolite name", "MS/MS assigned"],
        substrings=["lipid_annotation", "lipid name", "lipid_name"],
    )


def _sample_columns(df: pd.DataFrame, kind: str, metadata: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    """Return (sample_columns, rename_map) — rename_map turns each into a clean basename."""
    pat = re.compile(rf":{re.escape(kind)}\s*$", re.I)
    legacy = [c for c in df.columns if pat.search(c)]
    if legacy:
        rename = {c: pat.sub("", c).strip() for c in legacy}
        return legacy, rename

    # MS-DIAL: per-sample columns have headers equal to the sample basename.
    basenames = set(metadata["sample_basename"].astype(str).tolist())
    msdial_cols = [c for c in df.columns if c in basenames]
    if msdial_cols:
        return msdial_cols, {c: c for c in msdial_cols}

    return [], {}


def _detect_separator(csv: Path) -> str:
    """MS-DIAL writes tab-separated `.mdalign` exports; MZmine writes CSV."""
    head = csv.read_bytes()[:4096]
    return "\t" if head.count(b"\t") > head.count(b",") else ","


def _header_row(csv: Path, sep: str) -> int:
    """MS-DIAL alignment exports prepend ~4 metadata rows (Class, File type,
    Injection order, Batch ID) before the actual column header that starts
    with `Alignment ID`. Scan the first ~10 lines and return the 0-indexed
    row that begins with `Alignment ID` (or 0 if not found — MZmine case)."""
    with csv.open() as f:
        for i in range(20):
            line = f.readline()
            if not line:
                break
            cells = line.rstrip("\n").split(sep)
            if cells and cells[0].strip().lower() in {"alignment id", "id", "row id"}:
                return i
    return 0


def load_features(polarity: str = "merged", kind: str = "area", source: str = "msdial") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (features_meta, abundance_matrix).

    features_meta has one row per feature with id/mz/rt/mobility/ccs/lipid_name.
    abundance_matrix is rows=features × cols=sample_basename, dtype float.
    `kind` is only honored for the legacy MZmine format (`area` | `height`).

    source="metaboscape" reads the cleaned facility table written by
    clean_metaboscape.py (bio samples only); `polarity`/`kind` are ignored.
    """
    if source == "metaboscape":
        if not MS_FEATURES_CLEAN.exists():
            raise FileNotFoundError(
                f"{MS_FEATURES_CLEAN} missing — run clean_metaboscape.py first"
            )
        df = pd.read_csv(MS_FEATURES_CLEAN, index_col="feature_id")
        sample_cols = load_metadata(source="metaboscape")["sample_basename"].tolist()
        sample_cols = [c for c in sample_cols if c in df.columns]
        feat_cols = [c for c in df.columns if c not in sample_cols]
        feats = df[feat_cols].copy()
        abund = df[sample_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        return feats, abund

    # Prefer the annotate_features.py output if present — it has lipid_name
    # filled in via matchms (workaround for MS-DIAL Linux MSP load bug #733).
    candidates = [
        PROCESSED / polarity / f"aligned_features_{polarity}.annotated.csv",
        PROCESSED / polarity / f"aligned_features_{polarity}.csv",
        PROCESSED / f"{polarity}_smoke" / f"aligned_features_{polarity}.annotated.csv",
        PROCESSED / f"{polarity}_smoke" / f"aligned_features_{polarity}.csv",
    ]
    csv = next((p for p in candidates if p.exists()), None)
    if csv is None:
        raise FileNotFoundError(f"no MS-DIAL output found at any of: {candidates}")

    sep = _detect_separator(csv)
    skip = _header_row(csv, sep)
    df = pd.read_csv(csv, sep=sep, header=skip, low_memory=False)

    md = load_metadata()
    sample_cols, rename = _sample_columns(df, kind, md)
    if not sample_cols:
        raise RuntimeError(
            f"no per-sample columns recognized in {csv}; first columns: {df.columns[:25].tolist()}"
        )

    ann_col = _annotation_column(df)
    meta_cols = {
        "id": _first_matching(df, ["Alignment ID", "id", "ID"]),
        "mz": _first_matching(df, ["Average Mz", "Average m/z", "mz", "m/z"]),
        "rt": _first_matching(df, ["Average Rt(min)", "Average Rt", "rt", "Retention time"]),
        "mobility": _first_matching(df, ["Average Mobility"], substrings=["mobility"]),
        "ccs": _first_matching(df, ["Average CCS", "ccs"]),
        "lipid_name": ann_col,
    }
    if meta_cols["id"] is None:
        meta_cols["id"] = df.columns[0]
    keep = [v for v in meta_cols.values() if v]
    feats = df[keep].rename(columns={v: k for k, v in meta_cols.items() if v})

    abund = df[sample_cols].rename(columns=rename).copy()
    abund = abund.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    abund.index = feats["id"].values
    return feats.set_index("id"), abund


def resolve_source(arg: str) -> tuple[str, str, "Path", str]:
    """Map a CLI argument to (source, polarity, out_dir, tag).

    `metaboscape` → the facility table (merged polarity, outputs under
    processed/metaboscape/); `pos`/`neg` → the MS-DIAL path (outputs under
    processed/), tag == polarity.
    """
    if arg == "metaboscape":
        return "metaboscape", "merged", METABOSCAPE_DIR, "metaboscape"
    return "msdial", arg, PROCESSED, arg


def load_bio(source: str = "msdial", polarity: str = "merged") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load features + biological-sample abundance + per-sample metadata.

    Shared by the diff/overview scripts so they treat MS-DIAL and MetaboScape
    sources identically: returns (feats, abund_bio, bio_meta) where abund_bio
    columns and bio_meta index are aligned sample keys (biological samples only).
    """
    feats, abund = load_features(polarity, source=source)
    md = load_metadata(source=source)
    if source != "metaboscape" and "polarity" in md.columns:
        md = md[md.polarity == polarity]
    bio = md[md.sample_type == "sample"].copy()
    bio_cols = [c for c in abund.columns if c in bio.sample_basename.values]
    abund = abund[bio_cols]
    bio = bio.set_index("sample_basename").loc[bio_cols]
    return feats, abund, bio


def median_normalize(abund: pd.DataFrame) -> pd.DataFrame:
    """Divide each sample column by its non-zero median, then re-scale so the
    grand median across all samples stays at the original level."""
    nz = abund.replace(0, np.nan)
    sample_med = nz.median(axis=0)
    grand = sample_med.median()
    return abund.divide(sample_med, axis=1) * grand


# --- OD (biomass) normalization -------------------------------------------------
# Per Andras Szeitz (email 2026-07-08): divide the peak-area counts by the OD600 of
# the individual samples. OD ground-truth (24 culture ODs) is in research/fabfos/lipidomics/od_values.csv,
# transcribed verbatim from SCADC_method_Omics.docx. One OD per *culture*; each culture
# yields both a pellet (P) and supernatant (S) lipidomics fraction, so both fractions of a
# given (culture, treatment, rep) share the culture's OD.
OD_CSV = PROJECT / "research/fabfos/lipidomics/od_values.csv"

# culture (OD table) -> the lipidomics (strain, fraction) pairs it feeds.
CULTURE_TO_STRAINS = {
    "EPI300": [("Epi300", "P"), ("ESi300", "S")],
    "EpCC1":  [("EpCC1", "P"), ("ESCC1", "S")],
    "Clone1": [("Clone1", "P"), ("Clone1", "S")],
    "Clone2": [("Clone2", "P"), ("Clone2", "S")],
}


def load_od() -> pd.DataFrame:
    """The 24 culture OD600 values (culture, treatment, rep, od600)."""
    return pd.read_csv(OD_CSV, comment="#")


def od_map(mode: str = "per_rep") -> pd.Series:
    """Series indexed by sample_basename (`{strain}_{treatment}_{fraction}_{rep}`)
    giving the OD600 to normalize that sample by.

    mode="per_rep"        — the culture's OD for that exact (treatment, rep).
    mode="group_geomean"  — the geometric mean of the culture's 3 reps for that
                            (treatment), applied to every rep. Robust to a possible
                            OD-rep <-> lipidomics-rep index mismatch: it cancels the
                            pairing so the tol/ctrl fold-change correction depends only
                            on the group geomean OD.
    """
    od = load_od()
    out: dict[str, float] = {}
    for culture, group in od.groupby("culture"):
        strains = CULTURE_TO_STRAINS[culture]
        for treatment, g in group.groupby("treatment"):
            geo = float(np.exp(np.log(g["od600"]).mean()))
            for _, r in g.iterrows():
                for strain, fraction in strains:
                    key = f"{strain}_{treatment}_{fraction}_{int(r['rep'])}"
                    out[key] = geo if mode == "group_geomean" else float(r["od600"])
    return pd.Series(out, name="od600")


def od_normalize(abund: pd.DataFrame, mode: str = "per_rep") -> pd.DataFrame:
    """Divide each sample column of `abund` (raw peak areas) by its culture OD600.

    Only columns with a known OD are kept — QC/blanks (no OD) are dropped. Applied to
    RAW areas, NOT on top of median_normalize (median-norm forces equal per-sample
    totals and would erase the very biomass differences OD-normalization exposes).
    """
    od = od_map(mode)
    cols = [c for c in abund.columns if c in od.index]
    return abund[cols].divide(od.loc[cols], axis=1)


def log2(abund: pd.DataFrame, pseudo: float = 1.0) -> pd.DataFrame:
    return np.log2(abund + pseudo)


def contrast(
    feats: pd.DataFrame,
    abund_raw: pd.DataFrame,
    lg: pd.DataFrame,
    idx_a: list[str],
    idx_b: list[str],
    fc_col: str = "log2fc",
) -> pd.DataFrame:
    """One two-group contrast (a vs b) over all features.

    Welch t-test on the log2 matrix `lg`, BH-FDR across the feature set, plus a
    `present_absent` flag (exactly one side has all-zero RAW intensity — a real
    on/off rather than a fold-change). Returns a long-form table carrying the
    feature annotation. `idx_a`/`idx_b` are sample-key column lists.
    """
    from scipy import stats
    from statsmodels.stats.multitest import multipletests

    a, b = lg[idx_a].to_numpy(), lg[idx_b].to_numpy()
    _, pval = stats.ttest_ind(a, b, axis=1, equal_var=False, nan_policy="omit")
    pval = np.asarray(pval, dtype=float)
    fc = np.nanmean(a, axis=1) - np.nanmean(b, axis=1)
    _, qval, _, _ = multipletests(np.nan_to_num(pval, nan=1.0), method="fdr_bh")

    a_off = abund_raw[idx_a].sum(axis=1).to_numpy() == 0
    b_off = abund_raw[idx_b].sum(axis=1).to_numpy() == 0
    present_absent = a_off ^ b_off
    pval = np.where(present_absent, np.nan, pval)
    qval = np.where(present_absent, np.nan, qval)

    def col(name):
        return feats[name].reindex(abund_raw.index).values if name in feats.columns else None

    return pd.DataFrame({
        "feature_id": abund_raw.index,
        "lipid_name": col("lipid_name"),
        "lipid_class": col("lipid_class"),
        "mz": col("mz"),
        "rt": col("rt"),
        "n_a": len(idx_a),
        "n_b": len(idx_b),
        fc_col: fc,
        "pvalue": pval,
        "qvalue": qval,
        "present_absent": present_absent,
    })


def volcano(df: pd.DataFrame, fc_col: str, title: str, path) -> None:
    """Standard volcano: q<0.05 & |log2fc|>1 highlighted; present/absent shown
    as edge marks at the plot margin so on/off features are not lost."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sig = (df.qvalue < 0.05) & (df[fc_col].abs() > 1)
    plt.figure(figsize=(6, 5))
    plt.scatter(df[fc_col], -np.log10(df.pvalue),
                c=np.where(sig, "C3", "lightgray"), s=8, alpha=0.7)
    plt.axhline(-np.log10(0.05), ls="--", lw=0.5, c="k")
    plt.axvline(1, ls="--", lw=0.5, c="k")
    plt.axvline(-1, ls="--", lw=0.5, c="k")
    n_pa = int(df.present_absent.sum()) if "present_absent" in df else 0
    plt.xlabel(f"{fc_col}   (n_sig={int(sig.sum())}, present/absent={n_pa})")
    plt.ylabel("-log10 p")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


# --- LIPID MAPS shorthand parsing -------------------------------------------------
# Handles MZmine and MS-DIAL shorthand: "PE 34:1", "PG 32:0", "TG 52:3",
# "PE(16:0/18:1)", "PC 34:1|aligned" — anything matching CLASS C:DB at start.
SHORTHAND_RE = re.compile(
    r"^(?P<cls>[A-Za-z][A-Za-z0-9-]+?)\s*[\(\s](?P<carbon>\d+):(?P<db>\d+)"
)


def parse_shorthand(name: str | float) -> dict:
    if not isinstance(name, str):
        return {"lipid_class": None, "total_carbon": None, "total_db": None}
    s = name.strip().split("|")[0].strip()
    m = SHORTHAND_RE.match(s)
    if not m:
        return {"lipid_class": None, "total_carbon": None, "total_db": None}
    return {
        "lipid_class": m["cls"],
        "total_carbon": int(m["carbon"]),
        "total_db": int(m["db"]),
    }

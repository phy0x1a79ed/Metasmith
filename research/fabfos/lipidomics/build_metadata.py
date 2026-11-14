"""Parse Bruker .d filenames in data/fabfos/runs/scadc_lipidomics/msms/{POS,NEG}/ into metadata.csv.

Schema:
  filename, polarity, sample_type, strain, treatment, fraction, replicate, plate_pos, run_id

sample_type ∈ {sample, blank, qc}
strain      ∈ {Epi300, EpCC1, ESi300, ESCC1, Clone1, Clone2}  (NaN for blank/qc)
treatment   ∈ {ctrl, tol}                                      (NaN for blank/qc; blanks get blank_group)
fraction    ∈ {P, S}                                           (P=pellet, S=supernatant; "SN" → S)
replicate   ∈ {1, 2, 3}                                        (NaN for blank/qc; blanks get rep from blank index)

Run from the project root:  mamba run -n lipidomics python research/fabfos/lipidomics/build_metadata.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
import pandas as pd

DATA_ROOT = Path("data/fabfos/runs/scadc_lipidomics/msms")
OUT = Path("research/fabfos/lipidomics/metadata.csv")

STRAINS = ("Epi300", "EpCC1", "ESi300", "ESCC1", "Clone1", "Clone2")

# Biological sample:  {Strain}_(Tol_)?(P|S)_{rep}_{plate-pos}_1_{run}.d
SAMPLE_RE = re.compile(
    rf"^(?P<strain>{'|'.join(STRAINS)})_(?P<tol>Tol_)?(?P<fraction>[PS])_(?P<rep>[123])_"
    rf"(?P<plate>P\d+-[A-Z]-\d+)_1_(?P<run>\d+)\.d$"
)

# Blank:  Blank {n} (P|Tol)?_{plate-pos}_1_{run}.d
BLANK_RE = re.compile(
    r"^Blank (?P<idx>\d+)(?: (?P<tag>P|Tol))?_(?P<plate>P\d+-[A-Z]-\d+)_1_(?P<run>\d+)\.d$"
)

# QC:  "QC {n} {SN|P}_..." or "QC{n} {SN|P}_..."  (one outlier: "QC1 P")
QC_RE = re.compile(
    r"^QC\s?(?P<idx>\d+)\s(?P<tag>SN|P)_(?P<plate>P\d+-[A-Z]-\d+)_1_(?P<run>\d+)\.d$"
)


def parse_one(name: str, polarity: str) -> dict | None:
    if m := SAMPLE_RE.match(name):
        return dict(
            filename=name,
            polarity=polarity,
            sample_type="sample",
            strain=m["strain"],
            treatment="tol" if m["tol"] else "ctrl",
            fraction=m["fraction"],
            replicate=int(m["rep"]),
            plate_pos=m["plate"],
            run_id=int(m["run"]),
        )
    if m := BLANK_RE.match(name):
        # "Blank N P"   → pellet-queue blank (no Tol, fraction P)
        # "Blank N Tol" → supernatant-Tol-queue blank (fraction S)
        # "Blank N"     → supernatant non-Tol blank (fraction S)
        tag = m["tag"]
        if tag == "P":
            frac, treat = "P", "ctrl"
        elif tag == "Tol":
            frac, treat = "S", "tol"
        else:
            frac, treat = "S", "ctrl"
        return dict(
            filename=name,
            polarity=polarity,
            sample_type="blank",
            strain=None,
            treatment=treat,
            fraction=frac,
            replicate=int(m["idx"]),
            plate_pos=m["plate"],
            run_id=int(m["run"]),
        )
    if m := QC_RE.match(name):
        # "QC N SN" = pooled supernatant; "QC N P" = pooled pellet
        frac = "S" if m["tag"] == "SN" else "P"
        return dict(
            filename=name,
            polarity=polarity,
            sample_type="qc",
            strain=None,
            treatment=None,
            fraction=frac,
            replicate=int(m["idx"]),
            plate_pos=m["plate"],
            run_id=int(m["run"]),
        )
    return None


def main() -> int:
    rows: list[dict] = []
    unparsed: list[tuple[str, str]] = []
    for pol_dir, pol in (("POS", "pos"), ("NEG", "neg")):
        d = DATA_ROOT / pol_dir
        if not d.is_dir():
            print(f"!! missing {d}", file=sys.stderr)
            return 1
        for p in sorted(d.iterdir()):
            if not p.name.endswith(".d"):
                continue
            row = parse_one(p.name, pol)
            if row is None:
                unparsed.append((pol, p.name))
            else:
                rows.append(row)

    if unparsed:
        print(f"!! {len(unparsed)} unparsed filenames:", file=sys.stderr)
        for pol, n in unparsed:
            print(f"   [{pol}] {n}", file=sys.stderr)
        return 1

    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    # Sanity: per-polarity totals and group structure
    print(f"wrote {OUT} ({len(df)} rows)")
    print("\n== per polarity ==")
    print(df.groupby(["polarity", "sample_type"]).size().unstack(fill_value=0))
    print("\n== bio sample cells (pos polarity) ==")
    bio = df[(df.polarity == "pos") & (df.sample_type == "sample")]
    print(
        bio.groupby(["strain", "treatment", "fraction"]).size().unstack(fill_value=0)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

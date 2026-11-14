"""T3 -- read the acyl chains straight off the negative-mode MS/MS.

In negative mode a glycerophospholipid gives up its fatty acids as carboxylate
anions, and those anions are diagnostic: they say which chains the lipid carries
without needing any library to hold the intact species. That matters here
precisely because the libraries do NOT hold these species -- LIPID MAPS returns
nothing for HBMP, a class the facility identified in this very dataset.

This is what discriminates among the isomers sitting under an L3 call. A mass
search says "some C40H71O10P exists"; the acyl fragments say "and it carries a
16:0 and an 18:1".

It is evidence, not a level promotion. The grading rule is left alone and these
chains are reported alongside it, because a carboxylate anion identifies a chain,
not the molecule that shed it, and co-isolated precursors can donate fragments
they were never part of.

One ambiguity is called out rather than resolved: a monounsaturated odd chain and
a cyclopropane-containing saturated chain of the same carbon number are the same
formula and the same mass. In E. coli, 17:0-cyclo and 19:0-cyclo are abundant
real lipids, so a "17:1" here is at least as likely to be 17:0-cyclo.

Run:  mamba run -n p312 python -m identify.fa_fragments     (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

MASS_C, MASS_H, MASS_O = 12.0, 1.007825032, 15.994914620
PROTON = 1.007276467

TOL_DA = 0.012
MIN_REL_INTENSITY = 5.0     # % of base peak
CARBONS = range(10, 27)
DOUBLE_BONDS = range(0, 7)
# Chains where "n:1" and "n:0-cyclopropane" are indistinguishable by mass, and
# the cyclopropane form is a genuine E. coli membrane lipid.
CYCLO_AMBIGUOUS = {15, 17, 19, 21}


def fa_anion_mass(carbons: int, db: int) -> float:
    """[FA-H]- for CnH(2n-2d)O2."""
    neutral = carbons * MASS_C + (2 * carbons - 2 * db) * MASS_H + 2 * MASS_O
    return neutral - PROTON


def table() -> list[tuple[str, float, int, int]]:
    out = []
    for c in CARBONS:
        for d in DOUBLE_BONDS:
            if d > (c - 2) // 2:
                continue
            out.append((f"{c}:{d}", fa_anion_mass(c, d), c, d))
    return out


def annotate(peaks: list[list[float]]) -> list[dict]:
    """Fatty-acyl anions present in one consensus spectrum."""
    fa = table()
    found = {}
    for mz, inten in peaks:
        if inten < MIN_REL_INTENSITY:
            continue
        for name, ref, c, d in fa:
            if abs(mz - ref) <= TOL_DA:
                prev = found.get(name)
                if prev is None or inten > prev["intensity"]:
                    found[name] = {
                        "chain": name,
                        "mz_observed": round(mz, 4),
                        "mz_reference": round(ref, 4),
                        "ppm": round((mz - ref) / ref * 1e6, 1),
                        "intensity": inten,
                        "cyclo_ambiguous": bool(d == 1 and c in CYCLO_AMBIGUOUS),
                    }
    return sorted(found.values(), key=lambda r: -r["intensity"])


def run() -> pd.DataFrame:
    manifest = pd.read_csv(common.IDENT_DIR / "hit_manifest.csv").set_index("feature_id")
    spectra = json.loads((common.SPECTRA_DIR / "consensus_ms2.json").read_text())

    rows = []
    for fid, spec in sorted(spectra.items()):
        f = manifest.loc[fid]
        if f.polarity != "neg":
            continue   # carboxylate anions are a negative-mode readout only
        for hit in annotate(spec["peaks"]):
            rows.append({
                "feature_id": fid, "mz": f.mz, "rt": f.rt, "adduct": f.adduct,
                "n_scans": spec["n_scans"], **hit,
                "note": ("mass-identical to "
                         f"{hit['chain'].split(':')[0]}:0-cyclopropane"
                         if hit["cyclo_ambiguous"] else ""),
            })

    out = pd.DataFrame(rows)
    common.PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(common.PUBLISH_DIR / "clone_response_acyl_fragments.csv", index=False)
    out.to_csv(common.IDENT_DIR / "acyl_fragments.csv", index=False)

    neg = [f for f in spectra if manifest.loc[f].polarity == "neg"]
    print("Acyl-chain fragments from negative-mode MS/MS")
    print(f"  negative-mode spectra    {len(neg)}")
    print(f"  with >=1 acyl fragment   {out.feature_id.nunique() if len(out) else 0}")
    print(f"  fragment rows            {len(out)}")
    for fid in neg:
        sub = out[out.feature_id == fid] if len(out) else out
        chains = ", ".join(
            f"{r.chain}{'*' if r.cyclo_ambiguous else ''}" for _, r in sub.iterrows()
        ) or "-"
        mark = "  <- control" if fid in common.CONTROL_FEATURES else ""
        print(f"    {fid}  {chains}{mark}")
    print("\n  * mass-identical to the cyclopropane-containing saturated chain,")
    print("    which E. coli genuinely makes -- not resolvable by mass alone.")
    return out


if __name__ == "__main__":
    run()

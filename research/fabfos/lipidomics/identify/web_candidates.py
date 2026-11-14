"""T2 -- named lipid candidates from LIPID MAPS and RefMet, keyed by formula.

For each hit feature: take the facility formula if there is one, otherwise
enumerate plausible formulas from the neutral mass, then ask LIPID MAPS whether
any compound with that formula exists. A formula that returns records is
supported by a curated structure database; one that returns nothing was a
mass coincidence. That existence test, not the mass ranking, is what makes this
stage discriminating.

LMSD returns every acyl-chain isomer of a species separately, so records are
collapsed to the species level (`abbrev`) and the isomer count is kept as
evidence of how ambiguous the call is.

Run:  mamba run -n p312 python -m identify.web_candidates    (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common, formula as formula_mod, webapi  # noqa: E402

PPM_TOL = 5.0
MAX_FORMULAS_QUERIED = 20
MAX_FORMULA_ONLY = 5   # unsupported formulas reported per feature


def _formulas_for(row: pd.Series) -> list[tuple[str, float | None, str]]:
    """(formula, ppm_error, provenance) candidates for one feature.

    A facility-supplied formula carries no mass error of its own -- None, not
    zero. Reporting 0.000 ppm there would claim a perfect mass match that was
    never measured; the real error against that composition is computed
    per-candidate below, from the database's own exact mass.
    """
    if isinstance(row.formula, str) and row.formula.strip():
        return [(row.formula.strip(), None, "facility")]
    gen = formula_mod.generate(float(row.neutral_mass), PPM_TOL, MAX_FORMULAS_QUERIED)
    return [(str(f), round(f.ppm_error, 3), "generated") for f in gen]


def _ppm_for(neutral_mass: float, record_mass: object, fallback: float | None) -> float | None:
    """Mass error against the candidate's own exact mass, when the record has one."""
    try:
        ref = float(record_mass)
    except (TypeError, ValueError):
        return fallback
    if ref <= 0:
        return fallback
    return round(common.ppm(neutral_mass, ref), 3)


def _collapse(records: list[dict]) -> dict[str, dict]:
    """LMSD rows -> one entry per lipid species, carrying the isomer count."""
    by_species: dict[str, dict] = {}
    counts: dict[str, int] = defaultdict(int)
    for r in records:
        key = (r.get("abbrev") or r.get("name") or r.get("lm_id") or "").strip()
        if not key:
            continue
        counts[key] += 1
        by_species.setdefault(key, r)
    for key, r in by_species.items():
        r["_isomers"] = counts[key]
    return by_species


def run() -> pd.DataFrame:
    common.ensure_dirs()
    manifest = pd.read_csv(common.IDENT_DIR / "hit_manifest.csv")
    rows, summary = [], []
    unsupported_emitted: dict[str, list[str]] = defaultdict(list)

    for _, f in manifest.iterrows():
        cands = _formulas_for(f)
        n_lm = n_rm = 0
        supported = []
        for fml, ppm_err, prov in cands:
            lm = webapi.lipidmaps_formula(fml)
            rm = webapi.refmet_formula(fml)
            if not lm and not rm:
                # No curated compound carries this formula. The formula itself is
                # still evidence -- it is what separates "we know the composition"
                # from "we only know the mass" -- so it is emitted as its own
                # candidate and graded down accordingly, rather than dropped.
                if len(unsupported_emitted[f.feature_id]) < MAX_FORMULA_ONLY:
                    unsupported_emitted[f.feature_id].append(fml)
                    rows.append(
                        common.candidate_row(
                            f.feature_id, "formula_enumeration",
                            candidate_name=fml,
                            formula=fml,
                            ppm_error=ppm_err,
                            notes=f"formula {prov}; no LIPID MAPS or RefMet compound has it",
                        )
                    )
                continue
            supported.append(fml)

            for species, rec in _collapse(lm).items():
                n_lm += 1
                rows.append(
                    common.candidate_row(
                        f.feature_id, "lipidmaps_formula",
                        candidate_name=species,
                        formula=fml,
                        lipid_class=rec.get("main_class"),
                        super_class=rec.get("core"),
                        main_class=rec.get("main_class"),
                        sub_class=rec.get("sub_class"),
                        exactmass=rec.get("exactmass"),
                        ppm_error=_ppm_for(float(f.neutral_mass),
                                           rec.get("exactmass"), ppm_err),
                        external_ids=";".join(
                            f"{t}:{rec[k]}" for k, t in (
                                ("lm_id", "LM"), ("hmdb_id", "HMDB"),
                                ("kegg_id", "KEGG"), ("chebi_id", "ChEBI"),
                                ("pubchem_cid", "PubChem"),
                            ) if rec.get(k)
                        ),
                        notes=f"formula {prov}; {rec['_isomers']} LMSD isomer(s)",
                    )
                )

            for rec in rm:
                name = (rec.get("refmet_name") or rec.get("name") or "").strip()
                if not name:
                    continue
                n_rm += 1
                rows.append(
                    common.candidate_row(
                        f.feature_id, "refmet_formula",
                        candidate_name=name,
                        formula=fml,
                        lipid_class=rec.get("sub_class"),
                        super_class=rec.get("super_class"),
                        main_class=rec.get("main_class"),
                        sub_class=rec.get("sub_class"),
                        exactmass=rec.get("exactmass"),
                        ppm_error=_ppm_for(float(f.neutral_mass),
                                           rec.get("exactmass"), ppm_err),
                        external_ids=";".join(
                            f"{t}:{rec[k]}" for k, t in (
                                ("refmet_id", "RefMet"), ("pubchem_cid", "PubChem"),
                                ("inchi_key", "InChIKey"),
                            ) if rec.get(k)
                        ),
                        notes=f"formula {prov}",
                    )
                )

        summary.append(
            {
                "feature_id": f.feature_id,
                "formulas_tried": len(cands),
                "formulas_supported": len(supported),
                "supported": ";".join(supported),
                "lipidmaps_species": n_lm,
                "refmet_entries": n_rm,
                "is_control": f.is_control,
            }
        )
        print(
            f"  {f.feature_id}  {len(cands):2d} formulas -> "
            f"{len(supported):2d} supported, {n_lm:3d} LM species, {n_rm:3d} RefMet"
            + ("   <- control" if f.is_control else "")
        )

    out = pd.DataFrame(rows, columns=common.CANDIDATE_COLS)
    out.to_csv(common.IDENT_DIR / "candidates_web_formula.csv", index=False)
    summ = pd.DataFrame(summary)
    summ.to_csv(common.IDENT_DIR / "formula_support_summary.csv", index=False)

    print("\nLIPID MAPS + RefMet formula lookup")
    print(f"  features with >=1 supported formula  "
          f"{(summ.formulas_supported > 0).sum()}/{len(summ)}")
    print(f"  candidate rows written               {len(out)}")
    print(f"  cache                                {webapi.cache_stats()}")
    return out


if __name__ == "__main__":
    run()

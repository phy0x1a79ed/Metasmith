"""Find which universe reactions make carved E4 models stoichiometrically inconsistent.

    model_balance.py <rung> <own_universe.xml.gz> <other_universe.xml.gz> <models_dir> <out.jsonl>

<rung> is a label (B or U); <own_universe> is the universe that rung carved from and <other_universe> the
other one. For every model in <models_dir> it runs MEMOTE 0.17's stoichiometric-consistency check as
built, then after each of these interventions:

  drop_exclusive   drop the reactions only the rung's own universe holds
  drop_changed     drop the shared reactions whose stoichiometry differs between the universes
  patch_changed    give those shared reactions the other universe's stoichiometry
  drop_h_only      drop the reactions whose only element imbalance is hydrogen, by the own universe's formulas
  patch_and_drop   patch_changed and drop_exclusive together

Each result is True when the model passes. Run inside the MEMOTE 0.17 image, with universe_balance.py on
PYTHONPATH. Reaction ids are matched without their R_ prefix, because cobra strips it on load.
"""
import json
import sys
from pathlib import Path

import cobra
from memote.support import consistency as con

from universe_balance import classify, load


def bare(i):
    return i.removeprefix("R_")


def stoich_of(rxn):
    return {m.id.removeprefix("M_"): c for m, c in rxn.metabolites.items()}


def consistent(model):
    return bool(con.check_stoichiometric_consistency(model))


def patched(model, patches, drop):
    m = model.copy()
    m.solver = "glpk"
    m.remove_reactions([r for r in m.reactions if r.id in drop], remove_orphans=True)
    for rid, st in patches.items():
        if rid in m.reactions:
            r = m.reactions.get_by_id(rid)
            r.subtract_metabolites(r.metabolites)
            r.add_metabolites({(m.metabolites.get_by_id(k) if k in m.metabolites else cobra.Metabolite(k)): v for k, v in st.items()})
    return m


def main(rung, own_path, other_path, models_dir, out):
    own, other = load(own_path), load(other_path)
    own_ids = {bare(r.id): r for r in own.reactions}
    other_ids = {bare(r.id): r for r in other.reactions}
    shared = set(own_ids) & set(other_ids)
    exclusive = set(own_ids) - shared
    changed = {i for i in shared if stoich_of(own_ids[i]) != stoich_of(other_ids[i])}
    patch = {i: stoich_of(other_ids[i]) for i in changed}
    h_only = {i for i, r in own_ids.items() if classify(r)[0] == "H_only"}
    print(f"{rung}: exclusive {len(exclusive)}, changed {len(changed)}, h_only {len(h_only)}", flush=True)
    with open(out, "w") as fh:
        for path in sorted(Path(models_dir).glob("*.xml")):
            model = cobra.io.read_sbml_model(str(path))
            model.solver = "glpk"
            ids = {r.id for r in model.reactions}
            rec = {"rung": rung, "model": path.stem, "reactions": len(ids), "reaction_ids": sorted(ids),
                   "exclusive_held": sorted(ids & exclusive), "changed_held": sorted(ids & changed),
                   "h_only_held": sorted(ids & h_only), "consistent": consistent(model)}
            rec["drop_exclusive"] = consistent(patched(model, {}, exclusive))
            rec["drop_changed"] = consistent(patched(model, {}, changed))
            rec["patch_changed"] = consistent(patched(model, patch, set()))
            rec["drop_h_only"] = consistent(patched(model, {}, h_only))
            rec["patch_and_drop"] = consistent(patched(model, patch, exclusive))
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            print(path.name, {k: rec[k] for k in ("consistent", "drop_exclusive", "drop_changed", "patch_changed", "drop_h_only", "patch_and_drop")}, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

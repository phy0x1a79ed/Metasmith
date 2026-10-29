"""Count stoichiometric inconsistency, mass imbalance and charge imbalance in two CarveMe universes.

    universe_balance.py <universe_122.xml.gz> <universe_166.xml.gz> <out_dir>

Reads species formulas and charges from the SBML notes (the only place 1.2.2's universe keeps them) and
builds a cobra model per universe, then applies MEMOTE 0.17's own checks to it. Run it inside the MEMOTE
0.17 image. Every count is made over the whole universe, over the reactions both universes hold, and
over the reactions only one of them holds. Writes reactions.tsv (one row per reaction id) and
summary.json.
"""
import csv
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

import cobra
import libsbml
from memote.support import consistency as con
from memote.support import consistency_helpers as ch

NOTE = re.compile(r"^(FORMULA|CHARGE):\s*(\S+)\s*$")


def load(path):
    doc = libsbml.readSBMLFromString(gzip.open(path, "rt").read())
    sm = doc.getModel()
    model = cobra.Model(sm.getId())
    for i in range(sm.getNumSpecies()):
        s = sm.getSpecies(i)
        meta = cobra.Metabolite(s.getId(), compartment=s.getCompartment())
        for line in (s.getNotesString() or "").splitlines():
            m = NOTE.match(re.sub(r"</?p>", "", line.strip()))
            if m and m.group(1) == "FORMULA" and m.group(2) not in ("None", "nan", ""):
                meta.formula = m.group(2)
            elif m and m.group(1) == "CHARGE":
                try:
                    c = float(m.group(2))
                    if c == int(c):
                        meta.charge = int(c)
                except ValueError:
                    pass
        model.add_metabolites([meta])
    for i in range(sm.getNumReactions()):
        r = sm.getReaction(i)
        rxn = cobra.Reaction(r.getId())
        rxn.lower_bound, rxn.upper_bound = (-1000.0 if r.getReversible() else 0.0), 1000.0
        model.add_reactions([rxn])
        stoich = {}
        for j in range(r.getNumReactants()):
            ref = r.getReactant(j)
            stoich[ref.getSpecies()] = stoich.get(ref.getSpecies(), 0) - ref.getStoichiometry()
        for j in range(r.getNumProducts()):
            ref = r.getProduct(j)
            stoich[ref.getSpecies()] = stoich.get(ref.getSpecies(), 0) + ref.getStoichiometry()
        rxn.add_metabolites({model.metabolites.get_by_id(k): v for k, v in stoich.items()})
    return model


def subset(model, ids):
    sub = cobra.Model(model.id)
    sub.add_metabolites([m.copy() for m in model.metabolites])
    for rid in ids:
        r = model.reactions.get_by_id(rid)
        n = cobra.Reaction(rid)
        n.lower_bound, n.upper_bound = r.lower_bound, r.upper_bound
        sub.add_reactions([n])
        n.add_metabolites({sub.metabolites.get_by_id(m.id): c for m, c in r.metabolites.items()})
    return sub


def internal(model):
    return [r for r in model.reactions if not r.boundary and "biomass" not in r.id.lower() and r.id not in ("Growth", "R_Growth")]


def element_residual(rxn):
    """Net element counts of a reaction, or None when a participant has no formula."""
    if any(not m.elements for m in rxn.metabolites):
        return None
    net = Counter()
    for m, c in rxn.metabolites.items():
        for e, n in m.elements.items():
            net[e] += c * n
    return {e: v for e, v in net.items() if abs(v) > 1e-9}


def charge_residual(rxn):
    if any(m.charge is None for m in rxn.metabolites):
        return None
    return sum(c * m.charge for m, c in rxn.metabolites.items())


def classify(rxn):
    el, ch_ = element_residual(rxn), charge_residual(rxn)
    mass = "no_formula" if el is None else "balanced" if not el else "H_only" if set(el) == {"H"} else "other"
    charge = "no_charge" if ch_ is None else "balanced" if abs(ch_) < 1e-9 else "unbalanced"
    return mass, charge, el, ch_


def unconserved_lp(sub):
    """Unconserved metabolites by the exact LP behind MEMOTE's MILP.

    The cone of non-negative mass vectors m with N^T m = 0 is closed under addition and scaling, so one
    vector supports every metabolite any vector supports. Maximising sum(k) with 0 <= k_i <= min(m_i, 1)
    therefore gives k_i = 1 exactly on that support, and no binary variable is needed. MEMOTE's MILP on a
    5,000-reaction universe returns a feasible point, not necessarily the optimum.
    """
    problem = sub.problem
    lp = problem.Model()
    rxns = [r for r in sub.reactions if not r.boundary and "biomass" not in r.id.lower() and r.id not in ("Growth", "R_Growth")]
    mets = sorted({m for r in rxns for m in r.metabolites}, key=lambda m: m.id)
    m_var = {m.id: problem.Variable(f"m_{m.id}", lb=0) for m in mets}
    k_var = {m.id: problem.Variable(f"k_{m.id}", lb=0, ub=1) for m in mets}
    lp.add(list(m_var.values()) + list(k_var.values()))
    lp.update()
    lp.add([problem.Constraint(k_var[i] - m_var[i], ub=0) for i in m_var])
    lp.add([problem.Constraint(sum(c * m_var[m.id] for m, c in r.metabolites.items()), lb=0, ub=0) for r in rxns])
    lp.objective = problem.Objective(sum(k_var.values()), direction="max")
    lp.optimize()
    return sorted(i for i, v in k_var.items() if v.primal < 0.5)


def stoich_check(model, ids, find_mets=True, exact=False):
    sub = subset(model, ids)
    sub.solver = "glpk"
    sub.solver.configuration.timeout = 1800
    ok = bool(con.check_stoichiometric_consistency(sub))
    if ok or not find_mets:
        return ok, []
    if exact:
        return ok, unconserved_lp(sub)
    return ok, sorted(m.id for m in con.find_unconserved_metabolites(sub))


def summarise(name, model, ids, classes):
    internals = [r for r in internal(model) if r.id in ids]
    c = Counter(classes[r.id][0] for r in internals)
    q = Counter(classes[r.id][1] for r in internals)
    used = {m for r in internals for m in r.metabolites}
    out = {
        "reactions": len(ids), "internal": len(internals), "boundary_or_biomass": len(ids) - len(internals),
        "metabolites_used": len(used),
        "metabolites_used_without_formula": sum(not m.formula for m in used),
        "metabolites_used_without_charge": sum(m.charge is None for m in used),
        "mass": dict(c), "charge": dict(q),
        "mass_unbalanced_or_unknown": len(internals) - c["balanced"],
        "mass_unbalanced_determinable": c["H_only"] + c["other"],
        "charge_unbalanced_determinable": q["unbalanced"],
    }
    print(name, json.dumps(out), flush=True)
    return out


def main(p122, p166, out_dir):
    out_dir = Path(out_dir)
    models = {"122": load(p122), "166": load(p166)}
    ids = {k: {r.id for r in m.reactions} for k, m in models.items()}
    shared = ids["122"] & ids["166"]
    classes = {k: {r.id: classify(r) for r in m.reactions} for k, m in models.items()}
    summary = {"n_reactions": {k: len(v) for k, v in ids.items()}, "shared": len(shared),
               "only_122": len(ids["122"] - shared), "only_166": len(ids["166"] - shared)}

    for k, m in models.items():
        for label, sel in (("all", ids[k]), ("shared", shared), ("only", ids[k] - shared)):
            summary[f"{k}:{label}"] = summarise(f"{k}:{label}", m, sel, classes[k])

    for k, m in models.items():
        keep = [r.id for r in internal(m)]
        ok, mets = stoich_check(m, keep, exact=True)
        summary[f"{k}:stoich_all"] = {"consistent": ok, "unconserved": mets}
        print(k, "stoich all internal", ok, len(mets), mets[:20], flush=True)
        shared_keep = [r for r in keep if r in shared]
        ok, mets = stoich_check(m, shared_keep, exact=True)
        summary[f"{k}:stoich_shared"] = {"consistent": ok, "unconserved": mets}
        print(k, "stoich shared", ok, len(mets), mets[:20], flush=True)
        # Drop every reaction whose only element imbalance is hydrogen and ask whether the rest is consistent.
        no_h = [r for r in keep if classes[k][r][0] != "H_only"]
        ok, mets = stoich_check(m, no_h, exact=True)
        summary[f"{k}:stoich_without_H_only"] = {"consistent": ok, "unconserved": mets, "removed": len(keep) - len(no_h)}
        print(k, "stoich without H-only imbalanced", ok, len(mets), mets[:20], flush=True)
        # Control: with every formula-unbalanced reaction gone, only reactions that conserve mass by formula
        # remain, and an exact check must find no unconserved metabolite.
        balanced = [r for r in keep if classes[k][r][0] in ("balanced", "no_formula")]
        ok, mets = stoich_check(m, balanced, exact=True)
        summary[f"{k}:stoich_formula_balanced_only"] = {"consistent": ok, "unconserved": mets, "removed": len(keep) - len(balanced)}
        print(k, "stoich formula-balanced only", ok, len(mets), mets[:20], flush=True)

    rows = []
    for rid in sorted(ids["122"] | ids["166"]):
        row = {"reaction": rid, "in_122": rid in ids["122"], "in_166": rid in ids["166"]}
        for k in ("122", "166"):
            if rid in ids[k]:
                r = models[k].reactions.get_by_id(rid)
                mass, charge, el, ch_ = classes[k][rid]
                row[f"stoich_{k}"] = json.dumps(sorted((m.id, c) for m, c in r.metabolites.items()))
                row[f"mass_{k}"], row[f"charge_{k}"] = mass, charge
                row[f"resid_{k}"] = json.dumps(el, sort_keys=True) if el is not None else ""
                row[f"boundary_{k}"] = r.boundary
        rows.append(row)
    both = [r for r in rows if r["in_122"] and r["in_166"]]
    summary["shared_same_stoichiometry"] = sum(r["stoich_122"] == r["stoich_166"] for r in both)
    summary["shared_changed_stoichiometry"] = sum(r["stoich_122"] != r["stoich_166"] for r in both)
    summary["shared_mass_status_changed"] = Counter(f'{r["mass_122"]}->{r["mass_166"]}' for r in both if r["mass_122"] != r["mass_166"])
    summary["shared_charge_status_changed"] = Counter(f'{r["charge_122"]}->{r["charge_166"]}' for r in both if r["charge_122"] != r["charge_166"])
    cols = ["reaction", "in_122", "in_166"] + [f"{p}_{k}" for k in ("122", "166") for p in ("stoich", "mass", "charge", "resid", "boundary")]
    with open(out_dir / "reactions.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=dict))
    print("done", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

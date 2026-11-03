# Why CarveMe 1.6.6's universe doubles MEMOTE consistency

## Purpose & Contents

This file explains the rise in MEMOTE 0.17 consistency between E4 ablation rungs B and U, from a median of 0.391 to 0.803, over 1,408 paired bins. Only the BiGG universe changes between B and U. It holds findings only. The scripts and tables in this directory are the source.

## One test carries the jump

MEMOTE's consistency section has five tests, with weights 3, 1, 1, 1 and 1. `per_test.py` reads E4's archived per-test JSON; no rescoring was done. Output: `consistency_by_test.tsv`.

| Test | B median | U median | Change × weight / 7 |
|---|---|---|---|
| Stoichiometric consistency (weight 3) | 0 | 1 | +0.308 |
| Mass balance | 0 | 0 | 0 |
| Charge balance | 1 | 1 | 0 |
| Disconnected metabolites | 1 | 1 | 0 |
| Unbounded flux | 0.735 | 0.665 | −0.010 |

- **Pass rates:** 4.3% of B models pass stoichiometric consistency, against 76.2% of U models.
- **U's low mode:** all 335 U bins below 0.7 fail this test, and none of the other 1,073 do. This is E4's bimodal consistency.
- **Unconserved metabolites:** every failing model reports only H+ and H2, in c, p and e.

## Mass and charge balance do not contribute

`universe_balance.py` checks the universes themselves, using the formulas and charges in the SBML notes and MEMOTE's own check functions. Output: `reactions.tsv`, `summary.json`.

- **Mass balance:**
  - By formula, 33.3% of 1.2.2's internal reactions are unbalanced, against 0.18% of 1.6.6's.
  - Of the 991 shared reactions that were unbalanced in 1.2.2, 989 are balanced in 1.6.6. This is a species-formula cleanup.
  - The cleanup is invisible as scored: framed 0.5.1 writes no formula attribute at either rung, so mass balance scores 0 at both.
- **Charge balance:** 1.6.6 is not better. It has 131 charge-unbalanced reactions against 35, and 781 metabolites with no charge against 307.
- **Writer and flavor are ruled out:**
  - B and U both carry zero `fbc:chemicalFormula` and `fbc:charge` attributes in all 1,408 models.
  - The `default_flavor = fbc2` setting only changes how the universe is read.
  - Through CarveMe 1.6.6's writer (E4's rewrite lane), consistency still goes from 0.471 to 0.945. Mass balance then adds +0.062.

## The cause is a proton coefficient

`model_balance.py` drops reactions from archived models to find which ones repair stoichiometric consistency. It uses a random 226 B and 201 U models, not paired by bin. Output: `model_interventions.tsv`, `intervention_summary.tsv`.

- **Both universes fail as whole sets,** through the same six H and H2 pseudo-metabolites. What differs is which reactions are carved into each model.
- **57 shared reactions differ in stoichiometry** between the universes, 54 of them only in an H+ coefficient.
- **Dropping those 57 reactions repairs most failures:** 83% of failing B models and 100% of failing U models.
- **Formulas cannot find B's culprits:** dropping the 63 formula-detected H-only reactions repairs 0% of failing B models.
- **U's remaining failures** all hold the siderophore pair `CMCBTFL` and `CMCBTFU`. Of the 51 sampled models that hold the pair, 46 fail; none of the 150 without it fail.
- **Open:** 17% of failing B models still fail after the drop, and the cause was not identified.

## Caveats

- Dropping a reaction shows that the drop is sufficient for those models, not that the reaction is the only cause.
- The charge-unbalanced counts cover only reactions whose metabolites all have a charge.
- A reaction that BiGG renamed between the universes counts as absent from each.

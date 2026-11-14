# results/feature-set

## Purpose & Contents

The result of the feature-set topic: whether the lipidomics data resolve into compound-level units without identification, and by which route.

## Question

> ok, are we able to resolve a set of features that correspond to metabolites, even if we cant identify each feature? Can we resolve  a feature set in an unsupervised way? Like ORF prediction, can we first get a minimally transposed version of the raw data, if you kow what I mean?

## Survey

- The 2180 MetaboScape rows already carry partial componentization: isotopes, adducts and the pos/neg pairing. The facility ran it. Its grouping cannot be audited.
- 167 of 2180 rows carry a library or target-list annotation source. 2013 carry none.
- Retention time spans 0.54–6.3 min, a short gradient.
- Raw mzML exists for both polarities under `processed/{pos,neg}/mzml`. The June MS-DIAL 5 run on it returned 106 pos and 37 neg features because its thresholds were mis-scaled. Nobody tuned it further.
- First redundancy pass groups rows by co-elution plus cross-sample correlation (connected components):

| RT window | r threshold | components | singletons | largest |
|---|---|---|---|---|
| 0.02 min | 0.9 | 1500 | 1349 | 139 |
| 0.02 min | 0.8 | 1163 | 1000 | 180 |
| 0.05 min | 0.9 | 1350 | 1222 | 148 |
| 0.05 min | 0.8 | 974 | 875 | 226 |

- **CAUTION:** the large components are chaining artefacts. Connected components link A–B–C without A–C. The correlation also counts shared zeros as agreement. The count range of roughly 1000–1500 compounds is an upper-bound sketch, not a result. A proper pass needs mass-difference rules and peak-shape correlation.

## Routes

1. Componentize the MetaboScape table: co-elution, cross-sample correlation and mass-difference rules. Cheap. Inherits MetaboScape's peak picking.
2. Re-derive features from raw mzML with an open feature finder, then componentize. Auditable. Days of calibration.

## Data shape (settled with the user)

- Levels: raw frames, then ions (isotope envelope folded), then the feature table of ions aligned across samples.
- Each sample is a vector over ions. The only per-sample number is intensity.
- Rows are ions, not metabolites. 88% of xlsx rows hold one ion form. Only 55 of 3095 pair pos and neg.
- Candidate-free ion identity: m/z, charge, RT apex, peak shape, mobility, mobilogram, isotope pattern, MS2 spectrum. Every column that compares the ion to a candidate is dropped.
- The journal post of 2026-11-13 holds the full layout.

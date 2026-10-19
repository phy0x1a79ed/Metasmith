# Lipidomics results: where they were reported, and what they say

Research only. Nothing was edited, committed or published.

## 1. Where the results were reported

**No claude.ai artifact you can open today reports the LC-MS/MS results.**

- The lipidomics report was an HTML artifact: **https://claude.ai/code/artifact/1fd7fd5a-5561-47e6-a06f-e9577ed4d021**, titled *"How the SCADC clones tolerate toluene — OD-normalized lipidomics"*, dated 2026-07-18. The capella journal `a80ccb7c` (scadc/lipidomics) names it as awm artifact #856, and commit 8fc85db says the same. Reading that URL now returns "not found", so it was either deleted or published from another account.
  - **The source HTML still exists on capella:** `~/agentic_workspace/projects/scadc/writing-intro/data/_old/docs/reports/lipidomics_od_report.html` (337 KB, md5 5bdab053…). An identical copy is at `writing-intro/.awm/data.annex-retired/ai/`. A copy is also at `/home/tony/.claude/jobs/9268a2a8/tmp/lipid_od_report_capella.html`.
  - The same capella folder has the companion markdown reports:
    - `lipidomics_od_normalized.md` (#855)
    - `lipidomics_composition_per_sample.md` (#857)
    - `lipidomics_analysis_report.md` (2026-06-15, median-normalised; superseded by the OD-normalised analysis)
    - `lipidomics_sota_review.md`
- The two UUIDs you named are vesicle imaging only. `e008ba6e…` is the same page as `https://claude.ai/artifact/UfZ13YmWE915BCiE9YRkoj`, "Vesicle Membrane Per OD". `5aa4dd3f…` is `https://claude.ai/artifact/CCCcdFYMt1xdCrMvHAAgta`, "Segmentation Bake-off". The Artifact list shows no other lipid artifact.
- **Results after 2026-07-18 were never published as artifacts.** They exist only as readmes in the publish tree.
  - The publish tree exists only on **capella**: `~/agentic_workspace/projects/scadc/lipidomics/.awm/data/figures/publish/04_lipidomics/`.
  - It is not on altair. The `data/figures.dvc` manifest (7a7cb228…) is missing from altair's cache, so the tree cannot be materialised there.
  - The readmes that carry the results:
    - `06_identification/readme.md`
    - `07_lipid_class_enrichment/readme.md`
    - `05_clone_response/clone_response_identification_methods.md`
  - The top-level `readme.md` is your own note: *"please dont tunnel on these results … cherry on top if it validates ECSPr findings."*
- **Not everything on capella is backed up.** `dvc status` reports `data/figures` modified, and the capella worktree has 12 uncommitted changes. These capella files are newer than the pin and may exist nowhere else:
  - `clone_response_storey_volcano_only.svg`: no committed script writes it; it comes from the untracked `od_clone_response_volcano_nokde.py`.
  - `clone_response_storey_hits_identified.csv`
  - `clone_response_identification_methods.md`
  - `gem_universe.py` and `method_matrix.py`
- Session records are capella journals for scadc/lipidomics (`a80ccb7c`, `875826fb`, `a60324a4`, `886e6438`, `82a40c7f`, `342d8f2e`, `6e2bae77`, `6addd125`). Altair holds the two vesicle journals (`2671f9ce`, `2a2de9a4`).
- Code and commits are on branch `feat/lipidomics`:
  - OD analysis: 88cc3f0, 8fc85db.
  - Composition: b4a11c2, 295fd21.
  - Volcanoes: 24fb716.
  - Identification: 5f5ad5b.
  - Classification: b9b6cd3, 3228b49.
  - KDE rows and MS2Lipid rejection: 7868c34.
  - Vesicles: 5481ccc, 10bc6d7.
- Trilium note `scadc/results/lipidomics` embeds only `01_lipid_per_cell.svg` and `05_clone_response/clone_response_storey_volcano_only.svg`, served from 10.74.81.110, which is capella. Note `scadc/sketch` holds your draft results text: *"clone 2 overproduces specific lipids vs empty vector control and when subjected to toluene, clone 2 releases specific lipids into the supernatant."*

## 2. What the results say

### Design
- **Data:** the facility's MetaboScape merged table (`data/scadc/lipidomics/facility/metaboscape_merged.xlsx`). It has 3095 features; filtering against blanks (≥5×) and on QC CV (≤30%) leaves 2180. There are 48 biological samples. The MS-DIAL pipeline was abandoned because its output was too sparse.
- **Instrument:** timsTOF Pro, DDA-PASEF.
- **Strains:**
  - Pellet: Epi300 (parent), EpCC1 (pCC1 empty vector), Clone1, Clone2.
  - Supernatant: ESi300 and ESCC1 are the same two controls under supernatant names.
- **Factors:** ctrl vs 0.1% toluene, 6 d in M9-glucose; pellet (P) vs supernatant (S); n=3 per cell. Source: `main/lipids/README.md`.
- **Normalisation:** peak area ÷ culture OD600 (A. Szeitz's recipe). The group geometric-mean OD is the primary value.
  - OD600, ctrl → tol: EPI300 0.740 → 0.213; EpCC1 0.503 → 0.105; Clone1 0.450 → 0.336; Clone2 0.340 → 0.408.
  - Source: `main/lipids/od_values.csv` and the HTML report.

### Headline from the 2026-07-18 HTML report (the "artifact")
- Toluene raises total lipid per OD in the background strains but not in the clones (pellet, log2 tol/ctrl):

  | Strain | log2 tol/ctrl | Features up |
  |---|---|---|
  | Epi300 | +1.34 (2.5×) | 66–168 (background, up to 6× in supernatant) |
  | EpCC1 | +1.40 (2.6×) | (as above) |
  | Clone1 | +0.13 | 0–5 |
  | Clone2 | +0.15 | 0–5 |

- The strain × treatment interaction is significant for 90–254 features.
- This overturned the earlier median-normalised result of "toluene: 0 significant".
- The report proposes four mechanisms:
  - **M1:** the clones hold their lipid homeostasis under toluene.
  - **M2:** the clones are constitutively different. 436 pellet and 647 supernatant features differ more than 2× from the parent in both clones, and about 90% of them are unannotated.
  - **M3 (hypothesis):** the clones change membrane order in opposite directions. Clone1 has more saturated, shorter chains; Clone2 has longer, more unsaturated chains.
  - **M4 (ruled out):** lysis. There is no lyso-lipid build-up.
- The per-sample composition work (`875826fb`) adds two points. Headgroup mix is conserved (TV distance 0.02–0.10), and no toluene shift survives FDR. On the chain axis, Clone2 runs +2.4 to 2.6 C longer (q≈0.06) and Clone1 −1.5 to 1.7 C shorter, in both fractions.

### Clone-response volcano, Storey q (`04_lipidomics/05_clone_response/`)
- **Grid:** 4 columns:
  1. pellet, clone vs pCC1 (−tol)
  2. pellet, clone +tol vs −tol
  3. supernatant, clone vs pCC1 (−tol)
  4. supernatant, clone +tol vs −tol
- A hit is q<0.05 and |log2FC|>1, using median log2FC and Welch p. The code is `od_clone_response_volcano.py`.
- **There are 30 hit rows covering 29 unique features.** F1988 is a hit for both clones. Source: `clone_response_storey_hits.csv`.

  | Panel | Hits | Direction |
  |---|---|---|
  | Clone2 pellet vs pCC1 | **14** | all up (log2FC +1.14 to +3.35) |
  | Clone2 supernatant +tol | **8** | **7 up**, 1 down; pi0 = 0.81 |
  | Clone2 pellet +tol | 2 | both down (F2575 −1.67, F1011 −1.48) |
  | Clone1 supernatant vs pCC1 | 5 | all down (−1.5 to −4.4) |
  | Clone1 pellet vs pCC1 | 1 | up (F1988, +1.11) |
  | Clone1 +tol (either fraction) | 0 | — |
  | Clone2 supernatant vs pCC1 | 0 | — |

- **By lipid class (best evidence per hit):**
  - Clone2 pellet up-hits include **F0025 HBMP 16:1_18:1_16:0** (an acyl-PG; facility-named, L2). They also include F1942, PE/PC by mass balance, chains 17:1*/16:1/16:0/18:1. Most of the rest are dark.
  - The 7 Clone2 supernatant +tol up-hits are mainly phospholipids:
    - **F0161 PS** (facility-named, but the PS(18:3/16:0) chains are not supported by its own MS/MS).
    - **F2799 PE** (4 methods agree).
    - **F2873 and F1683, PG family.**
    - F2475, F0415 and F1515.
  - Five of those seven can now be called, and all five are membrane lipids.
  - Clone1 supernatant down-hits include **F0021 HBMP 14:0/16:1/16:0** (L2) and F1976 (PE/PC).
- **These enrichments are not significant.**
  - Fisher membrane-enrichment test: p=0.59 against an 81.6% background.
  - Curvature test: p=1.00.
  - No headgroup test survives Holm. The best is PE/PC, continuous across all features: p=0.0029 raw, Holm 0.069.
  - The 7-hit test is structurally underpowered.
  - Sources: `07_lipid_class_enrichment/readme.md` and journal `82a40c7f`.

### Identification lane (`06_identification/readme.md`)
- **MSI grades for the 29 hits:** L2 = 3, L3 = 16, L4 = 1, L5 = 9.
- **No public library names any of the 26 dark features.** GNPS, the MassIVE index, LIPID MAPS and MassBank were all searched. LIPID MAPS does not even contain HBMP.
- **Acyl chains can be read off the raw MS/MS:** 12 of 16 negative-mode features give their chains, and both HBMP controls match chain-for-chain.
  - `17:1*` could equally be 17:0-cyclopropane.
- **F2575 is a newly named HBMP/acyl-PG.** Three independent methods converge on it.
- **No cardiolipin is present.** This is a measured non-detection, and PG is not depleted.
- Two features (F1481, F1620) recur unidentified in 8 or more public datasets.

### Membrane and curvature classification (`07_lipid_class_enrichment/readme.md`)
- This covers negative mode only, 800 features.
- **Coverage:** 96.4% called, in four tiers:

  | Tier | Evidence | Features | Share of signal |
  |---|---|---|---|
  | 1 | MS/MS mass balance | 154 | 69.1% |
  | 2 | Formula / facility class | 27 | — |
  | 3 | Logistic model | 590 | 29.2% |
  | 4 | Abstain | 29 | — |

- **Membrane model:** AUC 0.982. Specificity rests on only 17 negatives (95% CI 0.82–1.00).
- **Curvature model:** AUC 0.888. The prior column covers 95.2% and the strict column 9.8%, because PE and PC cannot be told apart by mass.
- **Composition check:** tiers 1–2 give 78.9% PE-like signal, which matches E. coli's known 70–80%. All tiers together give 59.4%.
- **Abundance on the canonical grid: nothing survives Holm** for either clone.
- **The signal is in the reference arm.** pCC1's membrane per OD rises +1.49 log2 (2.8×, p=0.0012) in pellet and +2.24 log2 (4.7×, p=0.0034) in supernatant. Clone2 moves +0.07 and +0.26. The interaction is Holm ≤ 0.0004.
- **That rise is mostly OD.** pCC1's OD falls about 4×, so the readme says to write *"pCC1 barely grew and Clone2 did."*
- MS2Lipid was tested as an alternative classifier and rejected: 77.6% vs 96.3% for the trivial baseline on the membrane gate.

### OD-normalisation caveats
- **Pellet and supernatant behave differently.** The correlation r(log2 total signal, log2 OD) is **+0.60 in pellet and −0.34 in supernatant**. Dividing supernatant signal by OD therefore stacks two effects instead of cancelling one, so supernatant per-OD amounts are inflated by construction.
- **The clean supernatant statement is in raw signal:** pCC1+tol released 1.3× more lipid than Clone2 from about ¼ of the biomass.
- **Parent +tol OD values (0.11–0.29) are near the plate floor.**
- **The pairing between OD replicates and lipidomics replicates is undocumented.** The geometric-mean OD avoids needing it.
- **About 90% of features are unannotated, and PC is over-called.**
- **Proportion readouts are not "OD-normalised".** The OD cancels in a proportion.
- **Proportions depend on which features are selected:** 4 of 8 proportion contrasts flip sign between label sets, against 0 of 8 for amount contrasts.

### GUV vesicle imaging (artifact UfZ13YmWE915BCiE9YRkoj; `main/vesicle_panels/README.md`)
- **Method:** imaged 2026-05-22. 228k particles across 103 fields were segmented with sep, chosen by the bake-off. The primary population is radius ≥106 nm.
- **Membrane µm² per 1000 µm² per OD600, mean of n=2** ("floor" = particle density over the sample-free control):

  | Strain | −tol | +tol |
  |---|---|---|
  | Clone1 | 319.8 (1.95× floor) | 199.0 (3.67×) |
  | PCC1 | 125.3 (3.36×) | **366.3** (1.93×) |
  | Clone2 | 124.6 (2.31×) | **20.6 (0.46×, below floor)** |
  | EPI300 | 30.6 (1.46×, at floor) | 54.5 (1.00×, at floor) |

- **Caveats:**
  - PCC1+tol ranks first only because its OD (0.099, 0.103) is tiny.
  - Clone1 −tol depends on 4 hand-rejected fields: 320 with them, 75 without.
  - The OD values come from the lipidomics culture set (6 d), not from the imaging day.
  - Sizes are apparent sizes, an upper bound blurred by the PSF.
  - With n=2, no statistical test was run.
- **This partly cuts against the sketch.** Clone2 under toluene sheds the least membrane per OD, at or below the floor. That does not fit a reading of "flushing toluene out through vesicles."
- The Clone2 supernatant +tol lipid hits are a feature-level result, not a total-membrane one.

## 3. Candidate figures for the manuscript

All `04_lipidomics` paths are under capella `…/scadc/lipidomics/.awm/data/figures/publish/04_lipidomics/`, each as .png and .svg.

- `01_lipid_per_cell` — total lipid per OD, 4 cultures × P/S × ctrl/tol, with per-replicate dots and OD I-beams. The background strains rise under toluene; the clones stay flat. Embedded in the Trilium note. (`od_publish_figs.py`)
- `02_composition_invariant` — stacked class-family fractions, ctrl → tol, annotated with TV distance. The headgroup mix does not change.
- `03_toluene_lfc_clone_vs_control` — 2×2 per-feature scatter of toluene log2FC, clone vs control (Epi300/EpCC1), pellet. (`od_lfc_scatter.py`)
- `04_volcano_species/01_pellet_control`, `02_pellet_toluene`, `03_supernatant_control`, `04_supernatant_toluene` — per-condition 2×2 volcanoes of clone × (EPI300, EpCC1), BH-FDR. (`od_strain_volcano.py`)
- `05_clone_response/clone_response_storey` — the main figure: a 4×4 grid of Clone1/Clone2 volcanoes plus KDE density rows for all / membrane / curvature-forcing features, Storey q. The KDE rows use negative mode only (800/2180) and are stamped as such.
- `05_clone_response/clone_response_storey_volcano_only` — the same figure without the KDE rows. This is the version in Trilium. **It is not pinned and no committed script produces it.**
- Tables:
  - `05_clone_response/clone_response_storey_hits.csv` (30 hit rows)
  - `…_hits_bestcall.csv` (hits with the single best call)
  - `…_hits_identified.csv` (147 calls × 19 methods; unpinned)
  - `clone_response_identification_methods.md` (methods text)
- `06_identification/01_evidence_per_feature` — which evidence source reached each of the 29 hits, at what confidence. Tables: `clone_response_best_call_per_feature.csv`, `clone_response_acyl_fragments.csv`, `clone_response_identification_candidates.csv`.
- `07_lipid_class_enrichment/`:
  - `01_Membrane_classification_coverage_and_accuracy` — tiers, CV, covariate shift, composition check.
  - `02_Membrane_lipid_per_cell_Clone2_vs_pCC1` — 4 conditions × 4 readouts, per replicate.
  - `03_Does_the_result_depend_on_the_classifier` — sign concordance and OD decomposition. (Supplementary.)
- Old figures in git, superseded:
  - Panels of the 07-18 HTML report: `figures/lipids/od_summary_metaboscape.png` (4-panel A–D OD summary) and `figures/lipids/od_mechanism_metaboscape.png` (acyl-unsaturation shift and constitutive features).
  - Also `composition_chain_axis_metaboscape.png` (the divergent-chain pattern), `composition_per_sample_metaboscape.png`, and older `pca_*`, `heatmap_topvar`, `class_composition`, `saturation` and `chain_length` plots.
- Vesicle panels, on altair at `/home/tony/agentic_workspace/projects/scadc/lipidomics/main/vesicle_panels/`. **The rendered images are gitignored and not pinned**; the CSVs are committed.
  - `vesicle_surface_area.png/.html` — density, membrane area and membrane per OD, with the floor line.
  - `vesicle_size_distribution.png/.html` — radius ECDFs, all detections vs resolved. Clone1 sheds larger vesicles.
  - `vesicle_threshold_sweep.png/.html` — the ranking holds across thresholds (supplementary).
  - `bakeoff/` overlays and `index.html` — segmentation QC (supplementary).
  - Data tables: `vesicle_surface_area.csv`, `particles.csv.gz`, `control_floor.csv`.

Not analysed for the manuscript: DLS and zeta data for Epi300 only, at `data/scadc/lipidomics/particle_size/` (27 Aug 2025), with notebooks `dls_*.ipynb`.

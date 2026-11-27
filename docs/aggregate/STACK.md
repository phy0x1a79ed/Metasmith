# Aggregate — discussion stack

**Goal.** Aggregate every tool and pipeline the workspace has ever run into metasmith's standard library, so one install covers it, in parallel with `engine/install-loop` (the first aggregation attempt, which has gone slower than expected). Extend coverage beyond KBase: scrape Galaxy, grow geospatial query into other domains, and add a quick ML training-loop template.

**Decisions:** `docs/aggregate/DECISIONS.md` (none closed yet).

## Current

`template-blocks` — templates become additive blocks a plan can stack; first question: where composition happens.

## Waiting on the user

- `template-blocks` → where composition happens (plan-time union vs author-time). Asked 2026-11-27.
- `asv-pipeline` → indicspecies cap (≤3-group combinations for labels with >8 levels): keep, or skip such labels. Asked 2026-11-27.
- `curation-ledger` → the tools Tony's pass did not cover (phylogenetics/TreeSAPP, featureCounts + clusterProfiler, CoverM, Kalen ONT set, tiara/MetaEuk, psortm, AlphaFold/CLIPZyme, nf-core/mag comparator-only, superseded tools). Asked 2026-11-27; Tony chose to go pipeline by pipeline instead.

## Preferences

- 2026-11-19: Do not build `msm_solver` per worktree; link the released engine (env `msm_gate_0251`).
- 2026-11-27: Curate pipeline by pipeline, biggest first. ENGCYC counts as done.
- 2026-11-27: Use nf-core as inspiration for the RNA-seq lane, not as a wrapped pipeline.

## Stack

- `template-blocks` — "a way where we could add additional blocks targets to a plan. So templates can be additive … split the ENG CYC into more sensible chunks … an ASV to mag mapping template, which could be just like a target"
  - Survey: a template is one spec.yml (cases, target_types, input manifest), authored from a Python TARGETS list (`src/metasmith_libraries/engcyc_metagenomics.py`); `engcyc_metagenomics_lite` already composes at author time. No plan-time composition. `engine/variadic` adds TargetSet members (a386d875), related. Gotchas: each target costs solve rate; one unreachable target drops the plan silently.
- `asv-pipeline` — "next large one … Maybe ASV analysis"; Kalen's seat runs it now
  - ASPIRE template ported 35 rows (22 match, 12 fixed, 1 open), proven on cyano_r1 (equal to upstream) and ab48_r1 (621 tasks, checked against the July DADA2 cohorts). QIIME2 only in taxonomy (vsearch classifier). DADA2 = replaced-by ASPIRE.
  - Proposed drops: augmentation, batch correction, outlier checker, four lung-only analyses, MitoMaster web lookup. Follow-up: negative controls, group-size drop in curate.
  - `asv-mag-block` — "some links between the ASV table and the metagenomics": barrnap → skani_dedup → collect_mags → asv_mag_link → asv_mag_network / module_mag_anchors; ENGCYC's quality MAGs are already the input type; add GTDB-Tk taxonomy. Becomes a block under `template-blocks`. Gate: solve → plan → rerun ab48_e5.
- `curation-ledger` — "run a curation pass … decide what was dropped or replaced, represented by, and then journal that … hit every tool we've ever run"
  - Rules from Tony (2026-11-27), in DECISIONS § curation-ledger rules: in a template = in; discuss only what it shadows; drop logistics and ML; TOSICA dropped.
  - Review page now takes a keep / drop / discuss mark per tool (db collection `calls`, 93a8f230).
  - Harvest landed: `harvest.tsv`, 209 tools, 116 with a std transform, 93 without. Census scripts in `research/aggregate/harvest/`. Not counted: notebooks/markdown, the 398 KBase stubs (separate pass), Galaxy (never run here).
- `viz-set` — "Scikit-learn … UMap … we need like a visualization downstream for ENGCYC" (also hdbscan, leiden; aspire already ships umap_clustering)
- `fabfos-into-std` — "FabFOS needs to be like added in here" (std has 6 fabfos transforms + fosmid template; src/fabfos owns the rest)
- `lipidomics-pipeline` — "MZMine … there's a new lipidomics pipeline" (compound_id library on feat/fabfos/lipidomics-abundance, research/fabfos/lipidomics)
- `euk-transcriptomics` — "we need a eukaryotic transcriptomics pipeline because we do deal with like algae" (STAR, BRAKER3, StringTie, DESeq2 on release; no template)
- `solve-gate` — solve every template and research root on the released solver
- `promote` — RNA-seq (research/rnaseq + featureCounts + DE→gene set), phylogenetics group, CoverM, MMseqs2, binners
- `galaxy-scrape` — "we may want to do a scrape for Galaxy … cover as much of bioinformatics as possible"
- `geoquery-domains` — "start on stuff like geospatial query, and that'll branch out into other domains"
- `ml-template` — "a quick machine learning training loop template"
- `rnaseq-integration` — "can we use an established pipeline? nf-core maybe? … as inspiration"
  - `gene-set-producer` — DE → gene set; nothing produces `annotation::gene_set`
- `kbase-followups` — carried from the KBase readiness walk (journal 59ef2db5)
  - `app-coverage` — proposed close: 493→54 holds; ~15 reassignments to `tasks.yml`
  - `scope-bar` — which entries are judged, against what bar
  - `prove-kbase-domain` — reachability / transform tests / solve argument
  - `drop-all-diagnostics` — say which target was unreachable
  - `tool-fidelity` — planner substitutes type-valid shortcuts

## Workers

- (none running)

## Closed

- `survey` (2026-11-27) — done = every tool is a transform or has a disposition; three-layer gate; curation first.

# Aggregate — discussion stack

**Goal.** Aggregate every tool and pipeline the workspace has ever run into metasmith's standard library, so one install covers it, in parallel with `engine/install-loop` (the first aggregation attempt, which has gone slower than expected). Extend coverage beyond KBase: scrape Galaxy, grow geospatial query into other domains, and add a quick ML training-loop template.

**Decisions:** `docs/aggregate/DECISIONS.md` (none closed yet).

## Current

`curation-ledger` — every tool ever run, each with a disposition, journaled.

## Waiting on the user

- `curation-ledger` → confirm the ledger's columns and disposition vocabulary.

## Preferences

- 2026-11-19: Do not build `msm_solver` per worktree; link the released engine (env `msm_gate_0251`).
- 2026-11-27: Use nf-core as inspiration for the RNA-seq lane, not as a wrapped pipeline.

## Stack

- `curation-ledger` — "run a curation pass … decide what was dropped or replaced, represented by, and then journal that … hit every tool we've ever run"
  - Harvest landed: `harvest.tsv`, 209 tools, 116 with a std transform, 93 without. Census scripts in `research/aggregate/harvest/`. Not counted: notebooks/markdown, the 398 KBase stubs (separate pass), Galaxy (never run here).
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

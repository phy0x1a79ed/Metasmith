# Aggregate — discussion stack

**Goal.** Aggregate every tool and pipeline the workspace has ever run into metasmith's standard library, so one install covers it, in parallel with `engine/install-loop` (the first aggregation attempt, which has gone slower than expected). Extend coverage beyond KBase: scrape Galaxy, grow geospatial query into other domains, and add a quick ML training-loop template.

**Decisions:** `docs/aggregate/DECISIONS.md` (none closed yet).

## Current

`survey` — a comprehensive survey of everything there is to aggregate.

## Waiting on the user

- (none until the survey lands)

## Preferences

- 2026-11-19: Do not build `msm_solver` per worktree; link the released engine (env `msm_gate_0251`).
- 2026-11-27: Use nf-core as inspiration for the RNA-seq lane, not as a wrapped pipeline.

## Stack

- `survey` — "start with like a comprehensive survey of all of the other stuff"
  - Done inline (git sweep): release holds 375 std transforms in 15 groups, 17 templates, 115 envs, 27 type files; research roots hold 587 more (398 KBase stubs). 96 transform/template/type/env files on unmerged branches, led by fabfos/lipidomics-abundance (18), engine/manuscript(-figures) (16 each), lab/kalen-dofher (10).
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

- E2E install-loop survey — state, problem list, time sinks, lessons.
- Cross-project tool survey — every tool run anywhere, and whether it is a release transform.
- Galaxy / geoquery / ML survey — catalog scale and API, geoquery state, prior ML work.

## Closed

- (none)

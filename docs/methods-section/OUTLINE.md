# Methods outline (d2)

The point-form draft of the d2 Methods and the single source for every redraft. Levels: section, then paragraph, then points. Facts and sources come from `draft.md`; this file holds only what the user has chosen.

Status per entry: `proposed`, `agreed` (points accepted), `accepted` (prose accepted), `in doc`.

## Level 1: sections

Order and names (outline-sections, 2026-11-26): Planning, Specification, Execution, Contracts, Benchmarks. Declarations sit outside Methods as their own top-level section.

### M1. Planning — agreed (outline-sections, 2026-11-26)
- Role: the internals and definitions; how the planner works.
- Key message: contracts are matched through property-set types and lineage constraints, and a seeded search composes them into a verified plan.
- Paragraphs: to be set in outline-paragraphs (candidates: types; lineage; grouping and splitting; search; selection; refinement; determinism and verification).

### M2. Specification — agreed (outline-sections, 2026-11-26)
- Role: the surrounding infrastructure that turns a user's intent into a planning problem.
- Key message: a user gives typed data instances and targets through the API, CLI or GUI, and the planner treats each target as one more transform.
- Paragraphs: to be set in outline-paragraphs (candidates: interfaces; data instances and given types; targets as transforms; lineage in targets; variadic inputs; optional branching; parallel planned cases; known issues and workarounds).

### M3. Execution — agreed (outline-sections, 2026-11-26)
- Role: how a plan runs.
- Key message: each step compiles to a Nextflow process, runs through local or SLURM presets with each tool in its own container, and is cached under its lineage.
- Paragraphs: to be set in outline-paragraphs (candidates: compilation to Nextflow; agents and presets; containers and relay; caching; outputs).

### M4. Contracts — agreed (outline-sections, 2026-11-26)
- Role: how contracts are written and designed.
- Key message: TODO, from the user.
- Paragraphs: to be set in outline-paragraphs.

### M5. Benchmarks — agreed (outline-sections, 2026-11-26)
- Role: how each Results benchmark was run and scored.
- Key message: each published pipeline was rebuilt as contracts with its own tools and parameters, run on the original data, and compared output by output.
- Paragraphs: shared setup; nf-core/mag; MAG comparison; lines of code; viromics; vOTU comparison; assembler swaps; metaGEM; update ablation; KofamScan; combined workflow and cost.

## Declarations (own top-level section, beside Methods) — agreed (outline-sections, 2026-11-26)
- Role: declarations a journal requires.
- Paragraphs: statistics; AI assisted development; data and code availability.

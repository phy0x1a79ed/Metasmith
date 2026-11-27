# Methods outline (d2)

The point-form draft of the d2 Methods and the single source for every redraft. Levels: section, then paragraph, then points. Facts and sources come from `draft.md`; this file holds only what the user has chosen.

Status per entry: `proposed`, `agreed` (points accepted), `accepted` (prose accepted), `in doc`.

## Terms (terms, 2026-11-27)

Define each term only from those above it; use one name per idea throughout the paper.

1. property: one statement about data.
2. type: a set of properties; X satisfies Y when X ⊇ Y.
3. contract: the input types a tool requires and the output types it promises.
4. step: one use of a contract in a plan.
5. port: a typed position on a step, one per output type, with a fixed lineage; later steps bind their inputs to ports. Each port compiles to one Nextflow channel. (Code: `Endpoint`; d0.2 called it a data node, DN.)
6. plan: a DAG of steps joined through ports.
7. instance: the data that fills a port when the plan runs.

"Transform" names the code object (contract plus script) and appears only in Execution. "Endpoint", "application" and "data node" leave the paper.

## Level 1: sections

Order and names (outline-sections, 2026-11-26): Planning, Specification, Execution, Contracts, Benchmarks. Declarations sit outside Methods as their own top-level section.

### M1. Planning — agreed (outline-sections, 2026-11-26)
- Role: the internals and definitions; how the planner works.
- Key message: contracts are matched through property-set types and lineage constraints, and a seeded search composes them into a verified plan.
- Paragraphs (outline-paragraphs, 2026-11-26): the minimum to convey the implementation; the Results carry the motivation. Group-by is not used by the solver and moves to Execution.

#### P1. Types and lineage — proposed
- Role: the formal matching rules the solver applies.
- Key message: a port feeds an input when its type holds every property of the input's type and its lineage covers the input's lineage requirement.
- Points (revised in terms, 2026-11-27; keep the original prose, reshuffled; no EDAM claim):
  1. Types are sets of properties, each narrowing the range of variation of the data.
  2. A type X satisfies Y when X has all of the properties of Y, S(X,Y) ≡ X ⊇ Y.
  3. A port is a typed position on a step with a fixed lineage, and inputs bind to ports.
  4. A port X satisfies a lineage requirement Z when X was produced from ports with types that map to each type in Z, L(X,Z).
- Note: the d3 formula is kept (some ancestor's type satisfies each type in Z). The code is stricter on purpose: it checks the port bound to the ancestor input itself (`workflow_solver/src/search.rs:215`). The Methods must state the strict check and explain why (Tony, 2026-11-27). EDAM dropped: "a rough link". 

#### P2. Search and selection — proposed
- Role: how the plan is found.
- Key message: a PUCT search grows partial plans from the givens and targets until no input is left unfed.
- Points: next, after P1 (state, base case, frontier expansion, PUCT selection).

#### P3. Refinement and verification — proposed
- Role: how the plan is trimmed and trusted.
- Key message: a refiner removes unneeded steps, the seeded search makes plans reproducible, and an independent checker verifies each plan.

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

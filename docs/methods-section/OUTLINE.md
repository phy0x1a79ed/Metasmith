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

Grouping by concept (paragraph-sketch, 2026-11-27): "do the grouping by concept".

#### P1. Types — proposed
- Role: how types work, the property-set type and its satisfaction test.
- Key message: a type is a set of properties, and one type satisfies another when it has all of its properties.
- Points (paragraph-points, 2026-11-27):
  1. Types are sets of properties, and each property narrows the range of variation of the data it describes.
  2. A type X satisfies Y if X has all of the properties of Y, S(X,Y) ≡ X ⊇ Y.
  3. Abstract types follow from the subset test: a type with fewer properties is satisfied by every type that adds to it, but not the reverse. Example: a wooden chair is a chair, but not every chair is wooden.
- Note: where the test is used (givens, inputs, lineage) belongs to P2. No EDAM claim: "a rough link".

#### P2. Contracts — proposed
- Role: contracts, the ports they create as steps, and why contracts need lineage constraints.
- Key message: a step exposes one port per output type, inputs bind to ports, and a contract can require that bound ports share lineage.
- Earlier points: a port is a typed position on a step with a fixed lineage, and inputs bind to ports; a port X satisfies a lineage requirement Z when X was produced from ports with types that map to each type in Z, L(X,Z).
- Note: the d3 formula is type-based; the code is stricter on purpose and checks the port bound to the ancestor input itself (`workflow_solver/src/search.rs:215`). State the strict check and explain why (Tony, 2026-11-27). M4 covers contract authoring; this paragraph covers only what the planner needs.

#### P3. Planning search — proposed
- Role: how the plan is found.
- Key message: a PUCT search grows partial plans from the givens and the target until no input is left unbound.
- Covers: search state and base case, expansion (one step per child, one child per valid binding), PUCT selection.

#### P4. Refinement — proposed
- Role: the edge-refinement pass after the search.
- Key message: a short pass swaps single edges and prunes unneeded steps.

#### P5. Verification — proposed
- Role: how a plan is trusted and reproduced.
- Key message: an independent checker verifies each plan, and a fixed seed makes plans reproducible.

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

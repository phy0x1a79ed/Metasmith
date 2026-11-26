# Methods outline (d2)

The point-form draft of the d2 Methods and the single source for every redraft. Levels: section, then paragraph, then points. Facts and sources come from `draft.md`; this file holds only what the user has chosen.

Status per entry: `proposed`, `agreed` (points accepted), `accepted` (prose accepted), `in doc`.

## Level 1: sections

Order follows the Results: the interface, then the contract model, then planning and running, then each benchmark.

### M1. Interface — proposed
- Role: describes the layers a user can work through.
- Key message: the Python API, the CLI and the GUI expose the same operations in layers over the external tools.
- Paragraphs: interface layers.

### M2. Type system — proposed
- Role: formal definitions behind the contracts in the Results.
- Key message: contracts are matched through property-set types, lineage constraints, and grouping with implicit splitting.
- Paragraphs: types; lineage; grouping and splitting; cases.

### M3. Solver — proposed
- Role: how a specification becomes a plan.
- Key message: a seeded PUCT search composes the plan, a refiner trims it, and an independent verifier checks it.
- Paragraphs: search; selection; refinement; determinism and verification.

### M4. Data instances and caching — proposed
- Role: how data is identified and reused.
- Key message: every instance is identified by its lineage, and each execution is cached under that identity.
- Paragraphs: identity and caching.

### M5. Compilation and execution — proposed
- Role: how a plan runs on Nextflow.
- Key message: each step compiles to a Nextflow process, and an agent stages and runs the workflow with each tool in its own container.
- Paragraphs: transforms; compilation; execution; outputs.

### M6. Contract authoring — proposed
- Role: how the benchmark contracts were written.
- Key message: TODO, from the user.
- Paragraphs: authoring; Figure 2 toy library.

### M7. Benchmarks — proposed
- Role: how each Results benchmark was run and scored.
- Key message: each published pipeline was rebuilt as contracts with its own tools and parameters, run on the original data, and compared output by output.
- Paragraphs: shared setup (cluster, MAG quality, CPU hours); nf-core/mag; MAG comparison; lines of code; viromics; vOTU comparison; assembler swaps; metaGEM; update ablation; KofamScan; combined workflow and cost.

### M8. Statistics, AI use, availability — proposed
- Role: closing statements a journal requires.
- Key message: none; these are declarations.
- Paragraphs: statistics; AI assisted development; data and code availability.

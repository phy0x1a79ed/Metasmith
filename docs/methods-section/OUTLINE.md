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

#### P1. Types — agreed (paragraph-points, 2026-11-27)
- Role: how types work, the property-set type and its satisfaction test.
- Key message: a type is a set of properties, and one type satisfies another when it has all of its properties.
- Points (paragraph-points, 2026-11-27):
  1. Types are sets of properties, and each property narrows the range of variation of the data it describes.
  2. A type X satisfies Y if X has all of the properties of Y, S(X,Y) ≡ X ⊇ Y.
  3. Abstract types, which have fewer properties and so are more general, are satisfied by every more specific type, but not the reverse. Example: a wooden chair is a chair, but not every chair is wooden.
- Note: where the test is used (givens, inputs, lineage) belongs to P2. No EDAM claim: "a rough link".

#### P2. Contracts — agreed (paragraph-points, 2026-11-27)
- Role: contracts, the ports they create as steps, and why contracts need lineage constraints.
- Key message: a contract lists the input types a tool requires and the output types it promises, and its inputs can require that the data they receive share an origin.
- Points:
  1. A contract states the input types a tool requires and the output types it promises.
  2. Each use of a contract in a plan is a step, which binds each input to a port whose type satisfies it and exposes one new port per output type.
  3. Each port records its lineage, the ports its step consumed.
  4. A contract that accepts a general type loses which specific data came in; a compressor that accepts any file yields only a "compressed file" (flow F1, 2026-11-27). So an input can require that its port descends from the port bound to another input of the same step. Example: mapping reads to an assembly requires the assembly built from those reads.
  5. The check requires that exact port, not any ancestor of a matching type, so data from unrelated sources are never joined.
- Note: inputs declare other inputs of the same contract as parents (`src/metasmith/models/solver.py:180`); the bound port must be an ancestor (`workflow_solver/src/search.rs:215`). The d3 formula (type-based) is replaced by the strict check; Tony confirmed the reason, 2026-11-27. M4 covers contract authoring.

#### P3. Optional branching — proposed (moved from S4, 2026-11-27: a contract feature, after Contracts)
- Role: contracts with alternative outcomes.
- Key message: a contract can declare alternative outputs decided at run time, and the plan holds a route below every outcome.
- Points:
  1. Some tools write one of several sets of outputs, decided only at run time, so a contract can declare alternative output groups, which makes it a fork.
  2. A single solve plans for one group of each fork, and every other group is planned separately from the plan up to the fork and merged in, so the plan holds a route below every outcome.
  3. At run time each task writes only the group it produced, and the branches it did not take stay empty.
- Note: rc `docs/metasmith/architecture.md` ("A product group is one possible outcome"; "A fork outcome is a case"); `case_merge.PlanCases`; `optional: true` in codegen. No standard-library contract is a fork today. Forward reference: the merge is the parallel-case merge (S4).

#### P4. Planning search — agreed (paragraph-points, 2026-11-27)
- Role: how the plan is found.
- Key message: a PUCT search grows partial plans from the givens and the target until no input is left unbound.
- Points:
  1. Given a library of contracts, the givens and a target, the planner must find a plan (flow F2, 2026-11-27). We framed planning as a tree search of the Monte Carlo tree search (MCTS) family: each node is a search state, each edge adds one step, and the search walks from the root until it reaches a solved state.
  2. A search state is a partial plan; the root holds only the given steps and the target step, and a search state is solved when every input is bound.
  3. The frontier holds every step that could be added next, one entry per valid binding of a contract's inputs to existing ports.
  4. Before the search, a breadth-first search (BFS) that ignores lineage walks back from the target's inputs to the contracts that can produce them, level by level, so each contract's distance is the fewest steps between it and the target; it also counts the routes from each contract to the target and drops contracts it never reaches.
  5. PUCT scores each frontier step a, and the highest is grown next: U(a) = Q(t) + c·P(a)·√(1+N)/(1+n(t)), where t is a's contract, Q(t) is the mean reward t has earned, n(t) is how often t was picked, N is all picks, and P(a) is a prior favouring steps closer to the target and with more routes to it. The first term exploits contracts that made progress; the second favours promising, rarely tried steps and shrinks as a contract is picked.
  6. The reward is the gain in the target's satisfied inputs, or 1 when solved; there are no random rollouts, and the search stops at the first solved plan or a fixed iteration limit.
  7. A seeded random-number generator and a fixed iteration order make the same request return the same plan (moved from Verification, 2026-11-27).
- Note: statistics are per contract, not per node (`policy.rs:469`). Constants (`policy.rs:160`): c = 1.5; prior = softmax at T = 0.5 over min-max normalized channels, closeness 1 - d/d_max and routes 1 - 1/(1 + r/10) (`mcts.rs:127`), weighted 75:20; unvisited Q = 1.5; recency decay 0.985; self-feed penalty w2 = 0.95; reward = 2x progress delta clamped to [0,1]; max_iter 256. BFS in `problem.rs:346`. Reuse the d3 solver paragraph prose.

#### P5. Refinement — agreed (paragraph-points, 2026-11-27)
- Role: the edge-refinement pass after the search.
- Key message: a short search over single-edge swaps tidies the first plan found and removes steps it does not need.
- Points:
  1. Lineage makes the search path-dependent and PUCT is optimistic, so the first solved plan is not guaranteed to be the simplest.
  2. Each candidate rebinds one step's input to another existing port and rebuilds every step downstream so its lineage stays correct.
  3. A candidate must still pass the plan conditions of P6, chiefly that every step can be scheduled and every lineage constraint holds (flow F3, 2026-11-27).
  4. Valid candidates are ranked first by how few distinct ports their lineage constraints anchor to, then by how close those anchors sit to the inputs that need them.
  5. The same PUCT rule picks which candidate to expand, for a fixed budget of rounds; the best valid plan wins, and steps no longer connected to the target are removed.
  6. In development testing, the vast majority of plans were already optimal before refinement (Tony, 2026-11-27: the refiner is a real safety net; do not dwell on how often it acts).
- Note: score = 1000 x (sum p log2 p over anchor-port usage) + (- mean normalized anchor depth, in [-1, 0]), a lexicographic order written as a sum (`refine.rs:344`, from c71a706b, Aug 2025). Budget 8 (`REFINER_BUDGET`); statistics keyed on the swapped-in contract.
- Effect (records, not rerun): under the old selection rule, 2 of 55 case-seed pairs changed (`isolate_assembly_from_long_reads` seeds 7 and 99: 13 -> 11 and 13 -> 9 steps); every other pair unchanged (`data/metasmith/plans/08-where-the-unpinned-solve-goes.md`). Under PUCT the search finds the 9-step plan directly (`02-puct-selection-poc.md`), and `found_on` = 1 on every measured case, so no recorded PUCT plan is changed by the refiner.

#### P6. Verification — agreed (paragraph-points, 2026-11-27)
- Role: why and how every plan is checked.
- Key message: rather than prove the solver correct, we proved a small witness checker correct and run it on every plan.
- Points (paragraph-points, 2026-11-27; Tony's ladder: a provably correct solver is hard, so prove a witness checker, and the checker gates every plan; intro first, then the workings):
  1. Proving a search-based solver correct is hard, because its path depends on heuristics and on the order it explores.
  2. Checking a finished plan is far simpler, so we wrote a witness checker and proved that instead.
  3. Every plan the solver returns passes through the checker, and a plan that fails is refused with the condition it broke.
  4. The checker reads only the problem and the plan and tests ten conditions, among them that every binding satisfies its input type and lineage, every port has one producer and is given or produced before use, the steps form a DAG, and the target appears exactly once.
  5. A Lean 4 proof shows that the checker's Rust code returns true exactly when a plan meets the formal specification, so any plan it accepts is correct by that specification.
- Note: `check_spec`, `src/solver_witness/lean/Proof/Compose.lean:232`, proved, no sorry; Rust lowered via Charon/Aeneas; ten clauses in `lean/Spec.lean:255`. Correction (e2e session, 2026-11-27): `msm_solver solve` (Rust cmd_solve) has run the check on every complete plan and refused rejected ones since e7d72e9a (Sep 2026); my earlier 'tests only' reading missed it. New in 0.26.4 (e47326b9 on feat/engine/rc, unreleased): failing clause named in the error, and multi-case plans checked per case slice after the merge (checking the merged record as one problem is unsound, since one shared step stands for several cases' files). Cost ~0.4 s on a ~6.7 s engcyc_metagenomics solve; no shipped template refused. Determinism moved to P3 point 7.

### M2. Specification — agreed (outline-sections, 2026-11-26)
- Role: the surrounding infrastructure that turns a user's intent into a planning problem.
- Key message: a user gives typed data instances and targets through the API, CLI or GUI, and the planner treats each target as one more transform.
- Paragraphs (outline-paragraphs, 2026-11-27): each feature reduces to ordinary planning.
  - S1. Interfaces — agreed (paragraph-points, 2026-11-27)
    - Key message: one set of operations is exposed through three modalities (Python API, command line, GUI), so a user can take the same actions through any of them.
    1. A single operations layer defines every action, and each modality is a thin front end over it.
    2. The actions cover registering typed data, choosing contract libraries and targets, planning, deploying to a compute agent, running and monitoring, collecting results, and managing the cache.
    3. The Python API calls the operations directly; the command line (`metasmith`, or `msm`) maps each to a subcommand (e.g. `msm plan`, `msm workflow run`); the GUI exposes them as forms around saved templates.
    4. Writing new contracts is the exception: a contract is a Python file, so it is authored in Python.
    - Note: `src/metasmith/ops/` is the shared layer; CLI in `coms/cli/`, GUI (Flask + Svelte) in `gui/`. CLI can scaffold and validate contract files; not mentioned (Tony, 2026-11-27).
  - S2. Givens — agreed (paragraph-points, 2026-11-27)
    - Key message: a user's data enter as a library of typed instances, which becomes the plan's given step.
    1. A data library lists the user's files and values, each registered with a type.
    2. A type can be picked from the types the contracts require, or composed directly from properties.
    3. An instance can declare parents, so lineage among the givens is recorded before planning.
    4. The planner sees the givens as one given step with no inputs, whose ports carry the instances' types and declared lineage.
    - Note: points 1-2 reuse d3 "Data Instances"; that section's caching paragraph moves to Execution. No examples unless necessary (Tony, 2026-11-27).
  - S3. Targets — agreed (paragraph-points, 2026-11-27)
    - Key message: a target is a contract with inputs and no outputs, so it is planned like any other step and can carry lineage constraints.
    1. The user lists target types, which the planner builds into one target contract whose inputs are those types and which has no outputs.
    2. A target type can name earlier targets as parents, which become lineage constraints on the target's inputs, as in P2.
    3. Because the target is an ordinary contract, the planner needs no special case; a plan is solved once the target step's inputs are bound.
    - Note: `agents/targets.py` (`TargetBuilder`); rc builds the target model in `agents/spec.py:_target_model`.
  - S4. Parallel cases — agreed (paragraph-points, 2026-11-27)
    - Key message: parallel cases let varied inputs reach their own targets in one workflow while reusing the steps they share.
    1. Inputs often vary slightly in form, yet the user wants a common result from all of them, and some cases also need targets of their own.
    2. Each case therefore carries its own givens and targets and is solved on its own.
    3. The solved plans are merged step by step, so a step that several cases share runs once in the workflow.
    - Justify the final design; do not narrate the design history (Tony, 2026-11-27).
    - Note: sample type is syntactic sugar that generates cases (`Case.ByShape`); not mentioned (Tony: "samples are not well defined here"). Code on rc: `case_merge.py`. A case may reuse another case's route; merged plans are checked per case (P5).
  - S5. Variadic inputs — proposed (after S4; a solver-planning feature, Tony 2026-11-27)
    - Key message: a variadic input is matched to a set of member types the user names, and is expanded into ordinary inputs before the search.
    1. Some tools can take a variable number of inputs of one type, so a contract can mark one input as variadic.
    2. The user matches the variadic input to an actual set by naming, on a target, the member types that fill it, so the user can specify exactly which tools form an ensemble; each member must satisfy the variadic input's type.
    3. The planner then replaces the variadic input with one ordinary input per named member, and the search plans a route to each member like any other input.
    4. Outputs of the expanded contract carry a property naming the set, so outputs of different sets are different types and neither satisfies the other.
    - Note: rc `models/variadic.py` (`Specialize`, `SpecializeCases`); target `set:` in template spec.yml (binning_and_gpr_from_assembly: das_tool over metabat2/semibin2/comebin tables). One variadic input per contract; members distinct types; a target made only by a variadic contract must name its set.
  - (Optional branching moved to Planning P3, 2026-11-27.)

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

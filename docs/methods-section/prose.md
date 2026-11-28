# Methods prose (d3)

Prose written from the agreed points in `OUTLINE.md`, terse for replication (Tony, 2026-11-27). Written to d3 under Methods; `## ` lines are Heading 2, `**Title.**` opens a paragraph with a run-in subtitle.

## Solver

**Types.** A type is a set of properties, and a type X satisfies a type Y when X has every property of Y, S(X,Y) ≡ X ⊇ Y (Figure 1A). An abstract type has fewer properties and is satisfied by every more specific type, but not the reverse. Types are declared in namespaces, which are local YAML files, and are named as namespace::type.

**Contracts.** A contract lists the input types a tool requires and the output types it promises. A plan is a DAG of steps, each one use of a contract. A step binds each input to a port whose type satisfies it and exposes one new port per output type. Each port records its lineage, the ports its step consumed. An input can require that its port descend from the port bound to another input of the same step, not from any port of a matching type, so data from unrelated sources are never joined. Beyond its specification, a contract declares a protocol for fulfilling it, consisting of a Python procedure that runs the tool, the output file names, resource requests and a container image, itself declared as an input.

**Optional branching.** A tool whose outputs are decided only at run time is declared with alternative output groups, which makes its contract a fork. A single solve plans for one group of each fork, every other outcome is planned from the plan up to the fork, and the plans are merged so that every outcome has a route downstream. At run time each task writes only the group it produced, and the branches not taken stay empty.

**Planning.** The planner is a Monte Carlo tree search (MCTS) variant over partial plans. The root holds only the given and target steps, each edge adds one step, and a plan is solved when every input is bound. The frontier holds one entry per valid binding of a contract's inputs to existing ports. Before the search, a breadth-first search (BFS) back from the target's inputs, ignoring lineage, gives each contract its distance to the target and its number of routes to it, and drops contracts that cannot reach it. Frontier steps are ranked by a predictor upper confidence bound applied to trees (PUCT) rule, U(a) = Q(t) + c·P(a)·√(1+N)/(1+n(t)) with c = 1.5, where t is the contract of step a, Q(t) its mean reward, n(t) its number of picks, N the total picks and P(a) a prior favoring steps closer to the target and with more routes to it. The reward is the gain in satisfied target inputs, or 1 when the plan is solved. There are no rollouts, and the search stops at the first solved plan or after 256 iterations. A seeded random-number generator and a fixed iteration order make the same request return the same plan.

**Refinement.** Lineage makes the search path-dependent and PUCT is optimistic, so the first solved plan may not be the simplest. Refinement tries single-edge swaps, each rebinding one input to another existing port and rebuilding the steps downstream so that their lineage stays correct. A candidate must still meet the plan conditions listed under Verification. Valid candidates are ranked first by how few distinct ports anchor their lineage constraints, then by how close those anchors sit to the inputs that need them. PUCT selects the candidate to expand in each of 8 rounds, the best valid plan is kept, and steps no longer connected to the target are removed. In development testing, nearly all plans were already optimal before refinement.

**Verification.** Proving the heuristic search correct is hard, so we proved a witness checker correct instead, and every returned plan passes through it. The checker reads only the problem and the plan and tests ten conditions, among them that every binding satisfies its input type and lineage, every port has one producer and exists before use, the steps form a DAG and the target appears exactly once. A plan that fails is refused with the condition it broke. A Lean 4 proof shows that the checker's Rust implementation accepts exactly the plans that meet the formal specification.

## Specification

**Interfaces.** One operations layer backs a Python API, a command line (metasmith or msm) and a graphical user interface (GUI), so each action is available in all three. The operations cover registering typed data, choosing contract libraries and targets, planning, deploying to a worker (a machine that runs workflows), running, monitoring, collecting results and managing the cache. Contracts are Python files.

**Inputs.** User data enter as a data library of instances, files and values each registered with a type picked from those the contracts require or composed directly from properties. An instance can declare parents, so lineage among the givens is recorded before planning. The instances, called givens, form one given step with no inputs, whose ports carry their types and declared lineage.

**Outputs.** The target types requested by the user are built into one target contract with those types as inputs and no outputs. A target can name other targets as parents, which become lineage constraints on its inputs. The planner therefore treats the target as an ordinary step.

**Parallel cases.** A specification can hold several cases, each with its own givens and targets, so inputs of different forms can reach a common target in one workflow. Each case is solved on its own and the plans are merged step by step, so a step shared by cases runs once.

**Variadic contracts.** A contract can mark one input as variadic, accepting any number of inputs of one type. A target names the member types that fill it, each satisfying that type, which fixes the members of an ensemble. Before the search, the variadic input is replaced by one ordinary input per member. Outputs of the expanded contract carry a property naming the set, so outputs of different sets do not satisfy each other.

## Execution

**Compiling to Nextflow.** Each step compiles to one Nextflow process and each port to one channel. Each item in a channel carries a lineage index of the instances it descends from. Channels are combined only by merging, copying and grouping. A contract names one input to group by, the index, and a batch size, the number of index items per task. At compile time, each other input of a grouping step is classed by its relation to the index as an ancestor, a descendant, a sibling sharing an ancestor, or unrelated. At run time, each index item collects ancestors by the ids in its own lineage index, descendants by its id in theirs and siblings by a shared ancestor id, while unrelated inputs are passed whole. A group is released once every expected item has arrived, counted by stamps that the producing tasks attach to each output, or when the channel closes. Each process runs a bootstrap command that loads its step from the staged plan, matches the staged files to the step's inputs by lineage and calls the contract's protocol with a context of input paths, output paths and a shell. The protocol typically runs its tool in a dedicated container.

**Running workflows.** A compiled workflow is deployed to a worker home (msm_home), a path on the local filesystem or on a remote machine reached through the existing SSH configuration. Staging writes the workflow, input manifests, parameter files and a launcher script to the home. The launcher runs the Nextflow driver in a container, detached from the user's session, and a relay started outside that container lets the driver start each step's container. The launcher can also be run by hand. All Nextflow executors are available, and local and SLURM ship as presets and were tested. Each run records the plan's DAG, the Nextflow logs and lineage tables for all outputs and intermediates.

**Caching.** A data library is a directory of files with a manifest of instance types. Outputs are written in the same format with their lineage, so any output can be a given of a later run and a worker accumulates a pool of data products across runs. Metasmith therefore keeps its own cache on top of Nextflow's. Instance ids derive from the path within the library and the contents for files of at most 1 MiB, and from the absolute path and modification time for larger files and directories. Ids are re-derived when files change. Data already on the worker can instead be imported into the pool directly by path and type, receiving a fresh id without being read. A task's cache key is a BLAKE3 hash of its contract, protocol source included and resource requests excluded, and of the ids of the instances it consumed. Outputs take their ids from the key. Outputs of successful tasks are stored under the key. Each key is looked up before its task is submitted, a miss runs the step's process, and a hit runs a lightweight twin process that places the stored outputs in Nextflow's work directory, so downstream steps see an ordinary finished task. Results are thus reused whenever a contract runs on the same inputs, even in a different workflow. Editing a protocol invalidates its results and all results downstream, whereas changing compute resources does not.

## Benchmarks

**MAG comparison.** MAGs were compared within each sample and binner with skani 0.2.2 (--min-af 0). Identity was average nucleotide identity (ANI) multiplied by the smaller aligned fraction. MAGs were reciprocal partners when each was the other's best match, with ANI ≥ 95% and both aligned fractions ≥ 50%.

**Lines of code.** Counts excluded blank lines, comments and stubs. For nf-core/mag, logistics was the input and output blocks of each process (channel declarations) plus the workflow-level lines of the subworkflows reached by the benchmark configuration (routing), and procedure was the rest of each process. For Metasmith, logistics was the type declarations of each contract and procedure was the rest of its protocol.

**vOTU comparison.** vOTUs were compared with skani 0.2.2 (--small-genomes --min-af 15). A published vOTU was recovered if a reproduced vOTU matched it with ANI ≥ 95% over ≥ 85% of its length. For one-to-one pairing, identity was ANI multiplied by the published vOTU's aligned fraction, and the pairing maximizing total identity was found with the sparse Jonker-Volgenant algorithm in SciPy, which lets vOTUs stay unpaired (43, 44).

**GEM comparison.** Reproduced GEMs were built with CarveMe 1.2.2 (-g M8 --fbc2), DIAMOND 0.9.30 (--more-sensitive --top 10) and CPLEX 22.2. Each reproduced GEM was compared with the published GEM of the same bin by the Jaccard index of their BiGG reaction identifiers.

**Update ablation.** On a stratified 10% of bins (1,408), the update's components (BiGG gene reference, universal model, CarveMe 1.6.6 code, gap filling, DIAMOND, SCIP) were introduced one at a time, and each one's share of the drop in median Jaccard index was measured.

**KofamScan annotation.** KofamScan 1.3.0 (E ≤ 0.01, adaptive KO thresholds) annotated the ORFs of the same 1,408 bins. KOs were mapped to reactions through KEGG ko2reaction (release 119) and MetaNetX 4.5, and DIAMOND hits through BiGG gene to MetaNetX reaction mappings.

**Compute cost.** Core-hours were allocated cores multiplied by SLURM elapsed time, summed over every attempt, with cached steps counted as zero. Energy and CO₂ were estimated with Green Algorithms [TODO: CPU model, power per core, memory power, PUE and carbon intensity].

## Declarations

**AI-assisted development.** AI coding assistants extended Metasmith's hand-built core, wrote contracts and container definitions under architectural and methodological guidance, and helped draft this manuscript, with every code change tested and checkpointed in Git under a labeled author. The models were Anthropic's Claude Opus 4.6–5.5, Sonnet 4.6–5.5 and Fable 5–5.2.

**Data availability.** The datasets and their accessions are listed in Table [N].

| Dataset | Source | Accession or record |
|---|---|---|
| CAMI II strain madness, toy mouse gut, toy HMP, marine, plant-associated | CAMI portal | [TODO] |
| CAMI III toy human gut | CAMI portal | [TODO] |
| Pratama et al. viromes | ENA / SRA | PRJEB36505, PRJNA1236243 |
| Published vOTUs | Zenodo | 17897233 |
| metaGEM published bins and GEMs | Zenodo | 5596948, 5593111, 5593224, 5596972, 5597227, 5599412 |
| metaGEM studies (combined run) | ENA / SRA | PRJEB9718, PRJEB1786, PRJNA485196, PRJEB1787, PRJEB7626 |

**Code availability.** Metasmith is available at https://github.com/hallamlab/metasmith [TODO: Zenodo DOI] and documented at https://metasmith.readthedocs.io. Benchmark contracts and drivers are in research/ of the repository. Supplementary Table [N] lists each benchmark contract with its tool, tool version and container image.

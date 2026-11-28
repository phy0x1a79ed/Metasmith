# Methods prose (d3)

Prose written from the agreed points in `OUTLINE.md`, terse for replication (Tony, 2026-11-27). Written to d3 under Methods; `## ` lines are Heading 2, `**Title.**` opens a paragraph with a run-in subtitle.

## Solver

**Types.** A type is a set of properties, and a type X satisfies a type Y when X has every property of Y, S(X,Y) ≡ X ⊇ Y (Figure 1A). An abstract type has fewer properties and is satisfied by every more specific type, but not the reverse. Types are declared in namespaces, which are local YAML files, and are named as namespace::type.

**Contracts.** A contract lists the input types a tool requires and the output types it promises. Each use of a contract in a plan is a step, which binds each input to a port whose type satisfies it and exposes one new port per output type. Each port records its lineage, the ports its step consumed. An input can require that its port descends from the exact port bound to another input of the same step, not merely from some port of a matching type, so data from unrelated sources are never joined. Beyond its specification, a contract declares a protocol for fulfilling it, consisting of a Python procedure that runs the tool, the output file names, resource requests and a container image, itself declared as an input.

**Optional branching.** A tool whose outputs are decided only at run time is declared with alternative output groups, which makes its contract a fork. A single solve plans for one group of each fork, every other outcome is planned from the plan up to the fork, and the plans are merged so that every outcome has a route downstream. At run time each task writes only the group it produced, and the branches not taken stay empty.

**Planning.** Planning is a tree search of the Monte Carlo tree search (MCTS) family over partial plans. The root holds only the given and target steps, each edge adds one step, and a plan is solved when every input is bound. The frontier holds one entry per valid binding of a contract's inputs to existing ports. Before the search, a breadth-first search (BFS) back from the target's inputs, ignoring lineage, gives each contract its distance to the target and its number of routes to it, and drops contracts that cannot reach it. Frontier steps are ranked by a predictor upper confidence bound applied to trees (PUCT) rule, U(a) = Q(t) + c·P(a)·√(1+N)/(1+n(t)) with c = 1.5, where t is the contract of step a, Q(t) is its mean reward, n(t) is how often it was picked, N is the total number of picks and P(a) is a prior favoring steps closer to the target and with more routes to it. The reward is the gain in satisfied target inputs, or 1 when the plan is solved. No rollouts are performed, and the search stops at the first solved plan or after 256 iterations. A seeded random-number generator and a fixed iteration order make the same request return the same plan.

**Refinement.** Lineage makes the search path-dependent and PUCT is optimistic, so the first solved plan may not be the simplest. Refinement tries single-edge swaps, each rebinding one input to another existing port and rebuilding the steps downstream so that their lineage stays correct. A candidate must still meet the conditions of the witness checker, and valid candidates are ranked first by how few distinct ports anchor their lineage constraints, then by how close those anchors sit to the inputs that need them. The PUCT rule selects candidates for 8 rounds, the best valid plan is kept, and steps no longer connected to the target are removed. In development testing, most plans were already optimal before refinement.

**Verification.** Proving a heuristic search correct is hard, whereas checking a finished plan is simple, so every returned plan passes through a witness checker that is proven correct instead. The checker reads only the problem and the plan and tests ten conditions, among them that every binding satisfies its input type and lineage, every port has one producer and exists before use, the steps form a directed acyclic graph (DAG) and the target appears exactly once. A plan that fails is refused with the condition it broke. A Lean 4 proof shows that the checker's Rust implementation accepts exactly the plans that meet the formal specification.

## Specification

**Interfaces.** A single layer of operations is exposed through a Python API, a command line (metasmith, or msm) and a graphical user interface (GUI), so every action is available in each modality. The operations cover registering typed data, choosing contract libraries and targets, planning, deploying to a worker, running, monitoring, collecting results and managing the cache. Contracts themselves are Python files and are written in Python.

**Inputs.** User data enter as a data library of files and values, each registered with a type picked from those the contracts require or composed directly from properties. An instance can declare parents, so lineage among the inputs is recorded before planning. The instances, called givens, form one given step with no inputs, whose ports carry their types and declared lineage.

**Outputs.** The target types requested by the user are built into one target contract with those types as inputs and no outputs. A target can name other targets as parents, which become lineage constraints on its inputs. The target therefore needs no special handling, and a plan is solved once the target step's inputs are bound.

**Parallel cases.** A specification can hold several cases, each with its own givens and targets, so inputs of different forms reach a common result, alongside targets of their own, in one workflow. Each case is solved on its own, and the plans are merged step by step, so a step shared by several cases runs once.

**Variadic contracts.** A contract can mark one input as variadic, accepting a variable number of inputs of one type. A target names the member types that fill it, each satisfying the variadic input's type, which fixes the members of an ensemble. Before the search, the variadic input is replaced by one ordinary input per member, and each is planned like any other input. Outputs of the expanded contract carry a property naming the set, so outputs of different sets do not satisfy each other.

## Execution

**Compiling to Nextflow.** Each step compiles to one Nextflow process and each port to one channel. Each item in a channel carries a lineage index of the instances it descends from. Channels are combined only by merging, copying and grouping. A contract names one input to group by and a batch size, the number of index items per task. At compile time, each other input of a grouping step is classed by its relation to the index input as an ancestor, a descendant, a sibling sharing an ancestor, or unrelated. At run time, each index item collects ancestors by the ids in its own lineage index, descendants by its id in theirs and siblings by a shared ancestor id, while unrelated inputs are passed whole. A group is released once every expected item has arrived, counted by stamps that the producing tasks attach to each output, or when the channel closes. Each process runs a bootstrap command that loads its step from the staged plan, matches the staged files to the step's inputs by lineage and calls the contract's protocol with a context of input paths, output paths and a shell. The protocol typically runs its tool in a dedicated container.

**Running workflows.** A compiled workflow is deployed to a worker home (msm_home), a path on the local filesystem or on a remote machine reached through the existing SSH configuration. Staging writes the workflow, input manifests, parameter files and a launcher script to the home. The launcher runs the Nextflow driver in a container, detached from the user's session, and a relay started outside that container lets the driver start each step's container. Running the launcher by hand has the same effect. All Nextflow executors are available, and local and SLURM presets were tested. Each run records the plan's DAG, the Nextflow logs and lineage tables for all outputs and intermediates.

**Caching.** A data library is a directory of files with a manifest of instance types, and outputs are written in the same format with their lineage, so any output can be a given of a later run. A worker therefore accumulates a pool of data products across runs, and Metasmith keeps its own cache on top of Nextflow's. Every instance has an id. A library file of at most 1 MiB is identified by its path within the library and its contents, and a larger file or a directory by its absolute path and modification time, and ids are re-derived when files change. Data already on the worker can instead be imported into the pool directly by path and type, receiving a fresh id without being read. A task's cache key is a BLAKE3 hash of its contract, including the protocol source, and of the ids of the instances it consumed, and its outputs take their ids from that key. Outputs of successful tasks are stored under the key. Each key is looked up before its task is submitted, a miss runs the step's process, and a hit runs a lightweight twin process that places the stored outputs in Nextflow's work directory, so downstream steps see an ordinary finished task. Results are thus reused whenever a contract runs on the same inputs, even in a different workflow. Editing a protocol invalidates its results and their descendants, whereas changing compute resources does not.

## Benchmarks

**MAG comparison.** MAGs were compared within each sample and binner with skani 0.2.2 (--min-af 0). Identity was the average nucleotide identity (ANI) multiplied by the smaller of the two aligned fractions, and two MAGs were reciprocal partners when each was the other's best match with an ANI of at least 95% and both aligned fractions of at least 50%.

**Lines of code.** Lines were counted without blank lines, comments or stubs. In nf-core/mag, the input and output blocks of each process counted as channel declarations, and workflow-level lines in the subworkflows reached by our configuration counted as routing. In Metasmith, the type declarations of each contract counted as logistics and the rest of its protocol as procedure.

**vOTU comparison.** vOTUs were compared with skani 0.2.2 (--small-genomes --min-af 15). A published vOTU was recovered if a reproduced vOTU matched it at an ANI of at least 95% over at least 85% of its length. For one-to-one pairing, identity was ANI multiplied by the published vOTU's aligned fraction, and the pairing maximizing total identity was found with the sparse Jonker-Volgenant algorithm in SciPy, which lets vOTUs stay unpaired (43, 44).

**GEM comparison.** The reproduction built GEMs with CarveMe 1.2.2 (-g M8 --fbc2), DIAMOND 0.9.30 (--more-sensitive --top 10) and CPLEX 22.2. Each reproduced GEM was compared with the published GEM of the same bin by the Jaccard index of their BiGG reaction identifiers.

**Update ablation.** On a stratified 10% of bins (1,408), the components of the update were introduced one at a time, namely the BiGG gene reference, the universal model, the CarveMe 1.6.6 code, gap filling, DIAMOND and SCIP. Each component's share of the drop in median Jaccard index was then measured.

**KofamScan annotation.** On the same 1,408 bins, KofamScan 1.3.0 (E ≤ 0.01, per-KO adaptive thresholds) annotated the ORFs. KOs were mapped to reactions through KEGG ko2reaction (release 119) and MetaNetX 4.5, and DIAMOND hits were mapped from BiGG genes to MetaNetX reactions in the same way.

**Compute cost.** Core-hours were SLURM allocated time, allocated cores multiplied by elapsed time, summed over every attempt, with cached steps counted as zero. Energy and CO₂ were estimated with Green Algorithms [TODO: CPU model, power per core, memory power, PUE and carbon intensity]. Supplementary Table [N] lists each benchmark contract with its tool, tool version and container image.

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

**Code availability.** Metasmith is available at https://github.com/hallamlab/metasmith [TODO: Zenodo DOI], with documentation at https://metasmith.readthedocs.io, and the benchmark contracts and drivers are under research/ in the same repository.

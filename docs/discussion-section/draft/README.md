# Discussion draft, point form

Field-setting draft: as many topics as possible, to prune. [lit] marks a point that waits on the literature survey; [verify] marks a citation not yet checked.

## Opening: what we told the reader

- The gap: user intent vs the explicit specification today's workflow systems need; creating, changing or composing a workflow still takes developer expertise (Intro ¶4).
- What Metasmith adds: structural types with lineage as tool contracts; a solver that composes the workflow; compilation to Nextflow for execution.
- What the Results showed:
  - reproduced three published pipelines from three origins (Nextflow, scripts and methods, Snakemake), at the scale of the original studies;
  - each reproduction became a base for one-contract changes (assembler swap, CarveMe/SCIP update, KofamScan);
  - joined all three into one solved workflow, with no routing code written.

## Where the results fit in the literature

- **nf-core/mag.** MAG agreement with nf-core/mag sat inside nf-core/mag's own run-to-run variation (93.9% vs 94.5–95.5%). Binning is stochastic; place this against binner and CAMI benchmarks (Meyer 2022; Han 2025). [lit]
- **Reproduction as evidence.** WMS papers usually show worked examples; Loach 2026 finds evaluations rarely comparable or repeatable. Quantitative reproduction of published pipelines is uncommon. [lit: how often re-running published analyses fails]
- **Viromics.** 78.5% recovery from a pipeline published only as methods and scripts. Sources of loss: assembler non-determinism, caller and database versions, curation thresholds. Place against virus-caller agreement benchmarks. [lit]
- **Assembler trade-off.** MEGAHIT-only cost/yield and OPERA-MS without polishing agree with assembler benchmarks (Goussarov 2024; CAMI II). Shows that "better" depends on the question.
- **metaGEM.** The MEMOTE rise came 96% from the newer BiGG reference: GEM quality tracks the reference database, not the workflow. [lit: GEM reconstruction tool comparisons]
- **KofamScan.** More annotated ORFs but few new reactions: annotation coverage is not reaction coverage. [lit]
- **Cost.** 148,000 core-hours, ~267 per dataset; carbon by Green Algorithms (refs 76–78). Loach 2026: no reviewed evaluation measured Cost/Efficiency.
- **Development effort.** 0 vs 427 routing lines; 0.6 vs 0.8 logistics per procedure line. Loach's Usability theme names ease of development. Caveat: lines of code are a proxy.

## Comparison with existing systems

- **The table.** Rows: Nextflow/nf-core, Snakemake, CWL, WDL/Cromwell, Galaxy, Pegasus, KNIME, Taverna, Janis, BioShake, APE/Workflomics, Wings, PROPHETS/jABC, Dagster/Airflow, LLM agents (AutoBA, BioMaster, BioAgents), Metasmith. Columns: Loach's 12 themes. [lit: fill cells]
- **Additive to Nextflow.** Compiling to Nextflow inherits executors, containers, security (Apptainer, secrets), scalability and part of sustainability. Exceptions: Flexibility (no conditionals or loops) and Basic computing (adds Python and the container relay).
- **How structure is produced: a gap in the evaluation literature.** None of Loach's themes measures it. Lineage: written by hand (Nextflow, CWL, WDL) → chained by filename rules (Make, Snakemake) → synthesized from annotated tools (PROPHETS, APE, Wings) → planned by LLMs → solved from typed contracts (Metasmith).
- **Closest prior work: APE / Workflomics.** Shared idea: synthesis from tools annotated with typed inputs and outputs. APE: EDAM terms, SAT, lists candidates, does not execute. Metasmith: structural types plus lineage, per-sample logistics, compiled and run at scale. Workflomics benchmarks candidates; Metasmith leaves the choice to the expert. [verify]
- **Type systems.** Files and globs (Nextflow, Snakemake); named formats (Galaxy datatypes, CWL `format` with EDAM, Janis, WDL); phantom types (BioShake); structural plus lineage (Metasmith). Lineage expresses "made from that", which named formats cannot.
- **EDAM.** Metasmith types start from EDAM and may extend past it (non-strict). EDAM is often insufficient. [lit: EDAM coverage gaps]
- **Routing.** Nextflow's operator catalogue vs group-by and split; complex routing moves into a contract.
- **Modularity.** nf-core modules and subworkflows are reusable but still wired by hand; contracts reuse with no wiring (the combined workflow).
- **Provenance.** Nextflow `-resume` task hashes; CWLProv / RO-Crate; Metasmith identifies data by its derivation, so outputs are typed inputs for the next workflow. [lit]
- **LLM agents.** They plan flexibly but untyped, with no guarantee the plan runs or reproduces. Metasmith's contracts are a checkable target. In a world where implementation is cheap, the specification is the value (d2 fragment d).
- **Interface.** Galaxy GUI vs DSL; Metasmith's layers with lower layers open (Kiczales open implementation).

## Limitations

- **No conditionals or loops.** Conditionals: a contract that passes a channel through on a condition channel. Loops: need a new solver component, and conditionals in the type system so a loop can exit. (Tony, d2 Nov 5)
- **One step per contract.** Conceptual and resource partitioning do not converge; re-batching steps for contigs and ORFs exist only for logistics.
- **Tool choice needs domain expertise.** The solver wires; it does not rank. "Better" depends on the question (assembler evidence).
- **Shared vocabulary.** Properties beyond EDAM are local; contracts from different authors chain only on shared property names. Who governs them?
- **Solver.** Bounded PUCT search; plans not guaranteed minimal; scaling with library size not measured.
- **Evidence.** Lines of code as a proxy; no user study (SUS, time to first run); reproductions built by the developers with AI help; only local and Slurm executors tested; viromics and metaGEM reproduced in part.
- **Young project.** Sustainability, Learnability and Support not evaluated (Loach themes).

## Future directions

- **Multi-level compilation.** Separate the logical plan from the physical plan, as query optimizers and compilers lower in stages; group by resource homogeneity, size batches. [lit]
- **Control flow.** Conditional contracts; loops with convergence types.
- **Objectives for tool choice.** Attach benchmark metadata to contracts; let the user state objectives such as cost vs yield (the assembler trade-off); multi-objective solving.
- **LLMs on the specification.** LLMs write contracts or translate intent into targets; Metasmith checks and runs them. [lit]
- **Community library and vocabulary.** Shared contract library; EDAM extension proposals; bio.tools links.
- **FAIR outputs.** RO-Crate and WorkflowHub export; typed data libraries as shareable inputs. [lit]
- **Reuse across studies.** Lineage-hash caches shared between users and projects.
- **User study.** Evaluate on Loach's themes with non-computational users.

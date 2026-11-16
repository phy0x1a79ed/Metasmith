# Discussion draft, short form

Four paragraphs and the comparison table, modelled on Segler 2018 and Mölder 2021: a short Discussion, not a survey. Each paragraph is a topic sentence and its points. The full field-setting draft is `long.md`; citations with DOIs are in `lit-context.md`.

## Discussion

- **¶1 What Metasmith shows.** Workflow topology can be derived from typed tool contracts instead of written by hand.
  - Three published pipelines, from Nextflow, scripts and Snakemake, reproduced at study scale, inside the original pipeline's own rerun variation (93.9% vs 94.5–95.5%).
  - Each reproduction became a base for one-contract changes: assembler swap, CarveMe/SCIP update, KofamScan.
  - All three joined with no routing code: 33 contracts, 79 types, 556 read sets. A shared vocabulary turns n² pairwise adapters into n contracts.
- **¶2 Where it sits (Table 1).** Metasmith adds a planning layer on top of Nextflow rather than replacing it.
  - Compiling to Nextflow inherits its executors, containers and scale; the exceptions are Flexibility (no conditionals or loops) and Basic computing (Python and a container relay add a layer).
  - Snakemake chains backwards over filename patterns and Nextflow wires channels explicitly; Metasmith generalises the first to property sets and generates the second.
  - Automated composition was tried before (APE/Workflomics, PROPHETS, Wings, SADI), but none compiled to a production workflow system or ran at HPC scale.
  - Nextflow is adding static types and records (25.10/26.04); Metasmith types could compile to them.
- **¶3 Limitations.** The solver guarantees a well-typed plan, not the best one.
  - No conditionals or loops. Conditionals could be a contract that passes a channel through on a condition channel; loops need a new solver component and conditionals in the type system so a loop can exit.
  - No ranking of redundant tools: binners, virus callers and GEM builders disagree widely (Han 2025; Wu 2024; Hsieh 2024), so choosing between them needs domain expertise. Compare metrics, not tools.
  - Types are the ceiling. EDAM is often insufficient, so properties beyond it are local, and contracts from different authors chain only on shared names.
  - Evidence: lines of code are a proxy for effort, there is no user study, and the reproductions were built by the developers.
- **¶4 Future directions.** Separate what the workflow computes from how it runs.
  - Multi-level compilation: a logical plan lowered to a physical plan grouped by resource needs, as in query optimisers and Halide.
  - Bounded control flow, as in ¶3.
  - Tool ranking and cost (core-hours, CO₂) as pluggable solver objectives; the MEGAHIT-only run (−82% CPU hours, −32% vOTUs) is one point on that trade-off.
  - An LLM front end that turns intent into target types, with the solver keeping composition well-typed.

**Table 1.** Metasmith and seven workflow systems on the 12 themes of Loach, Smith & Bacon (2026). Cells are first-draft judgements.

| System | Basic computing | Functions | Security | Scalability | Sustainability | Usability | Learnability | FAIRness | Reproducibility | Cost/Efficiency | Flexibility | Support |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Metasmith** | Python + Nextflow + container relay (adds a layer) | typed contracts; solver composes DAG; group-by/split only | inherits Nextflow; relay adds surface ? | inherits Nextflow executors (HPC/cloud); 556 samples, 148k core-h | contracts are reusable units; Nextflow output is a fallback artefact | layered API/CLI/GUI; user states data + target types | write contracts, not routing; types need EDAM literacy | EDAM-grounded types; compiled Nextflow can join nf-core/WorkflowHub ecosystem | lineage-hash IDs + caching; reproduced 3 published studies | measured core-hours per dataset; logistics LOC measured | ✗ no conditionals/loops; ✓ swap/join tools freely | new; small community |
| Nextflow / nf-core [1–4] | Groovy DSL2, JVM | dataflow channels, operators, modules/subworkflows | containers; Tower/Seqera platform auth | ✓ many executors (SLURM, AWS, GCP, k8s) | ✓ nf-core templates, linting, CI | CLI; Seqera GUI launch | moderate–steep (channels, Groovy) | ✓ nf-core, WorkflowHub, RO-Crate export | ✓ containers, `-resume` task hashes | ~ resource labels; no built-in cost model | ✓ full control flow | ✓ very large community, Slack, training |
| Snakemake [6,7] | Python DSL | rules matched backwards by filename wildcards | conda/containers | ✓ cluster/cloud plugins | ✓ wrappers, catalog, linting [7] | CLI; reports | gentle for Make/Python users | ~ WorkflowHub; reports | ✓ conda pinning, provenance-based reruns | ~ benchmark directive per rule | ✓ Python; checkpoints for dynamic DAGs | ✓ large community |
| CWL (cwltool, Toil, Arvados) [9,10] | YAML/JSON standard; many engines | typed inputs/outputs (File, formats as EDAM IRIs) | engine-dependent | ✓ via Toil/Arvados | ✓ open standard, multi-vendor | verbose; usually generated | steep by hand | ✓ CWLProv, RO-Crate, EDAM format fields [11,12] | ✓ CWLProv | ? | ~ limited conditionals (v1.2), scatter | ✓ standards body |
| Galaxy [13,14,15] | web server + Python | tools wrapped in XML; GUI workflow editor; ToolShed | ✓ multi-user auth, quotas | ✓ public servers, Pulsar | ✓ ToolShed, IUC review | ✓ GUI, no code | ✓ GTN training | ✓ RO-Crate, WorkflowHub, EDAM in tool XML | ✓ history provenance | ~ server-side quotas | ~ GUI limits complex logic | ✓ very large |
| Pegasus [17,18] | Python/Java API, HTCondor | **abstract workflow mapped to executable workflow** | ✓ grid credentials | ✓ grid/HPC/cloud | ✓ long-lived (2001–) | API-driven | moderate | ~ | ✓ provenance DB | ~ planner optimises data movement | ~ | ✓ NSF-funded team |
| APE / Workflomics [25–28] | Java library; SAT solver; CWL output | **synthesises candidate workflows from bio.tools + EDAM constraints** | n/a | n/a (design-time) | ✓ eScience-funded 2022–25 | web UI (Workflomics) | low for users | ✓ bio.tools/EDAM native | runs CWL; benchmarker | Workflomics benchmarks time/memory | ~ linear sequences, bounded length | ~ research group |
| LLM agents (AutoBA, BioMaster, BioAgents, Biomni) [34–37] | Python + LLM API or local model | NL goal → plan → code → run → self-repair | ✗ executes generated code; data leaves site unless local | ~ single node typical | ✗ model drift | ✓ natural language | ✓ minimal | ✗ | ✗ non-deterministic generation | ✗ token + compute costs rarely reported | ✓ arbitrary | ~ research prototypes |

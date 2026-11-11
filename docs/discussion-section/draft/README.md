# Discussion draft, point form

Field-setting draft: as many topics as possible, to prune. Order follows the user's outline. Full citations with DOIs: `lit-context.md`. [verify] marks a claim or citation not yet checked.

## Opening: what we told the reader

- The gap: user intent vs the explicit specification workflow systems need; creating, changing or composing a workflow still takes developer expertise (Intro ¶4).
- Metasmith adds structural types with lineage as tool contracts, a solver that derives the topology, and compilation to Nextflow.
- Topology is derived, not written: answers the Intro's two models, Nextflow's explicit channels and Snakemake's explicit filenames.
- Reproduced three published pipelines from three origins (Nextflow, methods and scripts, Snakemake) at the scale of the original studies.
- Reproductions fell inside the original pipeline's own rerun variation (93.9% vs 94.5–95.5%) — the right yardstick, not bit-identity (Kim 2018).
- Each reproduction became a base for one-contract changes: assembler swap, CarveMe/SCIP update, KofamScan.
- Joined all three: 33 contracts, 79 types, no routing code, 556 read sets.
- Shared vocabulary turns n² pairwise adapters into n contracts — the same argument behind MetaNetX and EDAM.

## Limitations

- **No conditionals or loops.** Rules out re-binning, iterative assembly, retry on QC failure. Conditionals: a contract that passes a channel through on a condition channel. Loops: a new solver component, and conditionals in the type system so a loop can exit (Tony, d2 Nov 5). Contrast Nextflow control flow, Snakemake checkpoints, KNIME loops.
- **One step per contract.** Conceptual and resource partitioning do not converge; contig and ORF re-batching exist only for logistics.
- **No ranking of redundant tools.** The solver returns a valid plan, not the best one. "Better" needs domain expertise; tools disagree widely (binning: Han 2025; virus calling: Wu 2024; GEMs: Hsieh 2024).
- **Types are the ceiling.** Mis-specified or over-general types give valid but wrong plans; annotation quality is the known barrier for automated composition (Lamprecht 2021).
- **EDAM gaps.** EDAM is thin on intermediate artefacts (bins, coverage tables, solver settings) (Ison 2013; bio.tools, Ison 2016). Non-strict grounding is the pragmatic answer; properties beyond EDAM are local, so contracts from different authors chain only on shared names.
- **Structural over-matching.** Same property set, different meaning; lineage guards only partly.
- **Search.** MCTS is anytime and incomplete: no guarantee of a plan when one exists, or of minimality (Browne 2012; Rosin 2011). APE's SAT synthesis is complete up to a bound. Scaling with library size not measured.
- **Reference databases are invisible to types.** The BiGG update moved MEMOTE more than any tool change.
- **Extra layer.** Python and the container relay add install, maintenance and attack surface; every layer is a decay point (Zhao 2012).
- **Reproduction was not exact.** 94.5% of the vOTU count, 78.5% recovered; losses from undocumented parameters, versions, non-determinism (Mangul 2019).
- **Simulated data.** CAMI II/III are simulated (Sczyrba 2017; Meyer 2022).
- **Evidence.** Lines of code are a proxy for effort; no user study (Loach's Usability, Learnability); reproductions built by the developers with AI help; only local and Slurm executors tested.
- **Young project.** Sustainability and Support untested; small community next to nf-core (Langer 2025).

## Future directions

- **Multi-level compilation.** Separate the logical plan from the physical plan: query optimizers (Codd 1970; Selinger 1979; Volcano), LLVM/MLIR lowering, Halide's algorithm vs schedule. Group steps by resource homogeneity; size batches.
- **Bounded control flow.** Conditional contracts; loops as typed fixpoint contracts, or solver re-entry after a QC gate.
- **Tool ranking as a pluggable layer.** Benchmarks (CAMI, Workflomics) weight the solver's prior; expert judgement stays explicit and out of the type system.
- **Cost-aware planning.** Core-hours and CO₂ as solver objectives (Green Algorithms, Lannelongue 2021; GREENER 2023; Grealey 2022). The MEGAHIT-only trade-off (−82% CPU hours, −32% vOTUs) is one point on the Pareto front.
- **Multiverse analysis.** Cheap swaps let the solver enumerate valid plans and measure how choices move conclusions (many-analysts, Botvinik-Nezer 2020; microbiome DA methods, Nearing 2022).
- **Learned priors.** PUCT takes a trained policy, as in AlphaZero (Silver 2018) and retrosynthesis planning (Segler 2018, the closest analogy).
- **LLM front end, symbolic back end.** LLMs turn intent into target types or draft contracts from tool docs; the solver guarantees well-typed composition (AutoBA, BioMaster, Biomni).
- **Generate contracts.** Mine bio.tools/EDAM, Galaxy tool XML, nf-core meta.yml, Bioconda, BioContainers.
- **Lower to Nextflow typed records.** Nextflow 25.10/26.04 adds static types and duck-typed records; Metasmith types could compile to them.
- **More back ends.** CWL, Snakemake, WDL: one logical plan, many runners (Apache Beam, Akidau 2015).
- **Provenance export.** Lineage hashes map to Workflow Run RO-Crate (Leo 2024), CWLProv (Khan 2019), WorkflowHub (Gustafsson 2025).
- **Database version as a type property.** Makes GEM and annotation results traceable to their reference.
- **Formal guarantees.** Group-by and split form a restricted Kahn network; determinism and termination could be argued (Kahn 1974; Karp & Miller 1969; SyPet).
- **Ecosystem-scale re-analysis.** At ~267 core-hours per dataset, re-processing public metagenomes becomes a planning problem.
- **User study.** Evaluate on Loach's themes with non-computational users.

## Comparison with what is already out there

- **The table.** Rows: as many systems as possible; columns: Loach's 12 themes, plus a draft 13th, "Structure from". Cells are first-draft judgements.

| System | Basic computing | Functions | Security | Scalability | Sustainability | Usability | Learnability | FAIRness | Reproducibility | Cost/Efficiency | Flexibility | Support | Structure from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Metasmith** | Python + Nextflow + container relay (adds a layer) | typed contracts; solver composes DAG; group-by/split only | inherits Nextflow; relay adds surface ? | inherits Nextflow executors (HPC/cloud); 556 samples, 148k core-h | contracts are reusable units; Nextflow output is a fallback artefact | layered API/CLI/GUI; user states data + target types | write contracts, not routing; types need EDAM literacy | EDAM-grounded types; compiled Nextflow can join nf-core/WorkflowHub ecosystem | lineage-hash IDs + caching; reproduced 3 published studies | measured core-hours per dataset; logistics LOC measured | ✗ no conditionals/loops; ✓ swap/join tools freely | new; small community | **symbolic search (MCTS/PUCT) over typed contracts** |
| Nextflow / nf-core [1–4] | Groovy DSL2, JVM | dataflow channels, operators, modules/subworkflows | containers; Tower/Seqera platform auth | ✓ many executors (SLURM, AWS, GCP, k8s) | ✓ nf-core templates, linting, CI | CLI; Seqera GUI launch | moderate–steep (channels, Groovy) | ✓ nf-core, WorkflowHub, RO-Crate export | ✓ containers, `-resume` task hashes | ~ resource labels; no built-in cost model | ✓ full control flow | ✓ very large community, Slack, training | hand-written channel topology; static types/records from 25.10/26.04 [5] |
| Snakemake [6,7] | Python DSL | rules matched backwards by filename wildcards | conda/containers | ✓ cluster/cloud plugins | ✓ wrappers, catalog, linting [7] | CLI; reports | gentle for Make/Python users | ~ WorkflowHub; reports | ✓ conda pinning, provenance-based reruns | ~ benchmark directive per rule | ✓ Python; checkpoints for dynamic DAGs | ✓ large community | backward chaining of filename patterns (GNU Make lineage [8]) |
| CWL (cwltool, Toil, Arvados) [9,10] | YAML/JSON standard; many engines | typed inputs/outputs (File, formats as EDAM IRIs) | engine-dependent | ✓ via Toil/Arvados | ✓ open standard, multi-vendor | verbose; usually generated | steep by hand | ✓ CWLProv, RO-Crate, EDAM format fields [11,12] | ✓ CWLProv | ? | ~ limited conditionals (v1.2), scatter | ✓ standards body | hand-written, or generated by Janis/Galaxy/APE |
| WDL / Cromwell, miniwdl [unverified] | WDL language; Java engine | typed tasks/workflows, scatter | Terra/AnVIL cloud auth | ✓ cloud (GCP/Terra) | ✓ OpenWDL governance | moderate | moderate | ~ Dockstore | ✓ call caching | ~ cloud cost reports in Terra | ~ conditionals, scatter | ✓ Broad/GATK community | hand-written |
| Galaxy [13,14,15] | web server + Python | tools wrapped in XML; GUI workflow editor; ToolShed | ✓ multi-user auth, quotas | ✓ public servers, Pulsar | ✓ ToolShed, IUC review | ✓ GUI, no code | ✓ GTN training | ✓ RO-Crate, WorkflowHub, EDAM in tool XML | ✓ history provenance | ~ server-side quotas | ~ GUI limits complex logic | ✓ very large | hand-drawn in GUI; deep-learning tool recommender [16] |
| Pegasus [17,18] | Python/Java API, HTCondor | **abstract workflow mapped to executable workflow** | ✓ grid credentials | ✓ grid/HPC/cloud | ✓ long-lived (2001–) | API-driven | moderate | ~ | ✓ provenance DB | ~ planner optimises data movement | ~ | ✓ NSF-funded team | hand-written abstract DAG; *physical* plan automatic |
| KNIME [19] | Java desktop/server | node-based GUI; extensions | ✓ server edition | ~ server/cloud executors | ✓ commercial backing | ✓ GUI | ✓ | ~ | ✓ workflow files | ? | ✓ loops, switches | ✓ commercial + forum | hand-drawn in GUI |
| Taverna [20,21,22] | Java; web services (SOAP/REST) | service composition, myExperiment | ~ | grid-era | ✗ retired (Apache attic); workflow decay [22] | GUI workbench | moderate | ~ myExperiment | ✗ service decay | ? | ~ | ✗ inactive | hand-drawn; BioCatalogue lookup |
| Kepler [23] | Java, Ptolemy II actors | actor-oriented; directors set semantics (KPN, SDF) | ~ | ~ | ~ low activity | GUI | moderate | ~ | ✓ provenance module | ? | ✓ via directors | ~ | hand-drawn; semantic types proposed |
| Janis [unverified, BOSC 2019] | Python | typed tools; transpiles to CWL/WDL | via target | via target | ~ alpha status | Python API | moderate | via CWL | via target | ? | ~ | ~ small | hand-written with type checking at build time |
| BioShake [24] | Haskell EDSL | type-level checking of pipeline stages | via Shake | ~ cluster | ~ research code | ✗ Haskell | ✗ steep | ? | ✓ | ? | ✓ Haskell | ✗ | hand-written; **compiler rejects mis-typed compositions** |
| APE / Workflomics [25–28] | Java library; SAT solver; CWL output | **synthesises candidate workflows from bio.tools + EDAM constraints** | n/a | n/a (design-time) | ✓ eScience-funded 2022–25 | web UI (Workflomics) | low for users | ✓ bio.tools/EDAM native | runs CWL; benchmarker | Workflomics benchmarks time/memory | ~ linear sequences, bounded length | ~ research group | **SAT/temporal-logic synthesis**, user ranks candidates |
| Wings [29] | Java, OWL/semantic web | semantic constraints propagate through templates | ~ | via Pegasus | ✗ low activity | web GUI | moderate | ✓ semantic metadata | ✓ | ? | ~ template-based | ✗ | **template specialisation by semantic reasoning** |
| PROPHETS / jABC [30,31] | Java, jABC | loose programming; type taxonomies; SLTL synthesis | n/a | ✗ | ✗ archived | graphical | moderate | ~ | ? | ? | ✓ | ✗ | **synthesis fills loosely specified gaps** |
| SADI / SHARE [32] | semantic web services (OWL) | SPARQL query resolved by service discovery | web | web | ✗ low activity | query-driven | ✗ OWL | ✓ RDF-native | ~ | ? | ~ | ✗ | **automatic service chaining from a query** |
| Dagster / Airflow / Flyte / Prefect [unverified] | Python | Airflow: task DAGs; Dagster: software-defined assets; Flyte: typed tasks | ✓ enterprise auth | ✓ k8s/cloud | ✓ commercial | ✓ web UI | moderate | ✗ not science-oriented | ~ Flyte caching by typed inputs | ~ cloud cost tooling | ✓ full Python | ✓ industry | hand-written (Dagster: asset dependency graph) |
| Toil [10] | Python | CWL/WDL runner, Python API | ✓ | ✓ cloud autoscaling | ✓ UCSC | ~ | moderate | via CWL | ✓ | ✓ reported cost per sample on cloud | ✓ | ✓ | hand-written |
| Guix/Nix + GWL [33] | Scheme / Nix lang | package hash = hash of build inputs | ✓ reproducible builds | ~ | ✓ | ✗ | ✗ steep | ~ | ✓✓ bit-for-bit environments | ? | ✓ | ~ | hand-written; **content-addressed lineage as in Metasmith** |
| LLM agents (AutoBA, BioMaster, BioAgents, Biomni) [34–37] | Python + LLM API or local model | NL goal → plan → code → run → self-repair | ✗ executes generated code; data leaves site unless local | ~ single node typical | ✗ model drift | ✓ natural language | ✓ minimal | ✗ | ✗ non-deterministic generation | ✗ token + compute costs rarely reported | ✓ arbitrary | ~ research prototypes | **neural generation from natural language** |
| LLM → Galaxy/Nextflow generation [38] | as target WMS | LLM writes nf-core-style DSL2 or Galaxy workflows | as target | as target | ? | ✓ | ✓ | as target | ✗ variable across models | ? | ✓ | ✗ | **neural generation, judged against nf-core/GTN baselines** |

- **A gap in the evaluation literature.** No Loach theme measures how structure is produced, and Cost/Efficiency is empty for nearly every row (Loach 2026).
- **Additive to Nextflow.** Compiling to Nextflow inherits executors, containers, security, scalability. Exceptions: Flexibility, Basic computing.
- **Nextflow is converging on structural types.** 25.10 static types; 26.04 typed workflows and duck-typed records guaranteeing "a minimum set of requirements" (Seqera docs). Must be addressed; supports the additive framing.
- **Coordination lineage (Intro ¶1).** CSP, actors, Kahn networks, pipes fix topology by hand; Metasmith derives it from types.
- **Rule-based vs dataflow.** Generalises Snakemake's backward chaining from filename patterns to property sets; generates Nextflow's explicit topology instead of writing it.
- **Automated composition: closest prior art.**
  - APE/Workflomics: SAT synthesis over EDAM-annotated bio.tools; candidate linear workflows, CWL output, proteomics demonstrations; no peer-reviewed Workflomics paper.
  - Metasmith differs: DAGs with group-by/split, lineage, MCTS, compiled and run at HPC scale.
  - PROPHETS/jABC, Wings, SADI tried the same and are inactive; none compiled to a production WMS.
  - Lamprecht 2021 names the barriers: annotation, ranking, execution. Metasmith answers execution; ranking stays with the expert.
  - Roots in AI planning for service composition (McIlraith 2001). Galaxy's tool recommender is statistical, not type-guaranteed (Kumar 2021).
- **Type systems.** BioShake checks but does not synthesise; CWL formats are nominal and shallow; Janis and Flyte type tasks. In PL terms, Metasmith is component-based synthesis over a typed library (Synquid; SyPet).
- **Abstract vs executable.** Pegasus automates the physical half (abstract → executable workflow); Metasmith automates the logical half.
- **Content-addressed caching.** Nix/Guix, Nextflow `-resume`, VisTrails, DataLad. Metasmith hashes data lineage, not task scripts, so results are shared across workflows.
- **LLM agents.** Close the intent gap from the other side: flexible, but no determinism, type guarantees or audit trail (BioCoder; LLM → Nextflow generation varies by model, Alam & Roy 2025). Tool-augmented LLMs beat free generation (GeneGPT): a neurosymbolic split. When implementation is cheap, the specification is the value (d2 fragment d).
- **Modularity.** nf-core modules are reused, but wiring stays per pipeline — 427 routing lines in nf-core/mag. Same for Snakemake wrappers, Galaxy ToolShed.
- **FAIR.** Makes the I operational between tools, not only between metadata records (Wilkinson 2016, 2025; Goble 2020).
- **Decay.** Taverna decayed with its remote services; Metasmith pins containers through Nextflow, but contracts can still decay with tool versions.

## Where the results fit in the literature

- **Reproduction rates.** Re-running published work fails often: 2 of 18 microarray analyses (Ioannidis 2009 [verify counts]); 879 of 27,271 biomedical notebooks gave identical results (Samuel & Mietchen 2024); most Dataverse R scripts failed (Trisovic 2022); tools fail to install (Mangul 2019); repeatability in CS (Collberg 2016). Frame ours as reproduction by re-derivation, not re-execution.
- **nf-core/mag.** Deviation inside the pipeline's own stochasticity, small next to between-tool spreads in CAMI (Sczyrba 2017; Meyer 2022) and real-data binning benchmarks (Han 2025: refiners such as DAS Tool raise HQ recovery).
- **Viromics.** Virus callers agree poorly: TPR 0–97% across 9 tools (Wu 2024); tool and parameter choice bias results (Ho 2023); combining tools does not reliably help (mSystems 2024). A union of four callers amplifies small upstream differences — why 94.5% of the count coexists with 78.5% identity recovery.
- **Assembly cost vs yield.** MEGAHIT-only trade-off fits CAMI and assembler benchmarks (Goussarov 2024). OPERA-MS without polishing: polishing matters for long-read contigs [verify].
- **GEMs.** The database dominates: CarveMe, gapseq and KBase differ on the same MAGs mainly by database (Hsieh 2024); uncertainty across annotation, database, gap-filling, solver (Bernstein 2021); tools differ substantially (Mendoza 2019). The 96% BiGG attribution echoes this.
- **KofamScan.** Annotation-to-reaction mapping, not annotation, is the bottleneck. MEMOTE scores consistency, not biological accuracy.
- **Cost.** 148,000 core-hours, ~267 per dataset; carbon by Green Algorithms. No reviewed evaluation measured Cost/Efficiency (Loach 2026), so reporting it is a contribution.
- **Logistics code.** No prior study found that measures logistics vs procedure code in workflows [verify]: possibly a new metric.
- **Scale.** Compare with large catalogues: AGORA2 (7,302 reconstructions), UHGG [verify].

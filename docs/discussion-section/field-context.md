# The workflow field: approaches, principles and the problems they solved

Background for Discussion ¶2 and the Introduction. [verify] marks a claim from memory that needs checking against the source before it enters the manuscript. Citations with DOIs, where already checked, are in `draft/lit-context.md`.

## One lens for every system

Every workflow system answers three questions:

- **Structure:** how is the graph of steps described?
- **Execution:** where and how do the steps run?
- **Trust:** how can someone rerun the analysis or check it later?

Each generation solved one of these and left the other two roughly as they were. Metasmith's claim is about structure: the graph comes from types, not from a person writing it.

## Roots (Intro ¶1): two ways to describe structure

- **Goal-driven rules.** Make (Feldman 1979) works backwards: name the file you want, and Make finds rules that produce it from files you already have. Snakemake descends from this.
- **Dataflow.** Kahn process networks (1974), CSP (Hoare 1978), actors (Hewitt 1973) and Unix pipes connect processes by channels. Data flows forward, and a step fires when its inputs arrive. Nextflow descends from this.

Metasmith takes from both. It is goal-driven like Make, but it matches on types instead of filenames. Its output is a dataflow graph, compiled to Nextflow.

## Grid and e-Science, about 2000–2012 (Intro ¶2)

**Problem:** data and compute were spread across institutions. Scientists needed to coordinate remote resources without becoming systems programmers.

- **Taverna** (myGrid, UK e-Science; Oinn et al. 2004)
  - **Approach:** a desktop GUI for chaining remote web services.
  - **Philosophy:** the biologist composes services and writes no code.
  - **Where it broke:** services rarely agreed on data formats, so users wrote "shim" adapter steps. This is the n² adapter problem, already visible in 2005.
  - **Workflow decay:** Zhao et al. (2012) found that most Taverna workflows on myExperiment no longer ran, largely because the remote services had disappeared [verify the percentages]. Taverna was retired to the Apache attic.
- **Kepler** (Ludäscher et al. 2006)
  - **Approach:** built on Ptolemy II. Components are actors, and a separate "director" sets how they run together (Kahn network, synchronous dataflow and so on).
  - **Principle:** separate what the components do from the rules that compose them.
  - **Users:** mainly ecology and environmental science.
- **Pegasus** (Deelman et al., ISI, 2001 onwards; the 2015 paper is the one cited)
  - **Approach:** the user writes an abstract workflow, saying what to compute with no machines named. Pegasus plans it into an executable workflow on HTCondor DAGMan. Along the way it stages data, groups small jobs together, skips products that already exist and cleans up.
  - **Users:** LIGO, Montage (astronomy) and CyberShake (earthquakes).
  - **Why it matters:** it is the closest earlier "compiler", from an abstract plan to a concrete one. But Pegasus automates the physical half (where and how it runs), and a person still writes the graph. Metasmith automates the logical half and hands the physical half to Nextflow.
  - **AI planning:** early Pegasus work used AI planning to generate LIGO workflows (Blythe, Gil, Deelman et al. 2003) [verify]. That makes it a direct ancestor of Metasmith's solver.
- **Galaxy** (Giardine 2005; Goecks et al. 2010, *Genome Biology*)
  - **Problem:** biologists without command-line skills.
  - **Principles** (the 2010 paper's title): accessible, reproducible, transparent.
  - **Approach:** web servers that host tools wrapped in XML, each with named datatypes. The workflow editor only lets you connect compatible datatypes. That is a type check, but it never builds the graph for you.
  - **Status:** still large and active (usegalaxy.org and usegalaxy.eu, the ToolShed).

## The reproducibility turn, about 2012–2020 (Intro ¶2–3)

**Problem:** results could not be reproduced, often because the software environment differed. The answer was to pin the environment and keep the run on your own cluster.

- **Snakemake** (Köster & Rahmann 2012; Mölder et al. 2021)
  - **Approach:** Make's model in Python. Rules use filename wildcards, and the graph is inferred from the target you request.
  - **Principles:** Mölder's paper frames them as sustainability: readability, modularity, portability, scalability, reproducibility, transparency and adaptability.
  - **Limit:** rules chain only through filename patterns, so rules from different authors connect only if they agree on naming. This is the weakness the Intro names.
- **Nextflow** (Di Tommaso et al. 2017). The paper is a short *Nature Biotechnology* piece that argues one measurable claim: the same pipelines gave different numbers on different platforms, and running them through Nextflow with containers made the numbers agree [verify the specific demonstration]. So it reads like an advertisement for containers. Nextflow's real principles live in its design and documentation:
  1. **Dataflow concurrency.** Processes talk through asynchronous channels and fire when their data arrives, so parallelism comes for free. This is the Kahn process network lineage.
  2. **Portable execution.** Pipeline logic is kept separate from the executor (local, SGE, SLURM, AWS Batch, Kubernetes) and from the container. The same script runs anywhere.
  3. **Resume.** Each task is hashed, so a rerun skips work already done.
  4. **Pragmatism.** Each process body is a shell script in any language, and Nextflow imposes no data model. This is why the topology is hand-written: channels carry untyped tuples and files, and what the data means lives in the developer's head. The nf-core convention of passing `[meta, file]` tuples is a manual, untyped version of Metasmith's typed lineage.
  5. **Community.** DSL2 (2020) added modules, and nf-core (Ewels et al. 2020) turned Nextflow into a curated library of pipelines. That social layer is a big reason it won.

  One fair summary: Nextflow is a portable dataflow execution engine plus a community library, not a theory of how to compose tools. Since 2025 it has been adding static types and records, which moves it toward Metasmith's ground.
- **CWL** (2016 onwards; Crusoe et al. 2022)
  - **Problem:** lock-in to one engine.
  - **Approach:** a vendor-neutral standard for describing tools and workflows. Inputs and outputs are typed, and file formats are EDAM terms. Many engines run it (cwltool, Toil, Arvados). It is verbose and is usually generated by tools rather than written by hand.
  - **WDL:** the Broad Institute's equivalent, built for GATK and Terra.
- **Infrastructure around them:** Docker (2013), Bioconda (2018) and BioContainers made pinning an environment cheap. FAIR (Wilkinson 2016) and FAIR for workflows (Goble 2020) followed.

## Automated composition: the lineage the Intro skips

The history Metasmith continues most directly. Reviewers will ask about it.

- **AI planning for web services:** McIlraith & Son (2002), OWL-S.
- **BioMoby** (Wilkinson & Links 2002) and **SADI** (Wilkinson et al. 2011): services annotated with an ontology of data types, so a query could be answered by discovering and chaining services. BioMoby is the closest precedent for typed bioinformatics interoperability.
- **PROPHETS/jABC** (Steffen, Margaria, Lamprecht, about 2009–2014): "loose programming". You sketch the workflow, and synthesis fills the gaps from type taxonomies and temporal-logic constraints.
- **Wings** (Gil et al.): workflow templates with semantic constraints that generate Pegasus workflows.
- **APE and Workflomics** (Kasalica & Lamprecht 2020 onwards): SAT-based synthesis over bio.tools tools annotated with EDAM. It outputs candidate workflows as CWL.
- **Why none took off.** Lamprecht et al. (2021, *F1000Research*) name three barriers: annotation quality, ranking the candidates, and actually running them. These systems worked at design time over remote or annotated services, and none compiled to a production engine or ran at scale.
- **Where Metasmith differs:** contracts you own and run in containers; real graphs with group-by and split, not only linear chains; lineage; compiling to Nextflow at HPC scale. Ranking is still open, and is left to the domain expert.

## Search-based planning outside workflows

- **AlphaGo and AlphaZero** (Silver et al. 2016, 2018): Monte Carlo tree search guided by neural networks; AlphaZero's PUCT selection rule is the one Metasmith's solver uses.
- **Segler, Preuss & Waller 2018** (*Nature*): the same search plans chemical syntheses, chaining reaction rules backwards from a target molecule to purchasable precursors. The closest analogy to Metasmith: tools are rules, and a workflow is a route from available data to a requested product.

## Now: LLM agents

AutoBA, BioMaster and Biomni attack the gap between intent and specification from the other side. They are flexible, but they give no determinism, no type guarantees and no audit trail.

## What this means for the paper

- **Intro:** it jumps from Taverna to Nextflow and Snakemake. It lacks the automated-composition lineage (BioMoby/SADI, PROPHETS, Wings, APE) and Galaxy.
- **Discussion ¶2** can rest on the structure / execution / trust lens. Nextflow and the reproducibility generation solved execution and trust. The automated-composition lineage tried to solve structure but never reached execution. Metasmith joins the two.

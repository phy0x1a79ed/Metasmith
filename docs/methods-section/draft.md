# Methods — draft for d2

Draft prose for the d2 Methods, rebuilt from the code and the benchmark records. `[TODO]` marks a fact no file records. `[CHECK]` marks a place where the records and the d2 Results disagree; each is listed at the end with its source.

## Type system

**Types.** A type is a set of properties, and a type X satisfies a type Y when X carries every property of Y, S(X,Y) ⇔ X ⊇ Y (Figure 1A). Properties are drawn from the EDAM ontology (version 1.25), extended with terms of our own where EDAM is insufficient. Types are declared in YAML libraries, where a type may extend an earlier type by taking the union of its properties. A type has no identity beyond its properties, so two libraries that declare the same property set declare the same type.

**Lineage.** An input of a contract may declare that it must descend from another of the same contract's inputs. The constraint is checked against the data actually bound to that other input: a candidate satisfies it only if the bound instance is among the candidate's transitive ancestors. Because each instance's ancestry is folded into its signature, lineage is part of an instance's identity, and two instances of the same type with different histories are never interchangeable.

**Grouping and splitting.** Each contract names one input as its group-by index. Every value arriving on the index stream defines one input set. Values on the other inputs are related to the index by lineage: an ancestor of the index value is copied into its input set, and descendants of the index value are gathered into it. Each input set yields one execution. Each execution may emit any number of instances of its declared outputs, and each instance is pushed downstream as its own value, so outputs split implicitly (Figure 1C, D). A batch size folds several whole input sets into one job without splitting any of them. Any routing beyond this is written as a contract of its own that takes an enclosing group and re-emits the desired sets.

**Cases.** A specification may hold several cases, each with its own given and target types, such as short-read and long-read samples within one study. Each case is solved as its own timeline, and timelines are merged wherever one timeline's steps can stand in for another's without leaving any consumer or target unsatisfied. A sample type can also split a library into one plan per sample, each restricted to that sample's lineage.

## Solver

**Search.** The solver turns a specification into a DAG of steps by searching over partial plans. A state is a partial DAG that starts with only the given and target steps, and it is solved when no requirement is left unmet. Expanding a state applies one contract with an explicit mapping of which existing outputs satisfy each of its inputs. A mapping is valid only where both the type and the lineage constraints hold, and each valid mapping is a distinct child state.

**Selection.** States are chosen for expansion with a PUCT rule, Q + c·p·√(1+N)/(1+n) with c = 1.5. The prior p is a softmax (temperature 0.5) over two normalised scores: the number of requirements a step would satisfy, and a breadth-first estimate of its distance to the targets. A step whose product has the same type as one of its own inputs is penalised in the prior, because such a step can re-enable itself indefinitely. Statistics are kept per contract rather than per state, because a state is expanded only once. Q is the decayed mean (0.985) of the progress each expansion made, and contracts not yet tried start at 1.5. No rollouts are performed. Steps that cannot contribute to any target are pruned before the search starts.

**Refinement.** The first solution is not guaranteed to be the smallest, because lineage makes the search path dependent. A refiner therefore tries single-edge swaps of each step's input bindings, rebuilds downstream lineage, and drops any step left disconnected from the targets. The search is limited to 256 iterations and the refiner to 8.

**Determinism and checking.** The solver is written in Rust and seeded (default 42), so the same specification always yields the same plan. Every plan is checked by an independent verifier before it is returned. The verifier tests ten conditions, including type conformance, a unique producer for every instance, provenance, schedulability and target coverage, and is specified in Lean (src/solver_witness).

## Data instances and caching

User inputs are imported by declaring a type for each file, chosen from the types required by the library's contracts or composed from properties. A user input is identified by its path and modification time. Every other instance is identified by its lineage. Each execution is cached under a key built from the contract (including the full source of its script), the lineage signature, and the identities of the consumed instances. A result is therefore reused whenever the same contract runs on the same inputs, even inside a different workflow. Editing a contract's script invalidates its results and those of its descendants. `[CHECK: the claim that changing compute resources does not invalidate the cache has no code reference.]`

## Compilation and execution

**Transforms.** A transform pairs a contract with a Python script. The script receives a context object with the paths of its inputs, the paths its outputs must take, and helpers to run shell commands and containers. Most transforms call one external tool and only pass paths through.

**Compilation.** Each step of a plan compiles to one Nextflow process. A Groovy plugin carries each value as a tuple with its index and lineage hashes, and it performs the grouping described above at run time, flushing each input set as soon as it is complete. The plan is also drawn as a DAG, coloured by module.

**Execution.** An agent is a home directory, local or reachable over SSH, where workflows are staged and run. Staging writes the workflow, input manifests, parameters and a bootstrap script. Running the bootstrap script launches Nextflow (26.04.1) inside the Metasmith container (quay.io/hallamlab/metasmith), detached from the user's session. Each tool runs in its own container (Docker or Apptainer), started through a relay outside the main container. All Nextflow executors are available. Local and SLURM presets are provided and tested.

**Outputs.** Each run records its DAG, Nextflow logs and trace, and lineage tables covering the provenance of every intermediate and output. Outputs are returned as a typed data instance library, the same format as inputs, so a run's outputs can be the next run's inputs.

## Interface

Metasmith exposes the same operations in three layers: a Python API, a command-line interface (`metasmith`, or `msm`), and a graphical interface (a Flask backend with a Svelte front end). Each layer is built on the one below, and the user can drop down to the external tools at any point.

## Contract authoring

`[TODO: how the benchmark contracts were written — from the published workflow files and methods, with AI assistance, checked against tool outputs. This also answers Rokaiya's comment "how were these written? script?".]` Figure 2 used `[TODO: the toy library and data for the assembly examples.]`

## Benchmarks

All benchmarks ran on the Digital Research Alliance of Canada's Fir cluster with the SLURM executor and Apptainer 1.3.5. MAG quality was assessed with CheckM2 1.1.0, using only completeness and contamination: high quality (HQ) is completeness > 90% and contamination < 5%, and medium quality (MQ) is completeness ≥ 50% and contamination < 10%, excluding HQ (41, 42). CPU hours are SLURM allocated time (allocated cores × elapsed time), joined to Nextflow tasks through the trace.

**nf-core/mag.** nf-core/mag 5.5.0 was run with Nextflow 25.04.6 on 249 CAMI samples. The 208 short-read samples come from CAMI II strain madness (100), toy mouse gut (49), toy HMP airways/skin/urogenital (29), toy HMP gastrointestinal/oral (20) and marine (10). The 41 long-read samples come from CAMI II plant-associated Nanopore (21) and the CAMI III toy human gut long reads (20). Long reads were used wherever CAMI provides a simulated Nanopore set. Assembly used MEGAHIT for short reads and Flye 2.9.5 (`--nano-raw --meta`) for long reads, with SPAdes disabled. Binning used MetaBAT2 2.17, SemiBin2 and COMEBin 1.0.4, refined by DAS Tool 1.1.7 (score threshold 0.5). Long-read mapping identity was lowered to 80% so that MetaBAT2's depth step would not reject long-read contigs. GTDB-Tk, Prokka and QUAST were skipped. For the reproduction, each tool call was written as a contract with the same version and parameters, and the solver composed the plan.

**MAG comparison.** MAGs were compared within each sample and binner with skani 0.2.2 (`--min-af 0`). Identity is ANI multiplied by the smaller of the two aligned fractions, and two MAGs are reciprocal partners when each is the other's best match with ANI ≥ 95% and both aligned fractions ≥ 50%. `[CHECK: the Results say a sparse Jonker-Volgenant pairing; the MAG comparison code uses reciprocal best partners.]` To measure run-to-run variation, binning in nf-core/mag was rerun twice on a stratified 10% of samples (21 short-read, 4 long-read), reusing the original assemblies and changing the MetaBAT2 and SemiBin2 seeds.

**Lines of code.** Lines were counted without blank lines, comments or stub sections. For nf-core/mag, the input and output blocks of each process count as channel declarations, and the remaining process lines count as procedure. Workflow-level lines in the subworkflows reached by our configuration count as routing, classified by rule into channel operators, channel factories, join-key functions and reporting. For Metasmith, the contract statements of each transform count as types, and the rest of its script counts as procedure. Fourteen transforms were counted, excluding the evaluation-only transforms.

**Viromics.** Reads were taken from BioProjects PRJEB36505 (2019, 31 paired runs after removing one duplicate) and PRJNA1236243 (2022, 34 paired NovaSeq runs and 6 MinION runs). MinION runs were paired with Illumina runs from the same well and size fraction, giving 17 hybrid pairs. Following Pratama et al., the steps were:
- Reads were trimmed with bbduk 39.49 (`ktrim=r qtrim=rl trimq=20 minlen=50 k=23 mink=11 hdist=1`).
- Each short-read run was assembled with metaSPAdes 3.15.5 (`-k 21,33,55,77`) and with MEGAHIT 1.2.9, and each hybrid pair with metaSPAdes in Nanopore mode.
- Viral contigs were called with VIBRANT 1.2.1 (`-virome`), geNomad 1.11.0, VirSorter2 2.2.4 (dsDNAphage and ssDNA, score ≥ 0.5, ≥ 5 kb) and DeepVirFinder (score ≥ 0.9, p ≤ 0.05).
- Calls were pooled and curated with CheckV 1.0.3, keeping contigs with at least one viral gene, with no viral or host genes, or with at least 75% unknown genes. Proviruses entered as their CheckV-trimmed regions.
- Sequences were clustered with MMseqs2 (`easy-cluster --min-seq-id 0.95 -c 0.8`).
- Representatives under 5 kb were removed, as were representatives over 100 kb carrying genomic-island marker genes.

The deviations from the published methods were newer tool versions, unpinned CheckV and geNomad databases, the omission of the manual spot checks, and stopping at vOTUs. The published set of 257,252 vOTUs was taken from Zenodo record 17897233.

**vOTU comparison.** vOTUs were compared with skani 0.2.2 (`--small-genomes --min-af 15`). A published vOTU is recovered if a reproduced vOTU matches it at ANI ≥ 95% over ≥ 85% of its length. For one-to-one pairing, identity is ANI multiplied by the published vOTU's aligned fraction. The pairing maximises total identity with the sparse Jonker-Volgenant algorithm in SciPy, which allows vOTUs to stay unpaired (44, 45).

**Assembler swaps.** In the MEGAHIT-only variant, the metaSPAdes lane was removed from the short-read samples. In the hybrid variant, each hybrid pair was assembled with MEGAHIT and then scaffolded with OPERA-MS 0.9.0 (`--no-ref-clustering --no-polishing`). CPU hours are per-sample means of each assembler's tasks. `[CHECK: the indel rate (400–650 per 100 kb) was measured with metaQUAST on simulated CAMI pairs, not on the Pratama samples.]`

**metaGEM.** The reproduction started from metaGEM's published protein sequences for 14,105 bins, taken from the per-study Zenodo records (5596948, 5593111, 5593224, 5596972, 5597227, 5599412). 14,087 of these bins have a published GEM. GEMs were built with CarveMe 1.2.2 (`-g M8 --fbc2`, metaGEM's M8 medium) using DIAMOND 0.9.30 (`--more-sensitive --top 10`) and CPLEX 22.2, and scored with MEMOTE 0.9.13. The updated lane used CarveMe 1.6.6, DIAMOND 2.1.13 and SCIP 9.2.4 on the same medium, scored with MEMOTE 0.17.0. GEMs were compared by the Jaccard index of their BiGG reaction identifiers, per bin against the published GEM.

**Ablation.** On a stratified 10% of bins (1,408), components of the update were introduced one at a time: the BiGG gene reference, the universal model, the CarveMe 1.6.6 code, gap filling, DIAMOND and SCIP. The share of the identity drop due to each step was measured from the median Jaccard index (Supplementary Table 2).

**KofamScan.** On the same 1,408 bins, KofamScan 1.3.0 (E ≤ 0.01, with per-KO adaptive thresholds) annotated the ORFs, and KOs were mapped to reactions through KEGG ko2reaction (release 119) and MetaNetX 4.5. DIAMOND hits were mapped from BiGG genes to MetaNetX reactions in the same way, to compare reaction coverage (Supplementary Table 3).

**Combined workflow.** The combined specification pooled the targets of the three reproductions. The run covered 556 read sets:
- metaGEM studies (491 runs): Korem PRJEB9718 (48), Karlsson PRJEB1786 (145), Li PRJNA485196 (6), Sunagawa PRJEB1787 (246) and Bissett PRJEB7626 (46).
- Pratama et al. (65 runs), including the 17 hybrid pairs.

Reads were trimmed with bbduk 39.49 (`ktrim=r k=23 mink=11 hdist=1 tpe tbo maxns=4 trimq=0 maq=3`). Assembly used MEGAHIT 1.2.9 for short reads and MEGAHIT with OPERA-MS for hybrid pairs. GEMs were built with CarveMe 1.6.6 `[CHECK solver]`. Core-hours are SLURM allocated time summed over every attempt, with cached steps counted as zero. Energy and CO₂ were estimated with Green Algorithms (76), using `[TODO: Fir CPU model, power per core, memory power, PUE, carbon intensity and grid]`.

## Statistics

Comparisons are reported as medians with distributions shown in the figures. No significance tests were performed.

## AI assisted development

(Existing d2 paragraph; add model versions.)

## Data and code availability

`[TODO]` Data: CAMI II/III from the CAMI portal; SRA/ENA accessions as listed above; published vOTUs from Zenodo 17897233; published metaGEM results from the Zenodo records above. Code: Metasmith 0.24.1 at https://github.com/hallamlab/metasmith, `[TODO: Zenodo DOI]`, with benchmark contracts and drivers under `research/`.

## Conflicts between the d2 Results and the records

| # | Results claim | What the records show | Source |
|---|---|---|---|
| 1 | MAGs paired one-to-one with sparse Jonker-Volgenant | MAG comparison code uses reciprocal best partners (ANI × min AF, ANI ≥ 95, AF ≥ 50); Jonker-Volgenant is used only for vOTUs | `research/metasmith_benchmark/results/compare_arms.py`; `results/e3/votu_lib.py` |
| 2 | nf-core control runs gave 94.5–95.5% reciprocal partners | Report gives 94.1–95.6% on the short-arm DAS Tool | `findings/E1_E2_REPRODUCTION.md` |
| 3 | 93.9% reciprocal partners (all samples) | Short-arm DAS Tool only; long arm is 90.8% and is not mentioned | same |
| 4 | 400–650 indels per 100 kb in OPERA-MS gap fills | Measured on simulated CAMI pairs (E5 pilot), not on the Pratama samples | `findings/E5_HYBRID_PILOT.md:112` |
| 5 | 21.4% vs 76.6% "matched" | These are matched/total; the recovery shares on the same basis as the headline 78.5% are 36.0% and 74.9% | `E3K` in `reproduction.html`; `E3_ABLATION.md` |
| 6 | metaGEM reproduction "started from MAGs" | Started from published protein bins (`genes.faa`) | `findings/E4_REPRODUCTION.md:10` |
| 7 | 812 → 1,153 annotated ORFs of 1,880 | Neither count appears in any file; 42.8% of 1,880 is 804 | `supplementary/kofam_lift/kofam_lift.tsv` |
| 8 | Combined run used CarveMe 1.6.6 on SCIP | No record names the solver for the combined run; one note says CPLEX | `R1_WAVES.md:281` |
| 9 | bbduk "per a published JGI method" | Combined run used the standard bbduk transform; nothing records the JGI attribution | `src/metasmith_libraries/transforms/assembly/bbduk.py:42` |
| 10 | 16.89 core-years | Cannot be reproduced exactly; the cost tables give 17.19–17.48 | `drivers/e5_cost.py`, `E5_RUN.md` (bench-E5) |
| 11 | 0.9 MWh / 20 kg; 3.3 MWh / 75 kg | No file records the Green Algorithms inputs or the metaSPAdes counterfactual | — |
| 12 | 33 contracts, 79 types | Numbers appear only unlabelled in `methods_panels/excal/*.json` | — |

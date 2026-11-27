# Aggregate — survey (2026-11-27)

The `survey` topic's findings. Sources: a git sweep of the bare repo, and three read-only surveys (E2E install loop, tools run across projects, Galaxy / geoquery / ML). Journal ids and commits are cited inline; rows marked *inferred* were matched by name, not read.

## What release already holds

- 375 standard transforms in 15 groups: functionalAnnotation 114, logistics 87, metagenomics 42, aspire 34, kbase 21, transcriptomics 19, viromics 15, metabolicModelling 11, assembly 11, fabfos 6, isolate 5, pangenome 4, geoquery 3, responseSurface 1, amplicon 1.
- 17 templates, 115 environments, 27 type files.
- 587 transforms in research roots: research/kbase/library 398 (stubs), research/metasmith_benchmark/library 126, research/metasmith/transforms 38, research/rnaseq/library 8 (isolate RNA-seq, real, ran for the collaborator's B2 delivery), research/hybrid_solve/library 5.
- 96 transform/template/type/env files on unmerged branches (`unmerged_files.tsv`): fabfos/lipidomics-abundance 18, engine/manuscript 16, engine/manuscript-figures 16, lab/kalen-dofher 10, engine/bench-E3 7, engine/psortm 6, geospatial_query/dev 5, others ≤3.

## Tools run but not on release

| Tool | Domain | Evidence |
|---|---|---|
| TreeSAPP (create, assign, retrain) | phylogenetic placement | cyanoverse/treesapp-refpkgs and treesapp-amber sbatch; most-run tool with no transform |
| IQ-TREE, FastTree, trimAl (standalone) | phylogenetics | only nested inside gtdbtk / TreeSAPP (c40296f7) |
| featureCounts | transcriptomics | nosco-phycocyanin fir/count*.sbatch; in research/rnaseq but not std |
| CoverM, MetaPop, CCTyper | viromics / coverage | listed absent in ee434adf |
| MMseqs2 cluster / search / all-vs-all (general) | protein clustering | cyanoverse protein-clusters, treesapp-amber; std has only viromics-specific mmseqs |
| MaxBin2, CONCOCT, VAMB | binning | *inferred* gap beside the six shipped binners |
| ProtT5, Ankh, CLIPZyme | protein embeddings | *inferred*; esmfold, esm_c, saprot, foldseek_3di are shipped |
| 9 CRAGE stubs (plasmid features, cargo BLAST, reference diff, methylation pileup, …) | isolate / plasmid | 78831d96; research stubs awaiting sign-off |
| MetaboScape differential, membrane classifier, acyl-chain ID | lipidomics | scadc lipidomics (886e6438, b2cfac86); notebook-grade |
| Embedding VAEs v3–v8, contig-binning VAE, NMF/LDA archetypes | ML / statistics | cyanoverse sbatch (msg:87, journal:14) |

Domains with no std group: phylogenetics, mass-spec omics (lipidomics/metabolomics/proteomics), ML training, bibliometrics, statistical modelling. Protein structure/embedding ships inside functionalAnnotation.

## The first aggregation attempt (engine/install-loop → engine/rc)

- Original goal — `metagenomics_from_paired_reads` on nibi — never executed a step. The effort moved to engcyc templates on sockeye + fir (run 4, round 9, active, 0.26.2+5f7fae4).
- 26 distinct problems, about two-thirds fixed. Largest single cost: a GUI delete confirm left metabuli in the plan and setup fetched 205 GB (fixed 553838c3).
- Why slow: each round is a 3–8 h cluster setup that surfaces one or two blockers; per-fix release-candidate rebuilds; harness/watcher faults; scope drift (metagenomics → engcyc + feature work); release contention.
- Lessons: size downloads before setup; make the harness right first; iterate at the cheapest layer (solve → plan-only → setup → tiny run); pin one target set; batch fixes per candidate.

## Coverage beyond the lab

- **Galaxy.** ToolShed 8,276 repositories (verified); usegalaxy.eu ≈3,300 tools. galaxy_codex already joins EDAM, bio.tools, bioconda and formats per tool. IWC: 121 curated, tested workflows (workflowhub.eu/projects/33) — the ground-truth set KBase narratives were. Wrappers carry real commands and bioconda requirements, so generated transforms can execute, unlike the KBase stubs. Datatypes are file formats, coarser than KBase's semantic types; EDAM data terms are the bridge.
- **Geoquery.** 0.26.x: 3 transforms, 75 source adapters, verified on 3 AOIs (dfb210a3, 0bb87ac4). Its shape — entity table → fan-out per source → aggregate — is domain-neutral; generalise `aoi_table` to an entity table with a pluggable adapter registry. Open: Tomer deliverable, DVC push, osm / postgis-loader / packaging topics.
- **ML.** No training transforms on release. Model case: the cyanoverse embedding VAE sweep (msg:87). Minimal shape: split → train → evaluate → collect sweep, with the split as its own artifact and a sweep as a fan-out over configs.

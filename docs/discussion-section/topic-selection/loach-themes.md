# Loach et al. 2026 themes

Loach M, Smith K, Bacon W. A scoping review of approaches to evaluating workflow management systems for bioinformatics users. Brief Bioinform. 2026;27(4):bbag396. https://doi.org/10.1093/bib/bbag396 (PMC13384634). Not yet in Zotero or the d2 EndNote library.

The user: "I think we can use these criteria to ground comparisons". The user's pasted brief is not the paper. The definitions below come from the paper's Table 2 (read from the OUP page, 2026-11-11; the Discussion was not read).

| Theme | Paper's definition | Paper's example criteria |
|---|---|---|
| Basic computing | Requirements for installing and running the WMS | environments it runs in |
| Functions | Availability of the tools, data types, or workflow functions needed | supported data types, tools, modularity, progress checking |
| Security | Measures that keep data, analyses and workflows private, or allow secure sharing | passwords, standards compliance |
| Scalability | Size of data or computational demand the WMS can handle | large data, compute demand |
| Sustainability | How likely the WMS is to stay available in a usable state | years active, maintenance, community, citations |
| Usability | The experience of using the WMS | installation, GUI vs text, ease of development, error handling, accessibility |
| Learnability | How easily users learn the WMS or analyses through it | learning materials, documentation |
| FAIRness | Whether data, workflows and the WMS follow FAIR | search, open access, CWL export, sharing |
| Reproducibility | Whether analyses can be repeated, replicated or reproduced | provenance, transparency |
| Cost/Efficiency | Cost of an analysis in time or money | run cost, time to result; **no reviewed paper assessed it** |
| Flexibility | Control to customise and express any workflow pattern | expressiveness, loops, nested workflows, conditionals |
| Support | Guidance through the analysis | support services, suggested parameter values; one paper only |

Paper's stated gaps: no clear way to choose a WMS; criteria often undefined (10 papers) and scoring unexplained (9); 16 of 71 named WMSs already defunct; Cost/Efficiency never evaluated. Most-evaluated WMSs: Galaxy, Nextflow, Snakemake, Taverna, bpipe, KNIME, Pegasus, Cromwell, Anduril, UGENE.

## Metasmith evidence per theme

| Theme | What the Results or code already show | Gap |
|---|---|---|
| Basic computing | Python + Nextflow in a container; conda package | not measured |
| Functions | typed data with EDAM grounding; contracts as modules | — |
| Security | container relay; not evaluated | — |
| Scalability | 249 CAMI samples; 556 read sets; 148k core-hours on SLURM | no scaling curve |
| Sustainability | conda releases; compiles to Nextflow, so execution outlives Metasmith | young project |
| Usability | GUI / API / CLI layers; ease of development: 427 routing lines vs 0, logistics 0.8 vs 0.6 | no user study |
| Learnability | readthedocs | no learning materials evaluated |
| FAIRness | EDAM types; outputs are typed data libraries; Nextflow output | no RO-Crate / WorkflowHub |
| Reproducibility | three reproductions match; lineage tables; containers | — |
| Cost/Efficiency | 267 core-hours per dataset; assembler swap saved 82% CPU hours; Green Algorithms refs in d2 | fills a theme no reviewed paper measured |
| Flexibility | contract swaps; combined workflow; data-dependent MAG counts | no loops or conditionals |
| Support | — | Support's "suggested values" is near the tool-choice boundary |

Corrections to the earlier map: lines of code fit Usability ("ease of development"), not Learnability; loops and conditionals sit under Flexibility, not Functions.

No theme measures how a workflow's structure is produced. Metasmith's core contribution sits under Flexibility and Usability at best; that absence is itself a Discussion point.

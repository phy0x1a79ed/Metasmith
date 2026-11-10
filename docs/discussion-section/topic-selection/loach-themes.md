# Loach et al. themes (user-supplied, 2026-11-10)

The user: "I think we can use these criteria to ground comparisons". They pasted an itemized brief of 12 themes attributed to Loach et al. (2026): Basic Computing, Functions, Security, Scalability, Cost/Efficiency, Sustainability, Usability, Learnability, Reproducibility, FAIRness, Flexibility, Support.

Source status: not in the d2 bibliography; the papers search (kb) was down; the web turned up only Loach M & Bacon W (2025), "What do biologists want? Finding the best Workflow Management System (WMS) for users", F1000Research poster 14-722 (not peer reviewed), which reports 7 themes: sustainability, reproducibility, FAIRness, usability, learnability, flexibility, support. The 12-theme list and the per-theme "how to measure" items need checking against the 2026 paper before citing.

## Metasmith evidence per theme

| Theme | What the Results or code already show | Gap |
|---|---|---|
| Basic computing | Python + Nextflow in a container; conda package | not measured |
| Functions | group-by and split; lineage-hash caching | no conditionals or loops |
| Security | container relay; not evaluated | — |
| Scalability | 249 CAMI samples; 556 read sets; 148k core-hours on SLURM | no scaling curve |
| Cost / efficiency | 267 core-hours per dataset; assembler swap saved 82% CPU hours; Green Algorithms refs in d2 bibliography | — |
| Sustainability (software) | releases on conda | young project |
| Usability | GUI / API / CLI layers | no user study |
| Learnability | lines of logistics 0.8 vs 0.6; 427 routing lines vs 0 — the theme names LOC as a measure | no SUS or time-to-first-run |
| Reproducibility | three reproductions match; lineage tables; containers | — |
| FAIRness | EDAM-grounded types; outputs are typed data libraries | no RO-Crate / WorkflowHub |
| Flexibility | adding a tool = writing a contract; contract swaps; combined workflow; data-dependent MAG counts | — |
| Support | readthedocs | young community |

No theme measures how the workflow's structure is produced. Metasmith's core contribution sits under Flexibility and Learnability at best; that absence is itself a point for the Discussion.

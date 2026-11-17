# discussion-section: decisions

One section per closed topic, in the order the topics closed.

## topic-selection (2026-11-09 → 2026-11-15)

**Question.** Which topics does the Discussion cover, and what structure holds them?

**User's words.**
> the main thing I can think of is a qualitative table comparing metasmtith against existing workflow managers, including nextflow.

> 1 paragraph per row is too narrow. I think we will chunk and find other groupings. we may want to also talk about other things.

> I guess thsi doesnt need to be a really long section, just a few paragraphs should be enough. we can point out a few main points and show the table of features

**Decided design.**
- The Discussion is short: a few paragraphs, each making one main point, plus the comparison table. Models: Segler 2018 (a short Discussion) and Mölder 2021 (Snakemake; one closing paragraph). The Nov 9 outline of four sections does not survive as headings.
- The table is central. Prose does not walk it column by column.
- Columns: Loach, Smith & Bacon 2026's 12 themes (doi:10.1093/bib/bbag396; not yet in Zotero). Where Metasmith was not evaluated, the cell says what it inherits from Nextflow. The draft 13th column, "Structure from", was dropped; how each system produces structure goes in prose.
- Rows: first filled with as many systems as possible, then cut on 2026-11-15 to 8: Metasmith, Nextflow/nf-core, Snakemake, CWL, Galaxy, Pegasus, APE/Workflomics, LLM agents.
- Framing: Metasmith is additive to Nextflow, "not strictly". Exceptions stated openly: Flexibility (no conditionals or loops) and Basic computing (Python and the container relay add a layer).
- Arguments to carry: EDAM grounds the types but "is often insufficient" (`ontology: EDAM 1.25, strict: false`, src/metasmith/models/libraries/types.py:52); judging which tool is "better" needs domain expertise, so compare metrics, not tools.

**Where it landed.** `draft/long.md` (field-setting draft, cut at d1150271; uploaded into live d2 on 2026-11-15, Nov 5 original kept as `Metasmith_d2_backup_2026-11-05.docx`). `draft/README.md` at 907c853b is an unreviewed proposal for the short form.

## intro-composition (2026-11-17)

**Question.** How does the Intro build from the field to Metasmith, around the new automated-composition paragraph?

**Tony's words.** "P5 and existing 4 should switch places. then we can shape our P5 as what was tried and what went wrong? existing p3 should then focus more on the why"; "we say that the idea has had sucess in similar problems rather than say we have direct inspiration"; "LLM agents i think go at the end for P4 since they act as both solver and interface"; "make all necessary changes and mark additions in blue, deletions in red".

**Design.**
- P2 ends on Loach et al. 2026's twelve themes, setting up Table 1.
- P3 (Nextflow, Snakemake) ends on the shared cause: the knowledge of which tools fit together lives with the author, not the system.
- P4 is the composition paragraph, moved above the user gap: semantic web services, BioMoby/SADI, Pegasus/Wings, PROPHETS/APE, the Lamprecht 2021 barriers, then LLM agents as solver and interface with no guarantees. The tree-search sentences are struck from it.
- P5 is the user gap, with Galaxy added.
- P6 opens with Metasmith, then typed contracts, the backward solver, and tree search's success on similar problems (Silver 2016/2018, Segler 2018).
- Taverna stays light in the Intro; its value is Discussion ¶4 (compute-market).
- EndNote fields kept in place; new citations are plain author-year text for Tony to insert.

**Landed.** d2 via Word COM over the Windows tether, 2026-11-17.

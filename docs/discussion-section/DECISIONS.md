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

## idea-partition (2026-11-19)

**Question.** How do the Intro and Discussion share their themes without repeating each other?

**Tony's words.** "I think the 4 parts work well for the intro, and we need to somehow map that to our groups for discussion"; "in the discussion, we can refer to the intro and say that loach further splits this?"

**Design.**
- Shared spine of four layers: ecosystem, execution, planning, intent. The four paradigms (service, dataflow, build, declarative) supply each layer's lineage; Metasmith sits in the declarative class.
- Each idea is placed in a grid: layer × (what exists, why it falls short, what Metasmith does, what is open). Cross-cutting threads: types, the accessibility–expressiveness trade-off, the paradigms, Loach, the precedents (tree search, query planning).
- The Intro walks up the stack: P2 ecosystem history, then execution, planning, intent (the open user gap), then Metasmith.
- The Discussion walks the same layers with verdicts, in bookend order: D2a concerns and Loach, then execution, planning, intent, ecosystem last, leading to D3 limitations and D4 future (compute market).
- Loach's 12 themes are mapped by us onto the layers (not "Loach splits"): execution = Basic computing, Scalability, Security, Cost/Efficiency, Reproducibility; planning = Functions, Flexibility; intent = Usability, Learnability, Support; ecosystem = FAIRness, Sustainability. Loach omits automated composition, which spans planning and intent.
- Table 1 columns grouped under the four layers.

**Landed.** `draft/outline.md` (cbe26eaa) as the working outline; the row-by-row re-split into Intro and Discussion comes later.

## d1-recap (2026-11-22)

**Question.** What does D1, the Discussion's opening paragraph, claim and cover?

**Tony's words.** He rewrote D1 himself around his seed; "lets try dropping P 3".

**Design.**
- Thesis: radical interoperability between bioinformatics tools, shown with Metasmith.
- Order: problem (hand-written topology, needs fluency in both tools and workflow system), claim (topology can be derived), mechanism (one typed contract per tool, symbolic solver, compiles to Nextflow), why it is radical (one contract per tool rather than routing to every tool), evidence (pipelines from well-developed to bespoke), composition (pipelines stitched together in response to user intent).
- The three named cases stay in the Results, not D1. The bridge to the literature is ¶2's opening.

**Landed.** Live d2 via Word COM over the Windows tether, 2026-11-22. Additions in blue.

## three-claims (2026-11-24)

**Question:** what organises the Discussion, now that a scorecard across Loach's 12 themes reads as hollow and unfocused?

**User's words:** "we just aren't staying true to them and just kind of pulling in an arbitrary 12 themed metric." "Let's do claim 2, then 1, then 3." Claim 1: "routing is a chore." Claim 3: "we attempt to be accessible full stack."

**Design:** after the D1 opening, three claims, each split into paragraphs with one core message apiece. Limitations and future directions sit inside the claim they qualify (Loach P4), and there is no standalone limitations paragraph.
- Claim 2, *Format isn't meaning*: 2a prior vocabularies; 2b why they didn't stick; 2c Metasmith's types; 2d limits.
- Claim 1, *Routing is a chore*: 1a manual; 1b earlier automation (FlowCraft, APE, Pegasus clause); 1c backward planning; 1d agents as planner clients; 1e smarter routing (conditionals, loops, ranking, domain knowledge: limits and future).
- Claim 3, *Accessible across the full stack*: 3a one-end-only systems; 3b one user owns the stack (scale is one clause, inherited from Nextflow); 3c limits; 3d compute market.
- Loach's 12 themes stay as background only. Table 1 is deferred; it supersedes table-criteria/levels and twelve-coverage.

**Primary messages as approved (2026-11-23 17:20, recovered from the transcript 2026-11-25):**
- D1: radical interoperability, one contract per tool.
- Claim 2, *Format isn't meaning*:
  - 2a. Earlier vocabularies described formats, so tools that agreed on format could still disagree on meaning.
  - 2b. A vocabulary survives only if annotating pays off.
  - 2c. Metasmith makes annotation pay off, because the planner consumes it.
  - 2d. Plans are only as right as their types.
- Claim 1, *Routing is a chore*:
  - 1a. Most systems hand the route to the user.
  - 1b. Earlier automation checked routes or sketched them, but the user still did the routing.
  - 1c. Metasmith routes backwards from the destination, so a plan is correct by construction.
  - 1d. Agents write routes without guarantees; as clients of the planner they supply judgement while the planner guarantees validity.
  - 1e. Smarter routing means bringing domain knowledge into the planner (limits: no conditionals or loops, one step per contract, no ranking, MCTS incomplete; future: Nov 5 conditionals/loops fix, ranking from domain logic).
- Claim 3, *Accessible across the full stack*:
  - 3a. Existing systems are accessible at only one end of the stack.
  - 3b. In Metasmith, one end user can own the whole stack.
  - 3c. Accessibility is designed, not yet measured.
  - 3d. Next, move from your own compute to shared compute on the same types.

Later changes (claims-reframe, 2026-11-24/25), not yet a closed decision: claim 2 became "Describing tools as typed contracts enables radical interoperability" (2a types of use; 2b shared ontology and local namespaces); claim 1 "A symbolic solver is sufficient to automate routing between typed contracts" gained an incentives paragraph and lost 1c (proposed restore pending); claim 3 became "Typed contracts are accessible at different levels of expertise" (3a hierarchical interfaces, 3b own the stack via Nextflow, 3c decentralised compute market).

**Landed:** outline artifact v7, https://claude.ai/artifact/1md7uDcwDF6aauFp7QGb1d

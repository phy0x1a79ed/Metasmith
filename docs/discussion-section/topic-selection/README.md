# Topic selection

## What the user said

> we need to first decide on topics, then how to order and connect them. follow mandate of "place results in context with literature"

> the main thing I can think of is a qualitative table comparing metasmtith against existing workflow managers, including nextflow.

> then I think a lot of the current points would fit inot this structure

## Proposal (awaiting confirmation)

The comparison table is the spine. Each column is a design dimension. The Discussion walks the columns, one paragraph each: where existing systems sit, where Metasmith sits, which Result is the evidence, and what Metasmith cannot yet do there.

Candidate columns:

1. **Where topology comes from** — written by hand (Nextflow, CWL, WDL); chained from filename rules (Make, Snakemake); synthesized from annotated tools (APE, Wings); solved from typed contracts (Metasmith). Evidence: the combined workflow needed no routing code.
2. **What a data type is** — files and globs; nominal formats (Galaxy datatypes, CWL/EDAM formats, Janis); structural properties with lineage (Metasmith).
3. **Routing and logistics** — channel operators; wildcards and checkpoints; group-by and split. Evidence: 427 routing lines vs 0; logistics ratio 0.8 vs 0.6.
4. **Control flow** — conditionals and loops. Metasmith has neither (limitation 2).
5. **Composition and modification** — modules and subworkflows vs swapping a contract. Evidence: assembler swap, CarveMe/SCIP update, combined workflow.
6. **Execution, provenance and caching** — own engine vs compiling to Nextflow; task-hash resume vs lineage hash.
7. **Tool choice and domain knowledge** — no system ranks tools; LLM agents now try. Metasmith wires but does not choose (limitation 3); the d2 AI-agent paragraph fits here.
8. **Interface layers** — GUI (Galaxy, KNIME), DSL, API.

Where the earlier candidate limitations land: 1 (two partitionings) → column 3 or 6; 2 → column 4; 3 → column 7; 4 (shared vocabulary) → column 2; 6 (evidence limits) → a results-in-context paragraph outside the table.

## Decisions

- **The table is central, but the prose is not one paragraph per column.** The user: "1 paragraph per row is too narrow. I think we will chunk and find other groupings. we may want to also talk about other things." The table's dimensions are raw material; the ordering topic groups them into larger chunks, and the Discussion may also cover topics outside the table.
- **Argument: EDAM grounds the types but is often insufficient.** The user: "metasmith types were supposed to be based on EDAM, but EDAM is often insufficient". Code check: every type library declares `ontology: EDAM 1.25, strict: false` (`src/metasmith/models/libraries/types.py:52`), so properties may extend past EDAM. This answers the shared-vocabulary limitation and is the main contrast with APE, which is bound to EDAM terms.
- **Argument: judging which tool is "better" needs domain expertise.** The user: "we can argue that domain expertise is required to answer which tool is "better"". The tool-choice limitation becomes a deliberate scope boundary: Metasmith wires, the expert chooses. The assembler swap (cheaper, fewer vOTUs) and OPERA-MS (similar count, poor match) are the evidence that "better" depends on the question.
- **Pick the comparison metrics before the rows.** The user: "lets not talk about which tools, but rather the metrics to compare by". The rows question waits until the columns are settled.
- **Ground the comparison metrics in Loach et al.** The user: "I think we can use these criteria to ground comparisons". Themes and the evidence map are in `loach-themes.md`. Citation still to verify.
- **All 12 Loach themes are table columns (option A).** The user: "A -> not evaluated, but leveraged nextflow". Where Metasmith was not evaluated on a theme, its cell says what it inherits by compiling to Nextflow — likely Basic computing (executors, containers), Security (Apptainer, Nextflow secrets), Scalability (Slurm and cloud executors) and part of Sustainability (the execution layer outlives Metasmith). Learnability and Support do not inherit; those cells say not evaluated.

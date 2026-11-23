# discussion-section: stack

Goal: draft the Discussion of the Metasmith manuscript, placing the results in context with the literature. Decisions: `docs/discussion-section/DECISIONS.md`.

## Current

**discussion-d2-d4**: tune D2–D4 on the four-layer spine (idea-partition), one paragraph at a time, starting with ¶2's opening (D2a).
- Prose for D2a–e and D3 is in live d2, drafts in blue. Outline artifact: https://claude.ai/artifact/1md7uDcwDF6aauFp7QGb1d
- Open: ¶2 promises an assessment against all twelve themes, so check each theme is covered; delete the ¶ scaffold headings?; ¶4 future directions still bullets.

## Waiting on the user

- intro-composition: review the Intro edits in d2. All 22 missing refs are now in EndNote (ids 84–105; Loach 93, AutoBA 103, Biomni 104, BixBench 105). Confirm Kiran 2023 (100), Wu 2024 (101), Hsieh 2024 (102). Then convert author-year text to EndNote fields via temporary citations {Author, Year #id} + Update Citations.

## Preferences

- (2026-11-09) Mandate: "place results in context with literature".
- (2026-11-09) Point form and concise while drafting; fill the field, then cut.
- (2026-11-15) Talk before acting: discuss a change before making it.
- (2026-11-22) Agree changes as itemized points in chat, then edit the doc directly. Keep Tony's sentences; add in blue only; no red. Don't echo doc text back in chat.

## Stack

- **table-criteria** (2026-11-22): "first establish what goes in the table: what are we comparing against … and what is the metrics". Table 1 is now `d2/tables/Table_1_wms_themes.csv` (removed from the doc, caption kept). Score cells by levels and criteria from the reviews Loach covers (Wratten 2021 and Kiran 2023 define levels); 17 of 22 full texts are in `data/loach-reviews/` (index.tsv; Kiran 2023 has the level definitions). Untracked: mizar has no dvc CLI, so they are not yet pinned. Wratten 2021, Larsonneur, Marinova and Welivita are paywalled; Tony to drop PDFs in `d2/_fetch`.
  - **systems-list**: which systems are columns. Current: Metasmith, Nextflow/nf-core, Snakemake, CWL, Galaxy, Pegasus, APE/Workflomics, LLM agents.
  - **levels**: one criterion and level definition per theme, drawn from the reviews.
  - **twelve-coverage**: ¶2 promises all twelve themes; Security and Scalability are not yet discussed (proposed: one sentence in ¶3).
- **flowcraft** (2026-11-23): "we must mention them in discussion. shelf for later". FlowCraft (https://github.com/assemblerflow/flowcraft; no paper found, last commit May 2020): ordered component strings with fork syntax, one free-form input/output type string per component checked between neighbours, compiles to Nextflow with per-component containers. Closest prior work on execution; the user still writes the topology. Proposed: one sentence in the planning paragraph (¶4) next to Snakemake and Pegasus; also a sustainability example. No Table 1 column.
- **main-points** (2026-11-15): "we can point out a few main points and show the table of features". Proposal in `draft/README.md` (907c853b), not yet reviewed.
  - **opening-vs-conclusion**: d2 has its own Conclusion; does the "what Metasmith shows" recap stay in the Discussion?
  - **limitations**: which limitations make the cut. Candidates in `draft/long.md` § Limitations; d2 fragments (one step per contract; no conditionals or loops, Tony's Nov 5 paragraph; no tool ranking; the AI-agents paragraph) enter here.
  - **results-in-literature**: whether any of the literature comparison of results (viromics and GEM tool disagreement, cost reporting) survives.
- **discussion-p1..p4** (2026-11-16): go over each Discussion section for what to say and in what order. Four sections are set up in d2 in point form (2026-11-15). ¶1 echoes the Intro's problem and solution, then bridges to ¶2.
  - **compute-market** (2026-11-16): "the vector towards a decentralized compute market that builds on the metasmith types would solve all of taverna's problems". Source: thesis/ch5 `docs/thesis-ch5/draft.md` §5.4 (pull market, typed offers, trust per function, resilience, visible sustainability). Goes in ¶4.
- **table-trim** (2026-11-15): keep 8 systems × 12 themes, or shrink further for a short section.
- **prose** (2026-11-15): turn the agreed points into paragraphs in d2, blue edits.

## Workers

(none)

## Closed

- **d1-recap** (2026-11-22). D1 thesis is radical interoperability; one-contract-per-tool point added.
- **idea-partition** (2026-11-19). Four-layer spine shared by Intro and Discussion; Loach mapped onto it.
- **intro-composition** (2026-11-17). Intro P2–P6 restructured in d2.
- **topic-selection** (2026-11-15). Short Discussion: a few main points plus the comparison table.

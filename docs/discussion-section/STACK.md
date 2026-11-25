# discussion-section: stack

Goal: draft the Discussion of the Metasmith manuscript, placing the results in context with the literature. Decisions: `docs/discussion-section/DECISIONS.md`.

## Current

**claims-reframe** (2026-11-24): claims argued against the literature, Tony's seeds filled. Outline artifact v16 https://claude.ai/artifact/1md7uDcwDF6aauFp7QGb1d holds 2a, 2b, 1a–1e, 3a–3c with prose.
- Settled: claim 2 = typed contracts enable radical interoperability (old 2b dropped, seed folded into 2a; SADI precise; local-vocabulary contrast in 2b). Claim 1 = symbolic solver suffices for routing; SHARE beside FlowCraft in 1a; 1b keeps Snakemake, Wings, APE; 1e = ranking (PUCT, learned prior, market as aspiration; no Fast Downward). Claim 3 = levels of accessibility. PlanBench/Blocksworld not reported.
- Accepted and in d2 (2026-11-25), in Discussion order after Tony's ¶5: 2a (`draft/2a-types.md`), 2b (`draft/2b-ontology.md`), 1c (`draft/1c-agents.md`; lead line "too in the weeds", revisit). All old claim prose and scaffold headings removed from d2.
- Claim 3 shape settled: "Typed contracts are accessible at different levels of expertise"; 3a interfaces are hierarchical, levels parallel the intent-to-execution gap; 3b own the stack via Nextflow; 3c decentralised compute market ("some compute is too specialised to hand over": ship the product, not the factory).
- Open now: in-order pass, itemized points then prose, next 1a.
- Structure reference: DECISIONS.md § three-claims, "Primary messages as approved" plus its later-changes line. Pending: Tony to confirm the merged claim 1 order (1a manual + incentives problem; 1b earlier automation; 1c restored backward routing; 1d incentives aligned; 1e agents; 1f smarter routing).
- d2 access: capella via ssh + schtasks task `msm_word` (ssh + schtasks task `msm_word`, interactive session; save the doc after each edit).

**table-criteria** (deferred by Tony, "will come back to that one"): Table 1 under the three-claim structure (three-claims, DECISIONS.md).

Previous current, superseded by three-claims: **discussion-d2-d4**: tune D2–D4 on the four-layer spine (idea-partition), one paragraph at a time, starting with ¶2's opening (D2a).
- Prose for D2a–e and D3 is in live d2, drafts in blue. Outline artifact: https://claude.ai/artifact/1md7uDcwDF6aauFp7QGb1d
- Open: ¶2 promises an assessment against all twelve themes, so check each theme is covered; delete the ¶ scaffold headings?; ¶4 future directions still bullets.

## Structure

Three levels: claim, paragraph key message, sentence points. Read back top-down. Status per paragraph in brackets. References are assigned to one paragraph where possible.

- **D1** Tony's opening: radical interoperability through per-tool typed contracts. [in d2]
- **Claim 2. Describing tools as typed contracts enables radical interoperability.**
  - **2a. Types join tools, so they must describe how data can be used; earlier systems typed what data are.** [v2 prose accepted, in d2 2026-11-25]
    1. Chaining rule: if an output type satisfies an input type, the tools chain.
    2. Earlier systems typed what data are, with increasing richness: Galaxy format classes; KBase schemas that record properties as fields but match apps by type name (Arkin 2018); SADI classes defined by properties, closest in approach (Wilkinson 2011).
    3. Case: whether reads can go to an assembler depends on the state they have reached (platform, pairing, trimming); none of these systems uses state to decide which tool takes the data.
    4. Metasmith: types are property sets that capture that state; one contract makes a tool chainable with every tool whose types it satisfies, so types are what make tools interoperable.
    - Refs: Galaxy, KBase (Arkin 2018), SADI (Wilkinson 2011). Not here: EDAM, BioMoby, CWL, WDL/Nextflow/Snakemake types.
  - **2b. Interoperability hinges on a shared vocabulary, which needs a community standard; a new tool should start local and let standards emerge.** [v2 prose accepted, in d2 2026-11-25]
    1. A shared vocabulary needs a standard adopted by a community; Metasmith has neither.
    2. Current standards fall short. Too coarse: EDAM, used by bio.tools and CWL, describes what data are and which operations act on them, not state, so plans run but are wrong (Lamprecht 2021). Too fragile: BioMoby's central registry decayed with its servers (Zhao 2012).
    3. A new standard would be counterproductive: many standards amount to none.
    4. Hence local namespaces, expanded and joined as adopted; local, so they cannot decay with a remote server.
    5. Narrow claim: types expressive enough for the Results; offer a principle (a type draws exactly the distinctions that decide which tools can take the data); standards left to use.
    - Refs: EDAM, bio.tools, CWL (one clause), Lamprecht 2021, BioMoby (BioMoby Consortium 2008), Zhao 2012.
- **Claim 1. A symbolic solver is sufficient to automate routing between typed contracts.**
  - **1a. Routing, and making modules reusable, is the developer's job; incentives do not align; the result is reimplementation.** [points in progress]
  - **1b. Earlier automation matched names or stopped at candidates.** [outline]
  - **1c? Metasmith routes backwards from the destination, so a plan is correct by construction.** [restore proposed, Tony to decide]
  - **1c. Agents can propose pipelines, but only typed contracts make their joins checkable.** [prose accepted; lead line to simplify; in d2 out of order; pull pending Tony]
  - **1d. Automated routing aligns the individual's incentive with the community's.** [outline]
  - **1e. Choosing among valid plans needs a softer search that can rank; conditionals, loops, incompleteness.** [outline]
- **Claim 3. Typed contracts are accessible at different levels of expertise.**
  - **3a. The interfaces are hierarchical levels that parallel the gap from intent to execution; adding tools still needs expertise.** [outline]
  - **3b. Deferring execution to Nextflow gives portability and lets users own the full stack.** [outline]
  - **3c. A decentralised compute market: some compute is too specialised to hand over; ship the product, not the factory.** [outline, aspiration]

## Waiting on the user

- Tony's ¶5 ("If the goal is…") still carries my blue Loach-rubric tail; trim or keep?

- intro-composition: review the Intro edits in d2. All 22 missing refs are now in EndNote (ids 84–105; Loach 93, AutoBA 103, Biomni 104, BixBench 105). Confirm Kiran 2023 (100), Wu 2024 (101), Hsieh 2024 (102). Then convert author-year text to EndNote fields via temporary citations {Author, Year #id} + Update Citations.

## Preferences

- (2026-11-09) Mandate: "place results in context with literature".
- (2026-11-09) Point form and concise while drafting; fill the field, then cut.
- (2026-11-15) Talk before acting: discuss a change before making it.
- (2026-11-22) Agree changes as itemized points in chat, then edit the doc directly. Keep Tony's sentences; add in blue only; no red. Don't echo doc text back in chat.
- (2026-11-25) Per paragraph: tight itemized points (key message + 4-5 items), then prose in chat, then write into d2 as soon as accepted: plain paragraphs, no claim headings, D1 formatting (Normal, Arial 12), blue.

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

- **three-claims** (2026-11-24). Discussion = D1 opening + claim 2 (format isn't meaning), claim 1 (routing is a chore), claim 3 (accessible across the full stack); 14 paragraphs, one core message each; limits and future inside each claim. Supersedes twelve-coverage and the D2–D4 layer spine.

- **d1-recap** (2026-11-22). D1 thesis is radical interoperability; one-contract-per-tool point added.
- **idea-partition** (2026-11-19). Four-layer spine shared by Intro and Discussion; Loach mapped onto it.
- **intro-composition** (2026-11-17). Intro P2–P6 restructured in d2.
- **topic-selection** (2026-11-15). Short Discussion: a few main points plus the comparison table.

# discussion-section: stack

Goal: draft the Discussion of the Metasmith manuscript, placing the results in context with the literature. Decisions: `docs/discussion-section/DECISIONS.md`.

## Current

**claims-reframe** (2026-11-24): claims argued against the literature, Tony's seeds filled. Outline artifact v16 https://claude.ai/artifact/1md7uDcwDF6aauFp7QGb1d holds 2a, 2b, 1a–1e, 3a–3c with prose.
- Settled: claim 2 = typed contracts enable radical interoperability (old 2b dropped, seed folded into 2a; SADI precise; local-vocabulary contrast in 2b). Claim 1 = symbolic solver suffices for routing; SHARE beside FlowCraft in 1a; 1b keeps Snakemake, Wings, APE; 1e = ranking (PUCT, learned prior, market as aspiration; no Fast Downward). Claim 3 = levels of accessibility. PlanBench/Blocksworld not reported.
- Accepted and in d2 (2026-11-25), in Discussion order after Tony's ¶5: 2a (`draft/2a-types.md`), 2b (`draft/2b-ontology.md`), 1c (`draft/1c-agents.md`; lead line "too in the weeds", revisit). All old claim prose and scaffold headings removed from d2.
- Claim 3 shape settled: "Typed contracts are accessible at different levels of expertise"; 3a interfaces are hierarchical, levels parallel the intent-to-execution gap; 3b own the stack via Nextflow; 3c decentralised compute market ("some compute is too specialised to hand over": ship the product, not the factory).
- Open now (2026-11-25): claims 2 and 1 done as a first pass (2a, 2b, 1a, 1b, 1c in d2). Claim 3 merged to one paragraph, first pass in d2. Coherence check done (2026-11-25): coherence/blind-summary-sonnet.md, coherence/fable-suggestions.md (8 ranked suggestions; main gap: three claims read as seven, claim 1's sufficiency never stated). Citations converted 2026-11-25: all 19 Discussion cites are EndNote temporary citations ({Author, Year #id} for library refs; no #id for the 8 new ones, all unique author-year). The 8 new refs are in discussion_missing.ris (Arkin 2018, Cimatti 2003, Peot 1992, Alam 2025, Dziri 2023, Fa 2026, Kurjan 2026, Kambhampati 2024); Biomni cited as Huang 2026 #104. Waiting on Tony: import the RIS, then Update Citations and Bibliography. Coherence suggestions #1 and #2 in d2 (2026-11-25; D1 stitching sentence ends "as a demonstration of interoperability"); review vs Tony's preferences in coherence/preference-review.md. All eight coherence suggestions except #4 (1b reorder, conflicts with Tony's placement) in d2, 2026-11-25. Tony ran Update Citations; all Discussion cites render numbered. Style pass 2026-11-25: paragraphs 2a-3 rewritten in Tony's register (style/comparison.md; before.txt, after.txt; reviewed for meaning drift and corrected), in d2 with temporary citations; Tony to run Update Citations again. Open: optional 2b limit on joining namespaces (not applied: unsure it is true, since libraries already mix namespaces).
- Citations method: d2 uses EndNote ADDIN EN.CITE fields, numbered (Vancouver-terse). Discussion paragraphs 2a-3 carry plain author-year text. Library: EndNote 2025 on capella (hostname Cosmos), B:\OneDrive - UBC\Hallam Lab - Metasmith\d2\endnote\Metasmith.enl, 105 refs (ids 84-105 added 2026-11-20; Loach 93, AutoBA 103, Biomni 104, BixBench 105; Kiran 100, Wu 101, Hsieh 102 unconfirmed). Read-only query scripts: /home/tony/.claude/jobs/3ff2282e/tmp/endnote/q_all.ps1, q_new.ps1 (copy sdb.eni to %TEMP%, query table refs; never write sdb.eni). Steps: list each author-year cite in the Discussion; match to library ids; write a RIS for missing ones (Cimatti 2003, Peot & Smith 1992, likely Fa 2026, Kurjan 2026, Alam 2025, Kambhampati 2024, Han 2025, Arkin 2018, Lamprecht 2021, Vandervalk 2009 ...) and have Tony import it (File > Import, RIS filter) or open it in EndNote; replace each with a temporary citation {Author, Year #id}; then Update Citations and Bibliography (Tony clicks, or via the add-in). Transcript lines ~1574-2650 hold the earlier Intro run. Earlier note: Next: itemized main points for 1a and 1b, same shape as § Structure claim 2 (key message + 4-5 points, refs assigned once); Tony will judge from them whether the backward-routing paragraph (old 1c) returns. Tony's 1a notes: say explicitly routing is the developer's job; frameworks leave it to the developer to make modules extensible; query-based systems (SHARE) begin to define modules/components; incentive mismatch is the problem 1d resolves. Tony cut the "If the goal is…" ¶ himself (2026-11-25). Pending: BioMoby Consortium 2008 beside Zhao in 2b (unanswered).
- Structure reference: DECISIONS.md § three-claims, "Primary messages as approved" plus its later-changes line. Pending: Tony to confirm the merged claim 1 order (1a manual + incentives problem; 1b earlier automation; 1c restored backward routing; 1d incentives aligned; 1e agents; 1f smarter routing).
- d2 access: capella via ssh + schtasks task `msm_word` (ssh + schtasks task `msm_word`, interactive session; save the doc after each edit). When adding a paragraph, copy the neighbour's format (`$new.Format = $prev.Format`: justified, 1.5 lines, 36 pt first-line indent); setting Style='Normal' resets it.

**table-criteria** (deferred by Tony, "will come back to that one"): Table 1 under the three-claim structure (three-claims, DECISIONS.md).

Previous current, superseded by three-claims: **discussion-d2-d4**: tune D2–D4 on the four-layer spine (idea-partition), one paragraph at a time, starting with ¶2's opening (D2a).
- Prose for D2a–e and D3 is in live d2, drafts in blue. Outline artifact: https://claude.ai/artifact/1md7uDcwDF6aauFp7QGb1d
- Open: ¶2 promises an assessment against all twelve themes, so check each theme is covered; delete the ¶ scaffold headings?; ¶4 future directions still bullets.

## Structure

Three levels: claim, paragraph key message, sentence points. Read back top-down. Status per paragraph in brackets. References are assigned to one paragraph where possible.

- **D1** Tony's opening: radical interoperability through per-tool typed contracts. [in d2] Stitching sentence ends "as a demonstration of interoperability"; new last sentence forecasts the claims: "Below, we place these results in the context of earlier work on types, routing and accessibility." [blue, coherence #3, 2026-11-25]
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
    5. Narrow claim: we do not prescribe the vocabulary, any more than the rest of the stack, and without a standard the claim is narrower (link fixed, coherence #5): types expressive enough for the Results; offer a principle (a type draws exactly the distinctions that decide which tools can take the data); standards left to use.
    6. [in d2 2026-11-25, coherence #2] Close on claim 2: whichever vocabulary emerges, tools described as typed contracts over it drive interoperability.
    - Refs: EDAM, bio.tools, CWL (one clause), Lamprecht 2021, BioMoby (BioMoby Consortium 2008), Zhao 2012.
- **Claim 1. A symbolic solver is sufficient to automate routing between typed contracts.**
  - **1a. Routing, and making modules reusable, is the developer's job; incentives do not align; the result is reimplementation.** [first pass in d2 2026-11-25, draft/1a-routing.md]
    0. [in d2 2026-11-25, coherence #2] Opening turn: types describe the valid connections between tools, but the route from end to end must still be chosen; point 1 follows as the next sentence.
    1. Routing is currently the developer's job, and frameworks give no mechanism for reuse: a Nextflow process is a step, not a module. FlowCraft is the exception (component types checked between neighbours), leading to 2.
    2. Query-based: SADI makes each service a component described by the properties it consumes and produces, so a query can find it; a multi-step query still spells out the route (Wilkinson 2011, second use). SHARE cut.
    3. Case in terms of state only, no reads: routing means taking data through the states each tool requires, and the developer does it by hand.
    4. Tony's seed as bridge: little incentive under immediate research goals; the community's goals are longer term.
    5. Result: reimplementation, GATK over 200 implementations (Wratten 2021).
    - Transition ("automating the route would remove this cost, and earlier systems tried to") moves to open 1b.
    - Source shape: artifact v17 1a.0-1a.4 (several compactions back), with Tony's 2026-11-25 notes.
  - **1b. Planning has proved useful, but earlier planners could not reach their full potential; Metasmith removes both obstacles.** [key message extension in d2 2026-11-25, coherence #1] [first pass in d2 2026-11-25, draft/1b-planning.md; absorbs 1d seed (intro) and planner limits (conditional, strong cyclic planning)]
    1. Intro answering 1a: if the route were derived rather than written, every module would be reusable at no extra cost to its developer; that is what planning promises.
    2. Strengths, established here (decided 2026-11-25, moved from 1c.4): a join is accepted only on type fit, so plans are valid by construction (main); systematic, reproducible, auditable (APE, Kasalica 2020).
    3. Held back by types: coarse types let invalid plans through as candidates (ref back to 2a); fixed vocabularies pushed structure into human-written templates, so search became template matching (Wings, Gil 2011; ref back to 2b; Lamprecht 2021 second use).
    4. Held back by execution: no clear path from a plan to a machine-executable protocol.
    4a. [in d2 2026-11-25, coherence #1] Metasmith removes both obstacles: types carry state, so invalid joins never become candidates (back to 2a); a plan compiles to Nextflow, so it runs as written. No Result anchor: D1's stitching sentence now ends "as a demonstration of interoperability" (Tony, 2026-11-25; in d2, blue).
    4b. [recorded, already in prose] Limits: strong plans over declared output sets (Cimatti 2003); conditional (Peot 1992) and strong cyclic planning (Cimatti 2003) not yet implemented.
    5. Bridge to 1c [in d2 2026-11-25]: agents have been applied as an alternative to planners, one that can also execute, composing and running tools directly (Nextflow, bash), without the guarantees of 2.
    - Make/Snakemake cut. Backward-routing paragraph likely unneeded: 1c's close carries the positive statement.
  - **1c? Metasmith routes backwards from the destination, so a plan is correct by construction.** [not restored: 1b.2 and 1c's close carry the positive statement; Tony moved on 2026-11-25]
  - **1c. Agents can propose pipelines, but only typed contracts make their joins checkable.** [first pass in d2 2026-11-25; absorbs 1e ranking (Han, Wu, Hsieh); lead line to simplify]
    - [in d2 2026-11-25, coherence #8] Lead sentence states the message: agents can propose whole pipelines, but nothing checks the joins between their steps. FlowBench cut to two findings (edgeless graphs dropped). 1c.4 now refers back to 1b: only a check of type fit, as in the planners above, makes a join valid by construction. 1c.1-1c.3 agent evidence and 1c.5 complementarity (Kambhampati 2024) stay.
    - 1c.6 [in d2 2026-11-25, coherence #2] Close on claim 1, merged into 1c.5: a symbolic solver can generate the valid routes between typed contracts, while an agent turns a question into a target and supplies the heuristics that guide search and rank the valid plans.
  - **1d.** [dropped 2026-11-25: overlaps 2b; Tony's incentive seed moved to 1b's intro; payoff clause for 2b offered, not applied]
  - **1e.** [dropped 2026-11-25: ranking folded into 1c; limits into 1b; market to 3c; MCTS/PUCT/learned prior cut]
- **Claim 3. Typed contracts are accessible at different levels of expertise.** [one paragraph, first pass in d2 2026-11-25, draft/3-access.md]
  - **3. Typed contracts are accessible at different levels of expertise, from stating intent to supplying compute.**
    1. Tony's seed: hierarchical interface levels following intent to execution (GUI templates, notebook/API/CLI, contracts and types); a contract written once serves every level above.
    2. Galaxy and Nextflow each fix a point on flexibility vs support (Loach 2026); Metasmith lets the user choose.
    3. Tony's seed: Nextflow gives portability (executor list) and full-stack ownership; Galaxy contrast: modification and compute go through a central authority, or users stand up the full server, much harder than Nextflow (Tony's wording 2026-11-25).
    4. Limits: new tools need expertise the GUI lacks; only local and Slurm tested; no user study.
    5. Aspiration, bridged from ownership (coherence #6): because users own the stack, they could offer it to others; some compute is too specialised to hand over; decentralised compute market; product not factory; track records; paid upkeep answers registry decay (back-ref 2b).
    6. Close on the thesis (coherence #7; the Conclusion section is empty): in each case the typed contract is the common unit; it joins tools, lets a solver choose the route, and could let providers offer compute.
    - Lead (coherence #6): "Beyond routing, typed contracts are accessible at different levels of expertise, from stating intent to supplying compute."

## Waiting on the user

- Tony's ¶5 ("If the goal is…") still carries my blue Loach-rubric tail; trim or keep?

- intro-composition: review the Intro edits in d2. All 22 missing refs are now in EndNote (ids 84–105; Loach 93, AutoBA 103, Biomni 104, BixBench 105). Confirm Kiran 2023 (100), Wu 2024 (101), Hsieh 2024 (102). Then convert author-year text to EndNote fields via temporary citations {Author, Year #id} + Update Citations.

## Preferences

- (2026-11-09) Mandate: "place results in context with literature".
- (2026-11-09) Point form and concise while drafting; fill the field, then cut.
- (2026-11-15) Talk before acting: discuss a change before making it.
- (2026-11-22) Agree changes as itemized points in chat, then edit the doc directly. Keep Tony's sentences; add in blue only; no red. Don't echo doc text back in chat.
- (2026-11-24) Seed sentences need not be verbatim: "I would appreciate if you kept the original thought, but some of my prose is very informal. If you could fix, please."
- (2026-11-25) Record every decided structure and point-form draft in § Structure as it is decided, at three levels (claim, paragraph key message, sentence points), with references assigned to one paragraph where possible, so the main points can be read back top-down. Never leave a decided structure only in the chat.
- (2026-11-25) Check each claim reads coherently once its prose is done.
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

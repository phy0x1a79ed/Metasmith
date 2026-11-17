# discussion-section: stack

Goal: draft the Discussion of the Metasmith manuscript, placing the results in context with the literature. Decisions: `docs/discussion-section/DECISIONS.md`.

## Current

**intro-composition**: the Intro's flow and main points around the new automated-composition paragraph. Agreed so far (2026-11-16): swap the user-gap paragraph and the composition paragraph; P3 refocuses on why today's systems cannot adapt; P4 = what was tried and what went wrong, ending on LLM agents ("act as both solver and interface") as the transition to P5; P5 = user gap with Galaxy added; P6 = Metasmith, with tree search framed as "success in similar problems" (AlphaZero, Segler 2018), not direct inspiration. Taverna stays light in the Intro; its main value is Discussion ¶4 (compute-market).

## Waiting on the user

- intro-composition: does Loach's 12-theme framework enter at the end of Intro P2 (after FAIR, setting up Table 1), or only in the Discussion?

## Preferences

- (2026-11-09) Mandate: "place results in context with literature".
- (2026-11-09) Point form and concise while drafting; fill the field, then cut.
- (2026-11-15) Talk before acting: discuss a change before making it.

## Stack

- **intro-composition** (2026-11-16): "the current intro paragraph has a few ideas, but doesnt read with a common thread or agenda that builds on the introduction". Then rewrite P3–P6 as prose in d2.
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

- **topic-selection** (2026-11-15). Short Discussion: a few main points plus the comparison table.

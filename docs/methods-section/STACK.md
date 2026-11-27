# Methods discussion stack

Goal: write the d2 Methods with the co-writing protocol, from `OUTLINE.md`. Decisions: `docs/methods-section/DECISIONS.md`.

**On every resume or compaction:** load the `dfs-interview` skill, then read and follow the co-writing protocol at `/home/tony/agentic_workspace/projects/self-improvement/writing-skill/docs/writing-skill/protocol-draft.md`, then read `OUTLINE.md`. Any compaction followup must name all three. The protocol is a draft and may change; reread it rather than working from memory.

## Current

**paragraph-points / Planning**: Planning grouped by concept as P1 Types, P2 Contracts, P3 Planning search, P4 Refinement, P5 Verification (agreed 2026-11-27). Now itemizing points one paragraph at a time, starting with P1. Earlier note: sketch the Planning group as itemized points, one paragraph per concept (Tony, 2026-11-27: "one paragraph per concept"). Split the earlier three paragraphs (types+ports+lineage; search+selection; refinement+verification) into one per concept, e.g. types; ports; lineage (strict bound-port check, deliberate, explain why); search state and base case; frontier expansion; PUCT selection; refinement; determinism; verification. Show it in small pieces on Tony's phone. Then the other groups, one at a time. Do not draft prose yet.

Level-2 proposal for Specification and Execution (shown 2026-11-27, "mainly fine", to be revisited in smaller sections): Specification = givens; targets as contracts (lineage on target inputs); variadic inputs; optional branching and parallel cases; limits and workarounds; interfaces (last, recommended). Execution = compilation (steps → processes, ports → channels, grouping at run time); agents and presets; containers and relay; caching; outputs.

## Waiting on the user

- Planning sketch: one-paragraph-per-concept points.

## Preferences

- (2026-11-27) Tony is on his phone: short messages, conversational, small sections, one block at a time.
- (2026-11-27) Settle the overall structure and grouping before prose; don't go into the weeds.
- (2026-11-27) One paragraph per concept.
- (2026-11-27) Order of work: itemized points for each paragraph, one at a time; then a flow check across the group; then prose for the whole group at once; then check again; then into d3.
- (2026-11-27) Reuse the original d3 prose where it exists, above all the existing Methods prose ("most of that is good already"); update and fill gaps rather than rewrite.

- (2026-11-25) Results are more up to date than Methods; where they contradict, Methods changes.

## Stack

- **outline-paragraphs**: level 2, section by section: Planning (current), Specification, Execution, Contracts, Benchmarks, Declarations. M2 needs a code survey first (variadic inputs are new, on a branch; optional branching is the old mechanism).
- **paragraph-walk**: per paragraph in document order: points, prose, then into d2.
- **results-conflicts**: the 12 rows in `draft.md` where the records do not back the Results (MAG pairing method, metaGEM input, OPERA-MS indels, ORF counts, combined-run solver, core-years, Green Algorithms inputs, and others).
- **todos**: contract authoring, Figure 2 library, Green Algorithms inputs, Zenodo DOI.

## Workers

- metasmith-e2e-install-test (peer session): witness gate on every solve, branch feat/engine/witness-gate, release 0.26.4+. Will message when merged into feat/engine/rc or if a template violates the spec. P5 must not call it landed before then.

## Closed

- **terms** (2026-11-27). property → type → contract → step → port → plan → instance.
- **outline-sections** (2026-11-26). Planning, Specification, Execution, Contracts, Benchmarks; Declarations as its own top-level section.

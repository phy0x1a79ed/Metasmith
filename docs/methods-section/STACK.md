# Methods discussion stack

Goal: write the d2 Methods with the co-writing protocol, from `OUTLINE.md`. Decisions: `docs/methods-section/DECISIONS.md`.

**On every resume or compaction:** load the `dfs-interview` skill, then read and follow the co-writing protocol at `/home/tony/agentic_workspace/projects/self-improvement/writing-skill/docs/writing-skill/protocol-draft.md`, then read `OUTLINE.md`. Any compaction followup must name all three. The protocol is a draft and may change; reread it rather than working from memory.

## Current

**paragraph-points / Execution**. Planning (P1 Types, P2 Contracts, P3 Optional branching, P4 Planning search, P5 Refinement, P6 Verification) and Specification (S1 Interfaces, S2 Givens, S3 Targets, S4 Parallel cases, S5 Variadic inputs) have agreed points and pass the flow check. Execution paragraph list proposed 2026-11-27 in OUTLINE.md: E1 Contract execution (protocol in Python, own container/env), E2 Compilation (plan -> Nextflow), E3 Running the workflow (local/SLURM presets, results and lineage collected; outputs folded in), E4 Caching. Open: rename "agent" (LLM collision); proposed "compute site" (alternatives host, runner, deployment). Then itemize E1..E4 one at a time, flow check, then Contracts, Benchmarks, Declarations; prose after all sections have points, one section at a time.

Code facts for Execution live on `origin/feat/engine/rc` (this branch is behind): variadic, cases, forks and the witness gate are there. Read rc with `git show origin/feat/engine/rc:<path>`.

## Waiting on the user

- Agent rename: compute site, host, runner or deployment?
- Execution paragraph list (E1-E4): agreed set and order?

## Preferences

- (2026-11-27) Tony is on his phone: short messages, conversational, small sections, one block at a time.
- (2026-11-27) Settle the overall structure and grouping before prose; don't go into the weeds.
- (2026-11-27) One paragraph per concept.
- (2026-11-27) No examples in points unless necessary.
- (2026-11-27) Methods paragraphs open with the problem or premise, then the mechanism. Justify the final design; never narrate how it was reached.
- (2026-11-27) Order of work: itemized points for each paragraph, one at a time, section by section, with a flow check per section; prose only after all sections have points, then one section at a time; check again; then into d3.
- (2026-11-27) Reuse the original d3 prose where it exists, above all the existing Methods prose ("most of that is good already"); update and fill gaps rather than rewrite.

- (2026-11-25) Results are more up to date than Methods; where they contradict, Methods changes.

## Stack

- **outline-paragraphs**: level 2, section by section: Planning (current), Specification, Execution, Contracts, Benchmarks, Declarations. M2 needs a code survey first (variadic inputs are new, on a branch; optional branching is the old mechanism).
- **paragraph-walk**: per paragraph in document order: points, prose, then into d2.
- **results-conflicts**: the 12 rows in `draft.md` where the records do not back the Results (MAG pairing method, metaGEM input, OPERA-MS indels, ORF counts, combined-run solver, core-years, Green Algorithms inputs, and others).
- **todos**: code refactor transform -> contract hoped for (Tony, 2026-11-27; not requested yet); rename for agents; contract authoring, Figure 2 library, Green Algorithms inputs, Zenodo DOI.

## Workers

- metasmith-e2e-install-test (peer session): witness gate merged into feat/engine/rc (e47326b9), ships in 0.26.4 (unreleased); will message on release.

## Closed

- **terms** (2026-11-27). property → type → contract → step → port → plan → instance.
- **outline-sections** (2026-11-26). Planning, Specification, Execution, Contracts, Benchmarks; Declarations as its own top-level section.

# Methods discussion stack

Goal: write the d2 Methods with the co-writing protocol, from `OUTLINE.md`. Decisions: `docs/methods-section/DECISIONS.md`.

**On every resume or compaction:** load the `dfs-interview` skill, then read and follow the co-writing protocol at `/home/tony/agentic_workspace/projects/self-improvement/writing-skill/docs/writing-skill/protocol-draft.md`, then read `OUTLINE.md`. Any compaction followup must name all three. The protocol is a draft and may change; reread it rather than working from memory.

## Current

**prose** (Tony, 2026-11-27: "compact. then write prose in chunks. then have an agent review for coherence and writing style. apply updates"). All sections have agreed points in `OUTLINE.md`, with titles in § Titles: Solver (Types, Contracts, Optional branching, Planning, Refinement, Verification), Specification (Interfaces, Inputs, Outputs, Parallel cases, Variadic contracts), Execution (Compiling to Nextflow, Running workflows, Caching), Benchmarks (seven titled mini paragraphs, three sentences or fewer, only what the Results leave out; details in `draft.md`), Declarations (AI-assisted development in two sentences; Data and code availability with a data table). Statistics cut; M4 Contracts dissolved into P1/P2/E2; B1 cut.

Progress (2026-11-27): Methods and Declarations in d3 (blue), matching `prose.md`; Execution split into Compiling to Nextflow, Grouping, Task execution, Running workflows, Caching, Cache keys. Results fixed in d3: Lineage sentence (strict rule), MAG pairing (reciprocal best partner; 94.6/93.9% short, 90.8% long, control 94.1-95.2%), vOTU sentence names Jonker-Volgenant with the moved EndNote fields (43, 44), CPU hours -> core-hours, Jaccard index. Tony must run EndNote Update Citations (43/44 now cited after 46-54). Incident: a partial copy of an EndNote field left an unterminated field that swallowed the doc; d3 was restored by SaveAs from the backup and all edits replayed by script (copy fields only as Range(Code.Start-1, Result.End+1)). Still TODO: Zenodo DOI, Green Algorithms inputs (no record), contract table (Supplementary Table 4). Word driver: `$CLAUDE_JOB_DIR/tmp/cap/run.sh <ps1>`.

Pending d3 Results edit (agreed in principle): MAG pairing is reciprocal best skani match, not Jonker-Volgenant (verified: JV only in `results/e3/votu_lib.py`); Results should just say "reciprocal partner" with the method in Benchmarks/MAG comparison; the 93.9% is Metasmith's MAGs (nf-core/mag's is 94.6%, short arm); the vOTU sentence must name JV with refs 43, 44 since it no longer matches "the same way as for MAGs". Word on capella: recreate an interactive schtasks task (`msm_word`); recipe not in transcripts; blue for additions, copy neighbour formatting (Arial 12), save after each edit.

## Waiting on the user

- Whether to restart the agent->worker / transform->contract refactor (two attempts were killed by interrupts; worktree `engine/rename-worker-contract` holds an unfinished merge of origin/release, one conflict in tests/metasmith/cache/fixtures/template_golden.json).
- Benchmark versions (nf-core/mag, Metasmith) and Data table accessions when prose needs them.

## Preferences

- (2026-11-27) Tony is on his phone: short messages, conversational, small sections, one block at a time.
- (2026-11-27) Settle the overall structure and grouping before prose; don't go into the weeds.
- (2026-11-27) One paragraph per concept.
- (2026-11-27) No examples in points unless necessary.
- (2026-11-27) Minimal overlap with the docs and the Results; each Methods paragraph gets a subtitle; benchmarks only document what the Results leave out.
- (2026-11-27) Methods paragraphs open with the problem or premise, then the mechanism. Justify the final design; never narrate how it was reached.
- (2026-11-27) Order of work: itemized points for each paragraph, one at a time, section by section, with a flow check per section; prose only after all sections have points, then one section at a time; check again; then into d3.
- (2026-11-27) Reuse the original d3 prose where it exists, above all the existing Methods prose ("most of that is good already"); update and fill gaps rather than rewrite.

- (2026-11-25) Results are more up to date than Methods; where they contradict, Methods changes.

## Stack

- **outline-paragraphs**: level 2, section by section: Planning (current), Specification, Execution, Contracts, Benchmarks, Declarations. M2 needs a code survey first (variadic inputs are new, on a branch; optional branching is the old mechanism).
- **paragraph-walk**: per paragraph in document order: points, prose, then into d2.
- **results-conflicts**: the 12 rows in `draft.md` where the records do not back the Results (MAG pairing method, metaGEM input, OPERA-MS indels, ORF counts, combined-run solver, core-years, Green Algorithms inputs, and others).
- **todos**: benchmark contract table (contract, tool, version, container URL); contract authoring, Figure 2 library, Green Algorithms inputs, Zenodo DOI.

## Workers

- rename-refactor: stopped by Tony's interrupt before any change (worktree `engine/rename-worker-contract` at rc 76823961, unpushed); restart only if Tony asks.
- metasmith-e2e-install-test (peer session): witness gate merged into feat/engine/rc (e47326b9), ships in 0.26.4 (unreleased); will message on release.

## Closed

- **rename** (2026-11-27). Agent -> worker; transform -> contract; read old, write new.
- **terms** (2026-11-27). property → type → contract → step → port → plan → instance.
- **outline-sections** (2026-11-26). Planning, Specification, Execution, Contracts, Benchmarks; Declarations as its own top-level section.

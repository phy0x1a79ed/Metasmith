# 1c draft: agents need planners (accepted for now by Tony, 2026-11-24)

Three tiers, each addressing the previous one's failure: naked agents; agents with a curated
catalogue; typed contracts (LLM-Modulo complementarity). BixBench rate and the 95%-per-step
arithmetic dropped in favour of 2026 failure-mode evidence.

Refs (all unreviewed preprints except Dziri, Kambhampati):
- Alam & Roy 2025, arXiv 2507.20122 (J Syst Softw label): expert-rubric scoring, anecdotal runs only; supports "hallucinated tools or incompatible parameter settings", omitted setup steps. Not "needed manual correction before they ran".
- Fa et al. 2026, BioAgent Bench, arXiv 2601.21800 (v4 Aug 2026): corrupted inputs carried to incorrect results; decoy picked by filename-suffix glob.
- Kurjan & Cribbs 2026, FlowBench, bioRxiv 10.64898/2026.06.12.731844: "incorrect toolchain selection rather than formatting errors"; edgeless graphs without DAG schema; "force a clean exit while leaving the underlying data invalid".
- Considered, not used: OmicsBench (Shaked 2026, arXiv 2610.21074), BiomniBench (bioRxiv May 2026), arXiv 2607.27556.

Accepted draft, trimmed 2026-11-25 (opening now follows 1b; planner guarantees moved to 1b):

When an agent writes a pipeline from scratch, each step is an unconstrained guess. Models invent tools and set incompatible parameters (Alam 2025), and because accuracy on composed tasks falls as steps are added (Dziri 2023), these errors compound over the length of a pipeline. A natural remedy is to restrict the agent to a curated catalogue, so that it can no longer invent what it calls; Biomni, for example, retrieves from 150 tools, 105 software packages and 59 databases (Huang 2025). A catalogue fixes what can be called, however, not how calls connect, and recent benchmarks locate the remaining failures at exactly these joins. On BioAgent Bench, correct high-level pipeline construction did not guarantee correct steps: agents carried corrupted inputs through to incorrect results without flagging them, and one selected a decoy file because its name matched (Fa 2026). On FlowBench, failures came from incorrect toolchain selection rather than formatting errors, plans written without a dependency schema came out as edgeless graphs, and models repaired faults by forcing a clean exit while leaving the data invalid (Kurjan 2026). Each of these runs to completion and returns plausible output, because nothing checks that one step's output is a valid input to the next. The guarantees of planning close this gap: a stronger model raises the odds that a join is right, but only types make a join checkable, and LLMs cannot reliably verify their own plans (Kambhampati 2024). Agents and planners are therefore complementary: the agent turns a question into a target and chooses among valid plans, while the planner guarantees that every join is valid.

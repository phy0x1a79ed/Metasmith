# Methods decisions

One section per closed topic, in the order the topics closed. Open state is in `STACK.md`.

## outline-sections (2026-11-26)

**Question.** What are the Methods' sections and in what order?

**Tony's words.** "type system (the internals and definitions, how the planner works). Then move into the surrounding infrastructure, interfaces, data instances, how actually giving the planner the intent with given and targets work. The new variadic inputs, as well as the old optional branching, how lineages are specified, target is just a transform, parallel planned cases, etc. Maybe other issues and how we work around them. Then we can move towards execution, how it compiles to nexflow, slurm presets, caching. Then we do contract authoring/design. M7 and M8 we can go over at the end. M7 is straight forward I think"

**Design.** Five Methods sections in this order: Planning (type system and planner internals); Specification (interfaces, data instances, givens and targets, variadic inputs, optional branching, lineage specification, target as a transform, parallel planned cases, issues and workarounds); Execution (Nextflow compilation, SLURM presets, caching); Contracts (authoring and design); Benchmarks. Declarations (statistics, AI use, availability) are their own top-level section beside Methods. The Methods no longer mirror the Results order.

Names revised the same day: "we can call sections: planning, specification, execution, contacts, benchmarks. Declarations is its own super section like methods".

**Landed.** `OUTLINE.md` level 1.

## terms (2026-11-27)

**Question.** What names the plan-level entity between type and instance, and what is the chain of terms?

**Tony's words.** "Data node doesn't really convey matched type… there's like a distinction between the type and the actual matched entity between contract, string, and DAG"; "We've been referring to kinds as types"; "let's try ports".

**Design.** property → type → contract → step → port → plan → instance. A port is a typed position on a step, one per output type, with a fixed lineage; later steps bind their inputs to ports; each port compiles to one Nextflow channel. Contracts keep "input types" and "output types"; "port" is used only for steps, not contracts. d0.2's "data node (DN)" covered both slot and joint and is retired. "Endpoint" and "application" leave the paper. Revised 2026-11-27 (outline-paragraphs / Execution): "transform" also leaves the paper, contracts are called contracts throughout, and "agent" is avoided because it now reads as an LLM agent.

**Landed.** `OUTLINE.md` § Terms.

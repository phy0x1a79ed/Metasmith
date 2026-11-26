# Methods decisions

One section per closed topic, in the order the topics closed. Open state is in `STACK.md`.

## outline-sections (2026-11-26)

**Question.** What are the Methods' sections and in what order?

**Tony's words.** "type system (the internals and definitions, how the planner works). Then move into the surrounding infrastructure, interfaces, data instances, how actually giving the planner the intent with given and targets work. The new variadic inputs, as well as the old optional branching, how lineages are specified, target is just a transform, parallel planned cases, etc. Maybe other issues and how we work around them. Then we can move towards execution, how it compiles to nexflow, slurm presets, caching. Then we do contract authoring/design. M7 and M8 we can go over at the end. M7 is straight forward I think"

**Design.** Five Methods sections in this order: Planning (type system and planner internals); Specification (interfaces, data instances, givens and targets, variadic inputs, optional branching, lineage specification, target as a transform, parallel planned cases, issues and workarounds); Execution (Nextflow compilation, SLURM presets, caching); Contracts (authoring and design); Benchmarks. Declarations (statistics, AI use, availability) are their own top-level section beside Methods. The Methods no longer mirror the Results order.

Names revised the same day: "we can call sections: planning, specification, execution, contacts, benchmarks. Declarations is its own super section like methods".

**Landed.** `OUTLINE.md` level 1.

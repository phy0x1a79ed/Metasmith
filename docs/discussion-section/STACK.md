# discussion-section: stack

## Purpose

Draft the Discussion section of the Metasmith manuscript: limitations, future directions, comparison with existing systems, and where the benchmark results sit in the literature.

Procedure, from dfs-interview § Work the stack:

1. Run `stack.py <folder> current` for the top topic. Ask only its own questions.
2. Dispatch read-only subagents to survey what already exists for the topic.
3. Record each difference between the survey and the user's description.
4. Ask the user about each difference with an unclear answer.
5. Put one question per message to the user, or a small set of closely related questions. Give your recommendation with it.
6. Queue the other questions with `stack.py <folder> ask`.
7. Match each answer to the message it replies to. Ask when a reply could answer more than one message.
8. Record each answer in the topic's `README.md`. Copy the user's words from `quote.py`.
9. Write the result as the current design.
10. Tick each answered question with `stack.py <folder> answer`.
11. Run `stack.py <folder> close` when the topic's question queue is empty.
12. Commit.
13. Compact only when the closed topic ran long, with many exchanges or large reads. After a short topic, present the next topic in the same turn.
14. To compact, run `reflection(verb="compact", args={followup:...})`. Write a followup that invokes `dfs-interview` by name. Name the discussion folder, the closed topic, its commit and the new top topic in it.

## Current topic

**limitations**. Its result: `limitations/README.md`.

## Stack

- **limitations** (2026-11-09): Limitations
- **future-directions** (2026-11-09): Future directions
- **comparison** (2026-11-09): Thoughtful comparison with what is already out there
- **results-in-literature** (2026-11-09): Where the results fit and compare in literature

## Parked

- **d2-fragments** (2026-11-02, Metasmith_d2.docx Discussion): four draft paragraphs already in d2 — (a) the 1:1 mapping of transforms to execution steps conflates conceptual and logistical partitioning; (b) a heading "Conditionals and looping"; (c) no domain knowledge: no system picks between redundant tools, the user "needs to know what they are doing"; (d) AI agents could implement from scratch, so Metasmith's value is the specification. Each fragment enters the topic it serves.

## Closed

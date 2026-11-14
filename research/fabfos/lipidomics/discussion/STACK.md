# armando-lipidomics: stack

## Purpose

Prepare a context presentation of the SCADC lipidomics results for the Armando consult: what was measured, what we found, and the questions to ask him (lipidomics interpretation, controls, sample mix-up).

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

**alignment**, under **feature-set**. Its result: `results/feature-set/alignment/README.md`.

## Stack

- **results** (2026-11-09): I need to prepare context presentation for scadc lipidomics results
  - [ ] Which findings make the cut, in what order?
  - **feature-set** (2026-11-13): ok, are we able to resolve a set of features that correspond to metabolites, even if we cant identify each feature? Can we resolve  a feature set in an unsupervised way? Like ORF prediction, can we first get a minimally transposed version of the raw data, if you kow what I mean?
    - [ ] Does 'minimally transposed' mean re-deriving compound-level features from raw mzML ourselves, versus componentizing the facility's MetaboScape table?
    - **alignment** (2026-11-13): can we now talk about how to "line up" ions between samples? to get a common table
- **asks** (2026-11-09): Meeting notes 20 Oct 2026 action item: SCADC presentation for Armando. Ask about lipidomics, controls, sample mix-up
  - [ ] Which 'controls are high' observation is meant: the 06 Oct volcano note (why controls are high?)
  - [ ] What is the sample mix-up: the unverified OD-replicate to lipidomics-replicate pairing, or a separate incident?
- **format** (2026-11-09): Format and length of the Armando presentation (deferred from audience)

## Parked

## Closed

- **audience** (closed 2026-11-09): `audience/README.md`

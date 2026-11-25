# Protocol

## Purpose & Contents

This file fixes the analysis of the BixBench ladder before any pilot run. It holds the capsule split, the metric, the contrasts, the test, the fault rule and the stop rule. A change to this file after the pilot starts goes in the *Amendments* section with its date and its reason.

## Design

- Three rungs run on one model, `claude-sonnet-5-5`: Harness, Search, Planner. `run_one.py --rung` selects the rung.
- All rungs share one image, one limit of 40 tool calls, one hour of wall time per run, and one grader.
- A run is one agent trajectory on one question. Each question runs 3 times per rung.
- The environment is an amd64 rebuild of the BixBench image. Scores are not directly comparable to scores from the published arm64 image.

## Capsule split

`split.py` holds the family of each capsule and draws the pilot set. The families came from question text on 2026-11-24, before any agent run.

| Family | Capsules | Questions |
|---|---|---|
| tabular | 20 | 83 |
| expression | 18 | 65 |
| phylogenetics | 15 | 51 |
| reads | 1 | 6 |

The pilot set is 8 capsules: 3 tabular, 3 expression, and 2 from phylogenetics and reads together. The draw is `random.Random(20261125).sample` on each stratum in that order, with capsules sorted by number.

- Pilot (29 questions): bix-2, bix-20, bix-41 (tabular), bix-3, bix-26, bix-53 (expression), bix-12, bix-57 (phylogenetics).
- Confirmatory (176 questions): the other 46 capsules.

Prompts, tool specs, the planner helper and the runner change on evidence from pilot capsules only. A commit freezes them before the first confirmatory run. bix-1 and bix-16 served as smoke tests while the runner was built. No prompt changed in response to their results.

## Primary metric

The metric is open-answer accuracy: the fraction of runs graded correct, over all questions and repeats of a rung. `grade.py` applies the BixBench rules at the pinned commit, with Sonnet 5.5 as the judge. The `correct` field is primary. The `lenient` field is a sensitivity check.

A run with no answer counts as incorrect. This includes a run that reached the tool-call limit, the time limit or the spend limit.

## Contrasts and test

The three contrasts are Search − Harness, Planner − Search and Planner − Harness, in accuracy on the 46 confirmatory capsules.

1. Resample capsules with replacement, 10,000 times, seed 20261125. A resampled capsule brings all of its questions and repeats on all three rungs.
2. Report the observed difference and the 2.5th and 97.5th percentiles of the resampled differences.
3. Compute a two-sided p-value per contrast as twice the smaller tail fraction of resampled differences at or beyond zero.
4. Adjust the three p-values with the Holm method. A contrast is significant at an adjusted p-value below 0.05.

The same analysis on all 54 capsules is reported for comparison with published scores. It is not confirmatory, because the pilot capsules shaped the prompts.

## Secondary measures

These are descriptive. No test applies to them.

- Accuracy per rung and family.
- Accuracy per rung and grading mode.
- Tokens and cost per run. A Search or Planner run includes its card selection call.
- Wall time per run.
- The fraction of runs with no answer.
- Repeat agreement: the fraction of questions where all 3 repeats have the same grade.
- Planner uptake: the fraction of Planner runs with at least one `bx plan` or `bx run` call in `tool_calls.jsonl`.
- Planner accuracy split by uptake. The agent chooses when to plan, so this split is not an effect estimate.

## Faults

A fault is a run that the infrastructure broke: no `result.json`, no model turn, an authentication or rate-limit error, or a container that failed to start. Rerun a faulted run up to 2 times. Drop a question and repeat from all three rungs when one rung still faults. Report the number of faults and drops per rung.

A wrong, missing or late answer is not a fault.

## Stop rule

Stop after the pilot when planner uptake is below 10% of Planner runs after prompt tuning. The full run cannot then measure the planner. Otherwise the pilot report gives the projected cost and duration, and Tony decides.

## Amendments

None.

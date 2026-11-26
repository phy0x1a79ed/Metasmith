# Pilot result, 2026-11-25

## Purpose & Contents

This file records the pilot of the BixBench ladder: the scores, and the cause of every failed run. `PROTOCOL.md` fixes the design. The runs are on altair in `research/bixbench_ladder/cache/pilot`, outside git. Reproduce the tables with `python3 analyse.py --out cache/pilot --set pilot`.

## Setup

- 8 pilot capsules, 29 questions, 3 rungs, 3 repeats: 261 runs on `claude-sonnet-5-5`.
- Image `bixbench-ladder/run:dev`, offline sandbox, 40 tool calls, one hour per run.
- Harness and Search ran at commit `4ddc8b00`. Planner ran with the tuned prompt of commit `60dfb9cc`.
- No run faulted. No run reached the tool-call limit, the time limit or the spend limit. Every run gave an answer.

## Scores

| Rung | Accuracy | Lenient | Mean seconds | Mean USD | Repeat agreement |
|---|---|---|---|---|---|
| Harness | 0.483 | 0.483 | 180 | 0.071 | 0.931 |
| Search | 0.506 | 0.506 | 267 | 0.144 | 0.966 |
| Planner | 0.471 | 0.483 | 260 | 0.152 | 0.897 |

| Contrast | Difference | 95% interval | Holm p |
|---|---|---|---|
| Search − Harness | +0.023 | 0.000 to +0.061 | 0.42 |
| Planner − Search | −0.034 | −0.072 to −0.009 | 0.15 |
| Planner − Harness | −0.011 | −0.037 to 0.000 | 0.66 |

Accuracy per family is equal on all rungs for expression (0.231) and phylogenetics (0.833). Tabular is 0.600, 0.667 and 0.567.

## Planner uptake

- Before tuning, 0 of 29 Planner runs called `bx plan` or `bx run`. Seven listed types or steps and then wrote their own code.
- The tuned prompt tells the agent to prefer the planner and shows one worked chain. Uptake rose to 11 of 87 runs (12.6%).
- Every use was a DESeq2 or PyDESeq2 chain on bix-3 or bix-53. Every chain completed. All 11 runs were graded wrong, with the same answer as the runs that wrote the step by hand.
- No Planner run used the planner on a tabular or phylogenetics question.

## How the runs failed

134 of 261 runs were graded wrong: 45 Harness, 43 Search, 46 Planner. Fifteen questions account for all of them, and twelve of those failed on every rung and repeat.

### 1. The reference data is not reachable: 54 runs, 6 questions

Questions bix-26-q3, q4, q5 and bix-53-q3, q4, q6 ask for a KEGG or WikiPathways enrichment. The sandbox is offline, and the image holds no KEGG gene sets for the organism, no Enrichr library and no mouse gene-ID mapping.

- The agent ran the differential expression step correctly.
- It tried the download, searched the disk for a local copy, and found none.
- It then answered from memory and said the answer was a guess. Every guess was wrong.
- No tool card and no planner step can supply the missing data, so the three rungs behave the same.
- The reference answer of bix-53-q4 is a p-value, and the question asks for a count. No run can pass it.

### 2. The agent chose a different analysis definition than the reference: 77 runs, 9 questions

The question leaves a choice open, the agent picks one reading, and the reference used another. The agent often listed the reference's reading among its alternatives.

- **bix-20-q1, q3, q4 (27 runs).** Proportion of benign variants. The agent kept variants with no ClinVar class in the denominator and got 0.68 to 0.79. The reference range is 0.80 to 1.00. The agent's own alternatives (drop unclassified variants, or drop intronic splice-region variants) fall inside the range.
- **bix-20-q2 (5 of 9 runs).** The sample group is worded ambiguously. The agent picked the affected patients (0.68) in 5 runs and the control children (1.0, correct) in 4.
- **bix-3-q1 (9 runs).** The workbook holds normalised counts. The agent rounded them and got 247 genes. The reference range is 700 to 1000. Scaling by 100 before rounding gave the agent 545.
- **bix-3-q2 (9 runs).** The agent defined a differentially expressed gene by adjusted p alone and got a proportion of 0.38. The reference range is 0.03 to 0.04, which implies a fold-change filter and one treatment group.
- **bix-3-q3 (9 runs).** A near miss: 866 or 871 against a range of 700 to 800. The agent kept three samples that the workbook marks as outliers.
- **bix-3-q4 (9 runs).** The agent applied no fold-change cutoff and pooled all animals: 8,603 genes against a range of 400 to 500.
- **bix-57-q1 (9 runs).** Gap percentage after MAFFT: 5.80 against a reference of 4.8. The cause is not established. Candidates are the MAFFT version and the set of files aligned.

The Search cards and the planner steps expose these choices as parameters, but they do not say which value the question intends. The agent made the same choice on every rung.

### 3. Answer format or a one-off choice: 3 runs

- bix-41-q5, Planner, one run: the value was right, and added words broke the exact-match grade. The lenient grade passes it.
- bix-2-q1, Harness, one run: the agent gave 3.0% where the range expects a proportion.
- bix-2-q2, Planner, one run: the agent added a gene-list filter and got 59.3 against a range of 60 to 70.

### What did not cause a failure

No run failed because the agent did not know a tool, called a tool wrongly, or wired steps wrongly. Those are the failures that tool cards and a planner address.

## Projection for the full ladder

The 46 confirmatory capsules hold 176 questions, 1,584 runs. At the pilot's rates this takes about 26 hours on altair at four runs at a time, and about 195 USD at API prices.

## Open decision

Tony decides go or stop. The pilot gives no sign of a planner effect. The two changes that would raise the score are network access for reference data, and a way to resolve underspecified questions. Neither is a rung of this ladder.

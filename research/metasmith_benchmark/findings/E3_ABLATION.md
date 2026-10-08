# E3 ablation: which assemblers the Pratama catalogue needs

## Purpose & Contents

Pratama 2026 builds one vOTU catalogue from three assembly lanes: short-read metaSPAdes, short-read MEGAHIT and hybrid metaSPAdes. This file reports what each lane and one metaSPAdes setting contribute to that catalogue, and what they cost. Each rung builds the whole pooled catalogue under one assembler set and scores it against Pratama's 257,252 vOTUs.

It holds the rung table, the conclusions it supports and the caveats on its numbers. `E3_PARITY.md` holds how the plan differs from the paper and the scoring cutoffs. `drivers/e3_pratama.py --rung` and its `RUNGS` table are the source of truth for which transforms each rung masks.

## The rungs

Every rung runs the same reads, trimmed by `bbduk_pratama`, through the same four callers, curation, CheckV trim and MMseqs2 clustering as E3. Only the assembler set changes.

| Rung | Short reads, 65 runs | Hybrid, 17 pairings | Change | Run |
|---|---|---|---|---|
| R0 | metaSPAdes + MEGAHIT | hybrid metaSPAdes | none, E3 as run | `nP0Jxo8W` (wave e3_w9) |
| R1 | metaSPAdes `--only-assembler` + MEGAHIT | hybrid metaSPAdes `--only-assembler` | read error correction off in both metaSPAdes lanes | `nP0Jxo8W` |
| R2 | MEGAHIT | hybrid metaSPAdes `--only-assembler` | short-read metaSPAdes removed | `arThlxPI` |
| R3 | MEGAHIT | OPERA-MS over a MEGAHIT draft | hybrid assembler swapped | `osU8IP4o` |
| R4 | MEGAHIT | Flye on the MinION reads, polished by POLCA | hybrid assembler swapped | `wdiikdGR` |

R0 and R1 share the plan key `nP0Jxo8W` and therefore one run directory.

R2, R3 and R4 share the short-read lane, so they compare the three hybrid assemblers directly.

## Results

Recovery counts a Pratama vOTU when a rung vOTU matches it at ANI ≥ 95 over ≥ 85% of the Pratama vOTU. Matched counts the rung's own vOTUs at ANI ≥ 95 over ≥ 85% of their length to any Pratama vOTU. Paired identity is ANI × aligned fraction of the Pratama vOTU, over a one-to-one assignment of the two catalogues that maximises summed identity (sparse Jonker–Volgenant, SciPy). CPU hours are fir allocated time (elapsed × cpus) of each task's successful attempt.

| Rung | vOTUs | Matched | Recovered | Recovery | Paired median | Assembly CPU-h | Viral-lane CPU-h | Total CPU-h |
|---|---|---|---|---|---|---|---|---|
| R0 | 243,186 | 196,547 | 202,053 | 78.5% | 99.05% | 40,404 | 23,819 | 64,351 |
| R1 | 244,351 | 192,052 | 196,411 | 76.4% | 98.76% | 22,342 | 24,069 | 46,538 |
| R2 | 178,916 | 139,379 | 180,256 | 70.1% | 99.21% | 10,694 | 12,531 | 23,353 |
| R3 | 172,295 | 123,599 | 168,336 | 65.4% | 98.88% | 7,463 | 10,671 | 18,262 |
| R4 | 157,800 | 118,727 | 164,210 | 63.8% | 99.02% | 6,314 | 9,732 | 16,174 |

Total CPU-h includes 128 CPU-h of read QC, shared by every rung. The viral lane covers contig splitting, the four callers and the pooled tail from the merge to the final recovery table. At least one rung recovers 210,241 Pratama vOTUs (81.7%).

Assembly CPU-h per assembly:

| Assembler | CPU-h per assembly | Rungs |
|---|---|---|
| metaSPAdes, error correction on | 399 | R0 |
| metaSPAdes `--only-assembler` | 179 | R1 |
| MEGAHIT | 87 | all |
| hybrid metaSPAdes, error correction on | 519 | R0 |
| hybrid metaSPAdes `--only-assembler` | 297 | R1, R2 |
| MEGAHIT draft + OPERA-MS | 107 | R3 |
| Flye + POLCA | 39 | R4 |

Recovery of Pratama's vOTUs by the lane their name carries (113,105 metaSPAdes, 112,924 MEGAHIT, 31,223 hybrid):

| Rung | metaSPAdes | MEGAHIT | hybrid |
|---|---|---|---|
| R0 | 72.2% | 81.8% | 89.8% |
| R1 | 71.1% | 81.8% | 75.7% |
| R2 | 60.7% | 78.1% | 74.9% |
| R3 | 60.7% | 78.3% | 36.0% |
| R4 | 60.2% | 77.9% | 26.3% |

The rungs' own vOTUs per lane tag. A vOTU takes its representative's lane, so a lane gains vOTUs when another lane that used to represent them leaves:

| Rung | metaSPAdes | MEGAHIT | hybrid |
|---|---|---|---|
| R0 | 95,165 | 114,409 | 33,612 |
| R1 | 95,057 | 115,495 | 33,799 |
| R2 | | 143,996 | 34,920 |
| R3 | | 142,578 | 29,717 |
| R4 | | 145,719 | 12,081 |

## What the ladder shows

- **Error correction matters mainly for the hybrid assemblies.** Turning it off (R1) costs 2.1 points of overall recovery and keeps the vOTU count. The loss sits in Pratama's hybrid vOTUs, from 89.8% to 75.7%. Pratama's metaSPAdes vOTUs move from 72.2% to 71.1%. R2 reuses R1's hybrid assemblies and scores 74.9% on them, so the drop is a property of the assemblies. Turning it off cuts metaSPAdes' cost by 55% on short reads and 43% on hybrids. Turning it off on short reads alone would save about 14,000 of R0's 64,351 CPU-h. No rung measures that set.
- **Short-read metaSPAdes earns its place but costs half the catalogue.** Removing it (R1 to R2) loses 6.3 points of recovery and 65,000 vOTUs, and saves 23,200 CPU-h. Pratama's metaSPAdes vOTUs fall from 71.1% to 60.7% and its MEGAHIT vOTUs from 81.8% to 78.1%. MEGAHIT represents 28,500 more clusters once metaSPAdes leaves, so the two short-read assemblers overlap heavily but not fully.
- **Hybrid metaSPAdes beats both swaps by a wide margin on the hybrid vOTUs.** With the same MEGAHIT lane, overall recovery falls from 70.1% (hybrid metaSPAdes) to 65.4% (OPERA-MS) and 63.8% (Flye + POLCA). On Pratama's hybrid vOTUs it falls from 74.9% to 36.0% and 26.3%. The swaps save 5,100 and 7,200 CPU-h. OPERA-MS barely scaffolds MEGAHIT's fragmented short-read graph. Flye + POLCA yields 12,081 hybrid vOTUs against 34,920, because these MinION reads are short (N50 1.6 kb).
- **The assembler set changes how many vOTUs a catalogue recovers, not how well.** Paired identity medians stay between 98.8% and 99.2% on every rung.
- **Each step down the ladder buys recovery at a rising price.** Per extra recovered Pratama vOTU, R2 over R4 costs 0.45 CPU-h, R1 over R2 costs 1.4 CPU-h, and R0 over R1 costs 3.2 CPU-h.

## How the numbers are built

Each run's `final_votu_recovery_pratama` step writes the skani table of its final set against Pratama's catalogue. Recovery, matched counts and pairing read that table. R0 reads wave e3_w9's table.

`results/e3/ablation/` holds the scorers, the sacct and task-list inputs of the CPU ledger, and their outputs. Run `abl_cpu.py`, then `abl_lanes.py`, then `abl_score.py`. The rung catalogues are too large to commit. The scorers read them from `$E3_FIG` (default `~/scratch/e3_fig`).

The CPU ledger charges a step a rung took from cache at the cost of the run that computed it. Short-read QC and assembly come from run `Son2YJiI`, hybrid assembly from `nP0Jxo8W` in September, and every new assembly from the rung's own runs. The R3 and R4 smoke runs (`1DdONH9q`, `5dqexz5s`) computed sample SRR32696698's hybrid lane, so the ledger adds them.

CAUTION: query fir's `sacct` by job id. A query bounded by `-S` and `-E` silently drops some array elements, and refuses a range wider than about a week.

## Caveats

- CAUTION: E3's own steps ran across several relaunches, some twice, so the ledger charges each its mean successful task times its task count in `nP0Jxo8W`'s September trace. fir's records hold under half the tasks of VIBRANT and geNomad on short-read metaSPAdes contigs. Those two are charged at R1's mean for the same transforms, about 8,000 of R0's 64,351 CPU-h.
- CAUTION: R4's DeepVirFinder skips contigs over 2 Mbp. Flye + POLCA contigs reach 4.32 Mbp. The other three callers still see them. R4's relaunch recomputed DeepVirFinder on the MEGAHIT lane under the guarded transform, at 1,538 CPU-h. The ledger charges R4 that recompute in place of E3's original.
- R3's OPERA-MS scaffolds a fresh MEGAHIT draft of each pairing's short reads (`e3::megahit_draft`), not the catalogue's MEGAHIT assembly. Fed the catalogue's assembly, OPERA-MS's output filled the merge's MEGAHIT slot and the plan dropped that lane. The draft's cost counts as R3's assembly.
- R1's short-read `--only-assembler` lane ran out of memory at 192 GB on 4 of 65 runs, in K77 path extension, and passed at 384 GB.
- Each rung is one run. The ladder adds one change per rung, so R1 measures error correction with short-read metaSPAdes present, and R2 measures short-read metaSPAdes with error correction off. Neither effect is measured from the other end.
- The ablation itself spent 43,019 CPU-h on fir, 1,807 of them on failed or cancelled attempts.

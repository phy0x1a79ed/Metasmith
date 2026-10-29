# Routing code in nf-core/mag against Metasmith's typed contracts

## Purpose & Contents

This directory holds one snapshot for the manuscript supplement. It counts the hand-written channel routing nf-core/mag 5.5.0 needs for benchmark E1's configuration. It also counts the declarations E2's Metasmith transforms carry for the same tool calls. This file says how to rerun the count and where it is weak. The numbers live in `summary.tsv`.

## Rerun

Run `mamba run -n msm python measure.py --nfcore <nf-core/mag checkout> --bench <bench-E2>/research/metasmith_benchmark`.

- The checkout must be tag 5.5.0, commit `56abab5b023ce953c9c43fe21090d156ad0e18af`. The script refuses any other commit.
- `--bench` refreshes `inputs/` from the bench-E2 worktree. Omit it to rerun on the copies in `inputs/`.
- The script writes `lines.tsv`, `summary.tsv`, `modules.tsv` and `metasmith.tsv`.

`lines.tsv` lists every non-blank, non-comment line of every workflow or subworkflow file the run reached, with its status, arms, bucket and subtype. `modules.tsv` lists the module files and `conf/modules.config` entries of the processes that ran.

## Method

1. Read E1's params from `nextflow.config`, then `fir.config`, then `control.config`, then the `run_e1.sbatch` command line.
2. Walk the call graph from `main.nf`'s entry workflow. Drop each `if`/`else` branch whose condition is false under those params.
3. Drop, per arm, each subworkflow whose processes completed no task in that arm. The union of the two arms is the PRUNED count.
4. Classify each kept line as routing, config, invocation, versions or other. `other` holds non-channel Groovy: validation, banners, citations, email.
5. Add the module `main.nf` lines (without `stub:`) and `conf/modules.config` entries of the processes that ran for the full denominator.

CAUTION: the script checks itself against E1's DAG. The processes the pruned code invokes must equal the processes in `inputs/e1/e1_{short,long}.dot`, or the script exits.

## Known limits

- **QUAST differs per arm.** `skip_quast` entered `control.config` after E1 long had run QUAST to completion. The script sets it false for the long arm and true for the short arm.
- **Classification is by rule, not by meaning.** MultiQC report plumbing counts as routing (subtype `multiqc`). Plain channel aliases such as `ch_x = PROC.out.y` count as invocation (subtype `alias`). Validation code inside channel closures counts as routing.
- **Pruning is static.** Data-dependent branches inside closures stay in the count. A short-arm count keeps mag.nf's call lines for long-read subworkflows.
- **Metasmith counts are declarations, not lines.** E2 transforms also read `sample` and `platform` from a `read_metadata` JSON inside their protocols. That is the runtime counterpart of nf-core's meta map, and it is not routing.
- **The driver is not counted.** `e2_cami.py` declares givens and targets for each arm. Those declarations stand in for nf-core's samplesheet and params.

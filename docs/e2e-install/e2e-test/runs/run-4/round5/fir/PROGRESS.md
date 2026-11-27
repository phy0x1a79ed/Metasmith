# PROGRESS
Done: metasmith 0.26.2 installed (envs/msm_env). GUI pid 3016903 on :8092 (log gui.log).
Done: agent important-fir deployed to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir (slurm, slurmAccount=def-shallam_cpu, setup `module load apptainer/1.3.5`).
Running: GUI setup run zOFmP (task WuIKjdgK) for judicious-hedgehog (= engcyc_prep_references), preset slurm. Remote nextflow run token v6rIIwoB (login1 java). Scratch 134G at 11:42.
Workflow maroon-pigeon (= engcyc_metagenomics) solved, short case SRR9658108 (sra_short_read_accession), references case kept, hybrid/long deleted, empty rows removed. NOT run yet; wait for setup zOFmP to finish first (same agent, cache).
Monitor: task byqto3ffe watches setup nextflow on fir.
Next: when setup done -> GUI maroon-pigeon > stage and run (agent important-fir, preset slurm). Then wait, collect results to ./results (scp/rsync from fir output dir), write REPORT.md + CONTROL.json.
05:0x tick: setup run v6rIIwoB still running (NF=3), 489G on scratch; squeue: buildPhyloflashDB (15:34), buildIphopDB (7:34). No GUI errors. Monitor b9poisz2n expired; re-arm if needed.
tick: setup still running
tick: setup still running
tick: buildIphopDB finished (scratch 900G->637G, likely archive cleanup); buildPhyloflashDB still running; NF=3; no errors
tick: setup running; buildGtdbDB active

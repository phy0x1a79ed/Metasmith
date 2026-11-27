# PROGRESS
- Read docs. Install plan: mamba (conda-forge, bioconda, hallamlab) into sandbox env. ssh fir works.
- NEXT: install metasmith (detached, log at install.log).
PID 3115268 install (mamba create msm_env), log install.log
PID 3119409 msm gui port 8092, log gui.log, workspace metasmith_ws
- Install done (envs/msm_env). GUI running PID 3119409 on 8092 (gui.log).
- Agent neon-fir created in GUI (fir, /scratch/phyberos/msm_e2e/run-4-fir, apptainer, slurm). Deploy clicked, in progress.
- Pre-existing /scratch/phyberos/msm_e2e/run-4-fir on fir (from before this run).
- NEXT: confirm deploy done, then setup run of engcyc_prep_references via GUI workflows tab.
- Workflow misty-wrasse (engcyc_prep_references) solved, 55 steps. NEXT: set up / run on neon-fir agent.
- Setup run launched from GUI: run misty-wrasse-xPO0d (Runs tab). Monitoring.
- 13:50 setup run 8Kwcx8Bf on fir running (nextflow driver on login1); 37 steps had exitcode at last check. Keep polling.
- 14:10 setup run still going (38 exit0). scratch quota ok (1385GiB/19TiB). downloads at ~19MB/s, long.

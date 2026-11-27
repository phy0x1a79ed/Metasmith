# PROGRESS
Done: msm 0.26.2 installed in envs/msm_env (conda/mamba per docs/setup/install.rst).
Done: GUI running on :8091 (PID 3009884, log logs/gui.log, workspace metasmith_ws).
Done: agent "brown-sockeye" deployed via GUI to ssh://sockeye:/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye (apptainer, slurm preset, slurmAccount=st-shallam-1, setup: module load gcc/9.4.0 apptainer/1.3.1).
Note: ssh sockeye works from shell (login02) and the GUI deploy reached it.
Next: GUI Workflows tab -> engcyc_prep_references_lite -> set up / run on brown-sockeye; then engcyc_metagenomics_lite default targets, SRR9658108; then collect results to ./results.
RUNNING: engcyc_prep_references_lite SETUP run on brown-sockeye, GUI run id brown-armadillo/brown-armadillo-98mbv (started 2026-11-27 ~04:28 local). Job IDs: not yet known (check Runs tab / ssh sockeye squeue -u txyliu).
Next: wait for it in GUI Runs tab; then engcyc_metagenomics_lite (default targets, SRR9658108 as ncbi::sra_short_read_accession on read_pair); then collect results to ./results.
Monitor task b5ax1ttmh: tails newest main.log of agent runs on sockeye (agent home /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye; run dirs runs/<task>/_metasmith/logs.*/main.log).
Cluster note: squeue shows 7 "rescue" jobs RUNNING under txyliu (not ours; left alone).
04:31 setup run (nxf run ShUeUoct on sockeye, log .../runs/ShUeUoct/_metasmith/logs.2026-11-27_04-29-09/main.log) is pulling containers (container_images 19G, progressing). Waiting.
04:33 WAITING: background until-loop byj550epv polls sockeye setup-run main.log for terminal markers (Execution complete / failed / ERROR ~). Will be notified on exit.
NEXT after setup completes: GUI Runs tab check; then Workflows > + workflow engcyc_metagenomics_lite > set SRA row (read_pair type ncbi::sra_short_read_accession, value SRR9658108, delete read rows) > solve > stage and run on brown-sockeye slurm (same agent, same agent home so caches are reused) > wait > collect to ./results.
04:48 SETUP RUN COMPLETED (engcyc_prep_references_lite, nxf ShUeUoct on sockeye, "run completed at 04:48:33", 38 outputs, no ERROR lines). Wait loop byj550epv ended.
NEXT: engcyc_metagenomics_lite in GUI (agent brown-sockeye, slurm, SRR9658108).
11:57 METAGENOMICS RUN LAUNCHED: GUI run charming-alligator/charming-alligator-mrhHY (agent brown-sockeye, slurm, SRR9658108). Watch the newest runs/*/_metasmith/logs.*/main.log on sockeye.
Background wait bhamcvema: polls sockeye runs/a6rB7vFV main.log for completion/error (task key a6rB7vFV).

# PROGRESS
- [x] 1 install metasmith v0.26.2 -> envs/msm_env (logs/install.log)
- [x] 2 GUI running: msm gui --port 8094 --no-browser (cwd metasmith_ws), log logs/gui.log.
- [x] 3 agent axiomatic-fir deployed to fir: ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir-lite; ping OK.
- [~] 4 setup run for workflow brass-mayfly (engcyc_prep_references_lite) RUNNING on fir: GUI run lrLku, task key jaTvne6n, nextflow driver PID 3962775 (since 13:20:18 local), SLURM job 6652695. Check: ssh fir 'tail runs/jaTvne6n/_metasmith/logs.latest/nxf.log'
- [~] 5 workflow courageous-mandrill (engcyc_metagenomics_lite): short case with SRR9658108 (ncbi::sra_short_read_accession), hybrid/long removed, references case kept. Solving in GUI (step 26). Next: solve OK -> run AFTER setup done, agent axiomatic-fir, preset slurm.
- [ ] 6 collect results to ./results
Failed so far: first GUI launch werkzeug error (not reproduced)
Notes: Don't touch other nextflow procs on login1 (rP9w0ycI etc.). GUI discard buttons are two-step (click twice).
UPDATE: setup run jaTvne6n RUNNING on fir (7/12 processes completed at 13:25 fir time, SLURM job 6652695 running, 0 errors). Watcher: scripts/watch_setup.sh (detached), writes logs/watch_setup.log with SETUP_DONE/SETUP_ERROR.
NEXT: when SETUP_DONE -> GUI run courageous-mandrill (engcyc_metagenomics_lite, short=SRR9658108, refs case) on agent axiomatic-fir, preset slurm, via Workflows > courageous-mandrill > stage and run.

[14:01 MST resume] GUI alive: msm gui PID 4185443 port 8094. Setup run jaTvne6n still running on fir (driver PID 3962775): downloadUniRef50DB, downloadKofamDB, downloadGtdbDB RUNNING (local executor on login1). Earlier SLURM job 6652695 COMPLETED. Watcher PID 66548 still polling (logs/watch_setup.log). Next: wait for SETUP_DONE, then GUI courageous-mandrill run.
[14:16] setup jaTvne6n: 16 processes COMPLETED, no errors; downloadUniRef50/Kofam/GTDB still RUNNING, watcher PID 66540 active. Monitor re-armed (expires 5m; re-arm on expiry).
[14:41] autonomous tick: setup jaTvne6n 18 processes COMPLETED, no errors; UniRef50 and GTDB still RUNNING; watcher 66540 active. Nothing to act on yet.
[15:02] autonomous tick: setup jaTvne6n 22 COMPLETED, no errors; buildGtdbDB (SLURM 6701389), UniRef50, VIBRANT downloads RUNNING; watcher 66540 active.
[15:23] autonomous tick: setup jaTvne6n 29 COMPLETED, no errors; UniRef50 and VirSorter2 DB still RUNNING; watcher 66540 active.
[15:44] autonomous tick: setup jaTvne6n still 29 COMPLETED, no errors; UniRef50 download active (log updating, ~910K/s, ETA ~75 min). Watcher 66540 active.
[16:05] autonomous tick: setup jaTvne6n still 29 COMPLETED, no errors; UniRef50 download at ~80%, ~41 min left. Watcher 66540 active.
[16:26] autonomous tick: setup jaTvne6n still 29 COMPLETED, no errors; UniRef50 at ~90%, ~18 min left. Watcher 66540 active.
[16:47] autonomous tick: setup jaTvne6n still 29 COMPLETED, no errors; UniRef50 at 99%, ~1 min left. Watcher 66540 active.
[17:08] SETUP_DONE: setup jaTvne6n Workflow completed, 31 processes COMPLETED, buildUniRef50DB SLURM 6724145 exit 0, no errors. NEXT: start courageous-mandrill via GUI (agent axiomatic-fir, slurm preset) in browser; then collect results.
[17:09] RUN STARTED via GUI: courageous-mandrill (engcyc_metagenomics_lite, SRR9658108 short case, refs kept, default targets), run l6Ly2, task key nxsA1XR2, agent axiomatic-fir, preset slurm, params slurmAccount=def-shallam_cpu slurmGpuAccount=def-shallam_gpu. Status: staging. Setup run lrLku/jaTvne6n completed (GUI shows completed).
NEXT: monitor run nxsA1XR2 on fir (runs/nxsA1XR2/_metasmith/logs.latest/nxf.log); when done, collect results to ./results.
[17:29] autonomous tick: run l6Ly2 (nxsA1XR2) 24 processes COMPLETED on fir, progressing.
[17:29] OBSERVATION: run nxsA1XR2 is re-running reference downloads (downloadGtdbDB, downloadKofamDB, downloadUniRef50DB RUNNING) in its own runs dir rather than reusing jaTvne6n outputs; no errors so far. Note for REPORT (check against docs/setup/deployment.rst 'Set up a workflow before its first run').

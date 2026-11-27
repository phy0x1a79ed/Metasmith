# PROGRESS (run 4, fir e2e)
DONE:
- docs read; ssh fir works (login1, phyberos).
- metasmith 0.26.2 installed: envs/msm_env (mamba create). msm binary: envs/msm_env/bin/msm
- GUI running on http://127.0.0.1:8092, project metasmith_ws. pid 3298405 (msm gui). log logs/gui.log
- Agent "prehistoric-fir" deployed via GUI to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir (apptainer, slurm preset, module load apptainer, slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu).
- Workflow "righteous-octopus" = engcyc_prep_references, solved (plan: setup ~860 GB, 19 images, 55 steps).
- Setup run started via GUI "fetch ~860 GB?" button: run key ZfRcWATU (GUI run 7fKLL). Started 09:24 (fir clock).
  - driver: nextflow pid 3474663 on fir login1; relay pid 3436727; run dir /scratch/phyberos/msm_e2e/run-4-fir/runs/ZfRcWATU
  - at 09:28: ~685G in runs/ZfRcWATU/results, 41 trace lines, downloads ongoing (GTDB wget, Metabuli).
  - no sbatch jobs yet.

TODO:
- wait for setup run ZfRcWATU to finish (check GUI Runs tab or fir logs at _metasmith/logs.latest/main.log)
- GUI: engcyc_metagenomics, default targets, SRA SRR9658108 (ncbi::sra_short_read_accession on read_pair row), run on prehistoric-fir
- collect results into ./results (sandbox/results)
- REPORT.md + CONTROL.json

Notes: GUI "set up" needs a second click after label becomes "fetch ~NNN GB?". Background wait task bgnedanj0 (sleep 580) pending.
- 09:39 setup ZfRcWATU still running; GTDB tar downloading (13GB .part), ganon/metabuli downloads active; 40 tasks done, 0 failed
- 09:49 setup still running; GTDB .part 25GB and growing; 22 ref dirs; 40 completed 0 failed
- 09:59 setup still running; GTDB .part 37GB growing; 22 ref dirs; 40 completed 0 failed
- 10:08 setup still running; GTDB .part 48GB (~11GB/10min); 22 ref dirs; 40 completed 0 failed. Full 860GB may take many hours at this rate.
- 10:18 setup still running; GTDB .part 60GB; 22 ref dirs; 40 completed 0 failed
- 10:28 setup still running; GTDB .part 71GB; 22 ref dirs; 40 completed 0 failed
- 10:38 setup still running; GTDB .part 82GB; 22 ref dirs; 40 completed 0 failed
- 10:48 setup still running; GTDB .part 93GB; 22 ref dirs; 40 completed 0 failed
- 10:57 setup still running; GTDB .part 105GB; 22 ref dirs; 40 completed 0 failed
- 11:09 (resume) GUI pid 3298405 alive; fir nextflow java pid 3496831 alive; results 685G; no sbatch jobs; still downloading GTDB/ganon/metabuli. Waiting.
- 11:24 GTDB wget (fir pid 3573278) progressing ~1.3GB/min, now 136GB (partial in container /msm_home, read via /proc/3573278/fd/3). ganon wget loop active. Log 'silent' only because nextflow waits on the download. Waiting.
- 11:34 GTDB ~150GB; Slurm fetch jobs now running (nf-p02__fetch_*, e.g. 6634517 6635270 6635310).
- 11:44 setup alive (nextflow java pid 3496831 on fir); trace 40 completed; ganon/metabuli still downloading (GTDB ~162GB).

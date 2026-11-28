# PROGRESS
## Done
- metasmith 0.26.2 installed: envs/msm_env (mamba create -n msm_env ...). Log logs/install.log.
- GUI running detached on port 8094 from sandbox/metasmith_ws (log logs/gui.log). Pid 1080908 (python, msm gui --port 8094).
- Agent fair-fir deployed via GUI to ssh fir, home /scratch/phyberos/msm_e2e/run-4-fir-lite, apptainer, preset slurm, params slurmAccount/slurmGpuAccount.
- Workflow curvy-bee (engcyc_prep_references_lite) created + solved (84 steps) in GUI.
- Setup run dFzrb (nSaQucfw) COMPLETED (GUI).

## Running
- setup run dFzrb (GUI, agent fair-fir, on fir login1). Check Runs tab.

## Done (prep)
- prep verified (nxf log: Execution complete; 26 reference dirs)

## Next
- Wait for dFzrb to finish (executing/finalizing).
- Create engcyc_metagenomics_lite workflow in GUI, SRA run SRR9658108 on short-read sample, default targets, solve, stage and run on fair-fir (agent must match setup agent).
- Collect results to ./results.
- Write REPORT.md, CONTROL.json.

## Failed so far
- Agent click on "Agents" tab timed out once; second try ok (WORKAROUND).
- First 'set up' click did not start run; second click revealed "fetch ~168 GB?" confirm (GUI behaviour).
- Monitor tool waits spam stale notifications; ignore.

## Metagenomics run (in progress)
- Workflow tangerine-jaguarundi (engcyc_metagenomics_lite): short case only, sample short_1 = sra_short_read_accession SRR9658108; hybrid and long cases removed (no samples). Solved 112 steps.
- Run key ENXTF, task key jVLlTkUU, agent fair-fir, preset slurm, GPU 16 GB. Staging started (GUI).
- Check on fir: /scratch/phyberos/msm_e2e/run-4-fir-lite/runs/jVLlTkUU/
- ENXTF progressing (45 processes submitted by 04:16; no errors).

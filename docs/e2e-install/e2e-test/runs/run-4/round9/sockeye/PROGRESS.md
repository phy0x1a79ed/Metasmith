# PROGRESS
Done:
- metasmith 0.26.2 installed (env msm_env, sandbox/envs). GUI on http://127.0.0.1:8091 (msm pid 3595903; log sandbox/tmp/gui.log; workspace sandbox/metasmith_ws).
- Agent nimble-sockeye deployed to ssh://sockeye:/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye (apptainer, slurm preset, params slurmAccount/slurmGpuAccount).
- Workflow visionary-coucal (engcyc_prep_references_lite) solved, 73 steps.
- Clicked 'set up' -> 'fetch ~162 GB?' confirm. GUI run 9Iflv, task key jaTvne6n, preset slurm, status 'staging' at ~12:06 MST.
Running: setup run jaTvne6n on sockeye (relay login02 at /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye/relay/login02).
Next: wait for setup run to finish (GUI Runs tab / runs status), then create engcyc_metagenomics_lite workflow with SRR9658108 (ncbi::sra_short_read_accession on read_pair row), default targets, solve, stage and run on nimble-sockeye slurm; then collect results to ./results.
Failed: none yet.

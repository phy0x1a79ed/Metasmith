# PROGRESS
DONE: ssh fir verified (login1, phyberos, /scratch/phyberos, accounts def-shallam_cpu/gpu).
RUNNING: mamba create -y -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith
  PID 1180182, log tmp/install.log. Solving/downloading (RSS ~1GB). Repodata warnings for hallamlab file:// .zst are harmless (repodata.json present).
  Wait-watcher: bash task b15ow1w35 (until process exits).
NEXT: activate msm_env (mamba run -n msm_env or $(envs)/msm_env/bin), `msm --version`, `msm gui --help` for port; start GUI on 8092 detached from a workspace dir (sandbox/metasmith_ws); browser to http://127.0.0.1:8092.
FAILED: none yet.
- GUI PID 1182601 on 8092 (log tmp/gui.log), msm_env installed.
- Next: drive GUI in browser: ssh host, agent (home /scratch/phyberos/msm_e2e/run-4-fir), prep refs, metagenomics.
- Agent amorphous-fir deploy started via GUI (in progress). GUI PID 1182601.
- Agent amorphous-fir DEPLOYED (done). Next: engcyc_prep_references via Workflows tab.
- RUNNING: GUI run "jDUaj" (task key 8MiXhcIu), workflow garnet-sloth = engcyc_prep_references, agent amorphous-fir, preset slurm, staging started via GUI "fetch ~861 GB?" at 22:46 MST. GUI view: Runs tab.
- NEXT after prep finishes: create engcyc_metagenomics workflow via GUI (+ workflow, template engcyc_metagenomics), SRR9658108 as ncbi::sra_short_read_accession on read_pair row, solve, stage and run on amorphous-fir slurm, default targets. Then collect results to ./results.
- wait-on-setup: msm workflow wait amorphous-fir 8MiXhcIu, log tmp/wait_setup.log
- wait PID 1189157 (agent yml path form), log tmp/wait_setup.log
- STATUS (latest): setup run 8MiXhcIu (garnet-sloth/engcyc_prep_references) still running on fir; wait PID 1189157 blocked (log tmp/wait_setup.log); background wait bnvoftwf2 for its exit.
- engcyc_metagenomics workflow = GUI workflow "vermilion-hog" (short case, SRA SRR9658108 as short_1 sample, hybrid/long cases removed). SOLVED (199 steps). NOT yet staged; waiting for prep to finish so refs are cached.
- Next: GUI stage-and-run for vermilion-hog on amorphous-fir, preset slurm; then monitor; then collect results to ./results.

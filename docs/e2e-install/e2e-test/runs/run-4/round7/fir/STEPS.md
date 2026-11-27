# STEPS
1. Check conda tooling. cmd: `which mamba; cat ~/.condarc`. Doc: no doc: guess (checked env). Outcome: mamba 2.5.0 at /home/tony/.cache/msm-e2e/bootstrap-env/bin/mamba; condarc envs_dirs and pkgs_dirs point into sandbox.
2. Install metasmith. cmd: `mamba create -y -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith` (background, log install.log). Doc: docs/setup/install.rst section "Installation > Conda".
2. outcome: SUCCESS. mamba create finished, metasmith-0.26.2 installed in env msm_env (log install.log). Note: harness blocks plain `sleep N`; used Monitor until-loops and `timeout ... while pgrep` loop instead.
3. Check GUI options. cmd: `mamba run -n msm_env msm gui --help`. Doc: docs/setup/gui.rst ("Run msm gui --help for the port, the host and the project folder").
4. Start GUI. cmd: `cd metasmith_ws && nohup setsid mamba run -n msm_env msm gui --port 8092 --no-browser > gui.log &`. Doc: docs/setup/gui.rst (start from empty workspace folder; port via `msm gui --help`). Outcome: pending check.
4 outcome: SUCCESS. GUI serving at http://127.0.0.1:8092, project metasmith_ws. gui.log holds output. Detached, pgrep "msm gui --port 8092".
5. Open GUI in browser (mcp__browser__browser_navigate to http://127.0.0.1:8092). Doc: docs/setup/gui.rst.
6. Browser: navigated to http://127.0.0.1:8092; SSH tab lists host fir (fir.computecanada.ca, user phyberos, defined in home/.ssh/config). Doc: docs/setup/gui.rst, docs/setup/ssh.rst. Outcome: OK. (Click on host row via role=button timed out once; clicking the name text worked.)
7. Click Agents tab. Doc: docs/setup/deployment.rst (agent deployment, Source.FromSsh) and gui.rst.
8. Click "+ agent" in Agents tab -> created agent "imperial-local" (local home default). Doc: gui.rst/deployment.rst. Outcome: OK.
9. Checked fir: apptainer 1.3.5 already on PATH (cvmfs), slurm 26.05.4, accounts def-shallam_cpu/def-shallam_gpu present. Doc: deployment.rst "Container Runtime" (apptainer on login). Outcome: runtime apptainer will be used, no setup module needed.
10. Switching agent to "a remote host" tab, host fir, home /scratch/phyberos/msm_e2e/run-4-fir. Doc: deployment.rst "Agents can also be deployed to remote machines through SSH".
11. GUI agent imperial-fir (auto-renamed from imperial-local): host fir, home /scratch/phyberos/msm_e2e/run-4-fir, runtime apptainer, preset slurm, params slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu. Doc: deployment.rst (SLURM section: slurmGpuAccount param) and gui.rst. Outcome: entered via GUI fields; deploy next.
12. Clicked "deploy" in GUI for imperial-fir. Outcome: SUCCESS per GUI log ("deployment complete relay-deployed deployed to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir"; image pulled to sif via apptainer on fir).
13. Click Workflows tab to start engcyc_prep_references. Doc: docs/workflows/engcyc_metagenomics.rst ("Run engcyc_prep_references first, once per agent") and docs/setup/deployment.rst "Set up a workflow before its first run".
14. Workflows > "+ workflow" > template engcyc_prep_references > create -> workflow "righteous-beluga". Doc: docs/workflows/engcyc_metagenomics.rst; deployment.rst "Set up a workflow before its first run". Outcome: OK.
15. Clicked "solve" in plan panel. Outcome: pending.
15 outcome: SUCCESS. Plan solved (55 steps; "setup: ~860 GB of references, 19 images").
16. Selected agent imperial-fir in "stage and run" panel. Doc: gui.rst step 5.
17. Clicked "set up" (setup run for references). Doc: deployment.rst "Set up a workflow before its first run" (setup first, then real run on same agent). Outcome: pending.
17 outcome: first "set up" click did not start a run (nothing in Runs). Second click on set up turned into a "fetch ~860 GB?" confirm button (the docs say the button asks again when size is large). Workflow righteous-beluga has agent imperial-fir and preset slurm with params slurmAccount/slurmGpuAccount.
18. Clicked "fetch ~860 GB?" to confirm the reference setup run (user asked for engcyc_prep_references). Doc: deployment.rst "Set up a workflow before its first run". Outcome: pending.
18 outcome: SUCCESS. GUI started run "righteous-beluga-0KqRy" (route #runs/righteous-beluga/righteous-beluga-0KqRy) = setup run for engcyc_prep_references on imperial-fir.
19. Monitor watching run.yml of setup run (task bf197hw3s). Outcome: state launching at 08:36, staging continued.
20. Created new workflow from template engcyc_metagenomics via "+ workflow" (Doc: docs/workflows/engcyc_metagenomics.rst). Outcome: pending config.
21 ERROR: setup run righteous-beluga-0KqRy (task 5im6f8xT) FAILED at 08:37:06 with "nextflow exited [1]". Cause in fir logs (runs/5im6f8xT/_metasmith/logs.latest/nxf.log, main.log): java.util.ConcurrentModificationException in Orchestrator._closed (Orchestrator.groovy:1407) during orchestration of 24 pending processes; no task was submitted. Looks like an engine race, not a data error. Doc: docs/setup/deployment.rst "Set up a workflow before its first run".
22. Plan: retry the setup run once via GUI ("set up" then "fetch ~860 GB?"). If it fails the same way, report ERROR and stop the setup step.
23. Clicked set up then 'fetch ~860 GB?' again (retry #1). Outcome: pending; check runs.
24. saffron-sturgeon: deleted hybrid and long cases (Doc: engcyc_metagenomics.rst "Delete each read case you have no samples for"). Changed short case read_pair row type to ncbi::sra_short_read_accession and value to SRR9658108 (Doc: engcyc_metagenomics.rst bullet on SRA run). Outcome: OK. Next: delete read rows (read_metadata + read rows) if any, then solve.
25. Fixed type text (first fill concatenated text; cleared with Ctrl+A/Backspace, typed, selected option). Row now ncbi::sra_short_read_accession = SRR9658108. Searches for read_1/read_2 rows found none, so only read_pair row existed to replace. Outcome: OK (screenshot emg_rows2.png). Next: solve.
23 outcome: ERROR. Retry run righteous-beluga-6q5pn (task 5im6f8xT, logs.2026-11-27_08-38-34) FAILED at 08:39:16. nxf.log: java.lang.NullPointerException "Cannot load from object array because this.keys is null" in Orchestrator._closed (Orchestrator.groovy:1407) - same orchestrator close-handler as before. Partial: "8 served from shards", "[8] outputs" written to fir runs/5im6f8xT/results.
26. Solved saffron-sturgeon in GUI (solving completed; check plan). Next: second retry of setup.
27. Retry #2 of setup: set up -> fetch ~860 GB? clicked (run dir will be new). Outcome: pending.

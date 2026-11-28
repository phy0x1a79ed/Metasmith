# STEPS

1. Command: `mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith -y`
   Doc: docs/setup/install.rst, section "Installation > Conda"
2. Installed metasmith 0.26.2 (exit 0). Output in install_metasmith.log
3. Command: `mkdir -p metasmith_ws && cd metasmith_ws && nohup setsid msm gui --port 8094 --no-browser > ../gui.log 2>&1 &`
   Doc: docs/setup/gui.rst "Web GUI" (start from empty workspace folder; msm gui --help for port). Port 8094 from user prompt.
4. Started GUI: nohup setsid msm gui --port 8094 --no-browser (pid 1124347, log gui.log). HTTP 200 at http://127.0.0.1:8094/
5. Browser: navigate http://127.0.0.1:8094/ ; click Agents tab. Doc: docs/setup/gui.rst (GUI); the "fir" host already listed in the GUI hosts panel (from home/.ssh/config).
   Outcome: OK. Note: clicks with stale element refs timed out; re-snapshot before each click (WORKAROUND-ish, browser tooling only).
6. ssh fir 'echo ok; hostname; module avail apptainer 2>&1 | tail -5' (checking connectivity and apptainer module for setup_commands). Doc: docs/setup/deployment.rst 'Container Runtime' & 'remote_agent.rst'. no doc for exact module name: guess
7. GUI: agent 'glittering-fir' created: remote host fir, home /scratch/phyberos/msm_e2e/run-4-fir-lite, runtime apptainer (default), preset slurm, params slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu, setup_commands default. Clicked deploy. Doc: docs/setup/gui.rst; deployment.rst 'SLURM' & 'Container Runtime'. AMBIGUITY: gui.rst does not describe the agent form; fields inferred from UI. WORKAROUND: home textbox needed type() not fill() to commit.
8. Deploy clicked in GUI; log shows 'deployment complete relay-deployed deployed to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir-lit'. OK.
9. GUI Workflows tab > "+ workflow" > template engcyc_prep_references_lite > create (workflow id emerald-grouse). Doc: docs/workflows/engcyc_metagenomics.rst (prep_references bullet) and docs/setup/deployment.rst "Set up a workflow before its first run". Outcome OK.
10. GUI: clicked "solve" on emerald-grouse -> PLAN success, 84 steps, ~168 GB references, 12 images (per GUI). Doc: docs/setup/deployment.rst. Note: the solve button was not discoverable by visual inspection; found via DOM text search (WORKAROUND, browser-only).
11. GUI: stage/run panel: agent=glittering-fir, preset=slurm (agent defaults slurmAccount/slurmGpuAccount inherited). Clicked "set up" (the setup run, per docs deployment.rst "Set up a workflow").
12. GUI: confirm 'fetch ~168 GB?' -> setup run launched. Run N7Gwm, task key aLahF0vo, stage 'staging' on fir (relay at /scratch/phyberos/msm_e2e/run-4-fir-lite/relay/login1). Doc: deployment.rst 'Set up a workflow'.
13. Checked GUI: setup run N7Gwm executing (staging done). Waiting.
14. Setup run N7Gwm executing; on fir Slurm job 6770657 (nf-p84__buildLabelTransferLandmarks, RUNNING). PROGRESS: setup in progress.

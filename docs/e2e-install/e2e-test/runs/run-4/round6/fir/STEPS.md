# STEPS

1. Read PROGRESS.md (empty), STEPS.md (absent). Fresh start.
   no doc: orientation. Read docs/setup/install.rst, docs/setup/gui.rst, docs/setup/deployment.rst, docs/setup/ssh.rst, docs/workflows/engcyc_metagenomics.rst.
   Outcome: install = `mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith` (install.rst, Conda). GUI = `msm gui` from an empty workspace folder, default port 8090, use `--port 8092` (gui.rst says run `msm gui --help` for port; the task says 8092).
2. Checked `ssh fir` with BatchMode: connected to login1 as phyberos, HOME=/home/phyberos. Outcome OK.
   no doc: guess (ssh check). ssh.rst says ssh alias config; the host alias `fir` already exists in home/.ssh/config.
2026-11-27 install: step 3 mamba create
3. Install. Command: mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith -y (install.rst, Conda section). Running detached, log install.log.
4. Start GUI. Command: msm gui --port 8092 --no-browser from sandbox/metasmith_ws (gui.rst: start from empty workspace folder; msm gui --help for port). Detached, log gui.log.
5. Install outcome: metasmith 0.26.2 installed into envs/msm_env (install.log). `msm --help` works.
6. GUI started: msm gui --port 8092 --no-browser, from metasmith_ws. Serving at http://127.0.0.1:8092 (gui.log). I used one curl probe that returned 000 while compiling; not an API step.
7. Browser: opened http://127.0.0.1:8092 via browser tool. Header shows nav Tutorials/SSH/Agents/Data/Workflows/Runs; SSH panel lists host `fir`. Next: Agents tab, deploy agent. Source: gui.rst (GUI steps) and deployment.rst.
8. Browser: Agents tab. The first click on tab timed out (element "not stable"); clicking via selector button[data-tour="tab-agents"] worked. WORKAROUND.
9. Clicked "+ agent" -> created agent neon-local with defaults (this machine, apptainer, local preset). Plan: switch to "a remote host" (fir), home /scratch/phyberos/msm_e2e/run-4-fir, nextflow preset slurm, slurm accounts. Source: deployment.rst (remote agents, SLURM, setup_commands with module load apptainer).
10. Checked fir: `module spider apptainer` lists apptainer/1.5.4 (and 1.4.5, 1.3.5 ...). ssh check found /scratch/phyberos/msm_e2e/run-4-fir ALREADY EXISTS on fir (created 04-37/06-26, with container_images and task_cache dirs) from an earlier attempt. Not created by me; I will not delete it. NOTE for report.
    slurm accounts available: def-shallam_cpu, def-shallam_gpu. Plan setup_commands: module load apptainer/1.5.4 (guess: version choice).
11. GUI agent form (agent renamed neon-fir): host=fir, home=/scratch/phyberos/msm_e2e/run-4-fir, runtime=apptainer (default), image default docker://quay.io/hallamlab/metasmith:0.26.2-e0f658e, preset=slurm, setup commands "#!/bin/bash / module load apptainer/1.5.4" (GUESS on version, from module spider), params slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu (deployment.rst SLURM section names slurmGpuAccount). Source: gui.rst, deployment.rst. Next: click deploy.
12. Clicked deploy in GUI (neon-fir). Log shows: deploying to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir, runtime APPTAINER, pull sif -> build sif -> unpack sandbox. Status "deploying..." at 13:36 UTC.
13. Deploy DONE: log 'deployment complete relay-deployed deployed to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir' (~06:35 fir time). Next: Workflows tab -> engcyc_prep_references setup run. Source: gui.rst steps 1-5, workflows/engcyc_metagenomics.rst (run prep first), deployment.rst 'Set up a workflow before its first run'.
14. GUI: Workflows > + workflow > template engcyc_prep_references > create (workflow misty-wrasse). Source: gui.rst steps 1-3, workflows/engcyc_metagenomics.rst bullet on prep.
15. GUI: clicked solve. Outcome: plan success, 55 steps. Message: "setup: ~860 GB of references, 19 images". (Big; note for quota / disk on fir.)
16. GUI: selected agent neon-fir in run panel, preset slurm (inherited), params inherited. Clicked "set up" -> button changed to "fetch ~860 GB?" -> clicked it to confirm. Run key misty-wrasse-xPO0d. Source: deployment.rst 'Set up a workflow before its first run' (setup run = GUI set up button); user requested prep run.

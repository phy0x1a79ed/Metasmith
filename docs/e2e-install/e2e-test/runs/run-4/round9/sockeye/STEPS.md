# STEPS
1. Read PROGRESS/STEPS (empty, fresh start). Read docs index, setup/*, workflows/engcyc_metagenomics.rst. Checked `ssh sockeye` (BatchMode ok, login02, scratch exists). Outcome: ok.
2. Install: mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith (source: docs/setup/install.rst, Conda section). Running with -y.
3. mamba create succeeded (exit 0), metasmith-0.26.2 linked. Outcome ok.
4. msm gui --help to find port flag (source: docs/setup/gui.rst says run msm gui --help for port, host, project folder).
5. Start GUI: mkdir metasmith_ws; cd metasmith_ws; msm gui --port 8091 --no-browser, detached (source: docs/setup/gui.rst; --port per gui --help). Note: docs say page at 127.0.0.1:8090 default; using 8091 as task asked.
6. GUI up at 127.0.0.1:8091, outcome ok. Next: browser tools.
7. Browser: navigated to http://127.0.0.1:8091 (page loaded; host sockeye already listed in SSH tab). Source: docs/setup/gui.rst. Next: Agents tab to deploy agent.
8. GUI Agents tab -> '+ agent' created agent 'nimble-local' (local defaults). Source: docs/setup/deployment.rst (Agent home / remote via SSH). Switching to 'a remote host' tab next; will rename agent to something sensible later if needed.
9. GUI agent form: host=sockeye, home=/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, runtime apptainer (default), setup commands 'module load gcc/9.4.0 apptainer/1.3.1' (source: docs/setup/deployment.rst Sockeye note). Next: nextflow preset slurm + params slurmAccount/slurmGpuAccount (deployment.rst SLURM section).
10. GUI agent form: nextflow preset=slurm; default params slurmAccount=st-shallam-1, slurmGpuAccount=st-shallam-1-gpu (source: docs/setup/deployment.rst SLURM section: slurmGpuAccount param). Next: click deploy (e185).
11. GUI deploy clicked on agent nimble-sockeye. Outcome: deploy running (log streaming: pull sif -> build sif -no-fragments -> unpack). Waiting.
12. Deploy complete on sockeye (log: 'deployment complete ... deployed to ssh://sockeye:/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye'). Outcome ok. Next: Workflows tab, pick engcyc_prep_references_lite (source: docs/workflows/engcyc_metagenomics.rst; docs/setup/deployment.rst 'Set up a workflow before its first run' -> GUI set up button).
13. Workflows tab -> '+ workflow' -> template engcyc_prep_references_lite -> create. Source: docs/workflows/engcyc_metagenomics.rst (lite variant). Outcome: create clicked after button enabled.
14. Clicked 'solve' in engcyc_prep_references_lite workflow editor (GUI). Source: docs/workflows/engcyc_metagenomics.rst + docs/setup/gui.rst step 4 (Solve). Outcome: pending.
15. solve completed (result.yml success:true, sidebar shows 73 steps). GUI 'nothing can make this' labels were stale. Source: docs/setup/gui.rst step 4 and setup/deployment.rst 'Set up a workflow'. Next: find 'set up' button and run setup for engcyc_prep_references_lite on nimble-sockeye agent.
16. Run panel ('stage and run' section): selected agent nimble-sockeye; preset slurm (source: docs/setup/deployment.rst SLURM + Set up section; '--preset slurm').
17. Clicked 'set up' for engcyc_prep_references_lite on nimble-sockeye, preset slurm (source: docs/setup/deployment.rst 'Set up a workflow before its first run'). Outcome: pending.
18. 'set up' button turned into 'fetch ~162 GB?' (large-download confirm, docs/setup/deployment.rst: 'the button asks again when the size is large'). Clicked confirm. Setup run for engcyc_prep_references_lite now expected (~162 GB download onto sockeye login node per deployment.rst).
19. setup run 9Iflv (task jaTvne6n) staging at 12:06 MST. Next: monitor. Outcome: running.
20. 12:15 setup run jaTvne6n executing on sockeye (nextflow pid 1078553 under login02 driver pgid 1071983). Currently in pullContainer processes (p28 at 12:14). Outcome: running.
21. 12:26 setup run: p35__pullContainer (gtdbtk image) failed once: apptainer build 'conveyor failed to get ... no descriptor found for reference' (ERROR). Nextflow auto-retrying (retry 1). Monitoring; will intervene only if it repeats.
22. 12:45 setup run jaTvne6n: 8 pullContainer tasks running ~30+ min, apptainer build --sandbox on Lustre progressing (container_images 61G). Not hung; slow. Continuing to wait.

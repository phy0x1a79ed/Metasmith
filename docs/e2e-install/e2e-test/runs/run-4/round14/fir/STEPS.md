1. Read docs index, setup/install.rst, setup/gui.rst, setup/deployment.rst, setup/ssh.rst, workflows/engcyc_metagenomics.rst. Checked `ssh fir` -> login1 OK.
2. Command: mamba create -y -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith
   Doc: docs/setup/install.rst, section "Installation > Conda".
3. Command: msm gui (envs/msm_env/bin/msm) in metasmith_ws, --port 8092 --no-browser, detached.
   Doc: docs/setup/gui.rst "Start it from an empty workspace folder". Outcome: serving http://127.0.0.1:8092 (HTTP 200). PID 1356758, log tmp/gui.log.
4. Browser: navigate http://127.0.0.1:8092. Snapshot clicks timed out ("not stable") until viewport set to 1400x900 (browser_resize). Then clicks worked.
   Doc: docs/setup/gui.rst (no specific step for this; WORKAROUND for browser tool).
   Host "fir" listed in SSH tab. Its ProxyCommand is sandbox/.no-fresh-login (script that says "no connection to the cluster; ask the operator to reconnect"). Plain `ssh fir` from bash still works (login1). Watching for this in deploy.
5. Browser: Agents tab > "+ agent" (created draft agent "raspberry-local", local). Plan: switch to "a remote host" = fir, home /scratch/phyberos/msm_e2e/run-4-fir, runtime apptainer, nextflow preset slurm, params slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu, gpuType=h100.
   Doc: docs/setup/deployment.rst (Agents deployed to remote via SSH; SLURM section; GPU gpuType=h100 for fir).
6. Command: ssh fir 'module avail apptainer; which apptainer' (check). Outcome: apptainer 1.3.5 already on PATH via cvmfs; no module load needed. Scratch /scratch/phyberos/msm_e2e exists.
7. Browser: agent raspberry-fir: host=fir, home=/scratch/phyberos/msm_e2e/run-4-fir, runtime apptainer (default), preset slurm, default params slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu, gpuType=h100. Note "+ a param" needed a second click and rows render with delay (GUI quirk).
   Doc: docs/setup/deployment.rst (SLURM section, gpuType=h100 for fir). Setup commands left as default "#!/bin/bash" since apptainer is on PATH.
8. Browser: clicked "deploy" on raspberry-fir. Outcome: log "deployment complete", relay deployed to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir. Status done.
9. Browser: Workflows > "+ workflow" > template engcyc_prep_references > create. Workflow tiny-kakapo created. Outcome: plan shows 175 outputs wanted; many outputs say "nothing can make this — the plan will not solve"; types panel says libraries 6 of 15 (assembly, functionalAnnotation, logistics, metabolicModelling, metagenomics, viromics). Note: browser_snapshot too large for this page (saved to tool-results); use screenshots/browser_find.
   Doc: docs/workflows/engcyc_metagenomics.rst; docs/setup/deployment.rst "Set up a workflow before its first run".
10. Browser: clicked "solve" on tiny-kakapo (default recipe, unchanged). Outcome: plan success, 130 steps; "setup: ~861 GB of references, 20 images". The "nothing can make this" labels were pre-solve and did not block. Doc: docs/workflows/engcyc_metagenomics.rst and docs/setup/gui.rst step 4 (Solve shows plan).
   AMBIGUITY: 861 GB reference download on fir scratch; file quotas (docs/setup/deployment.rst "File quotas") could bite. Watching.
11. Browser: Stage and run panel: agent=raspberry-fir, preset slurm (params inherited from agent). Clicked "set up" -> button became "fetch ~861 GB?"; confirmed.
   Doc: docs/setup/deployment.rst "Set up a workflow before its first run" (set up button; "asks again when the size is large").
12. Browser: clicked "fetch ~861 GB?" (set up). Run tiny-kakapo-2Ja0d, task key a2HZ8JAG, agent raspberry-fir, preset slurm, staging. Outcome: running; monitor in GUI Runs tab.
13. Set-up run staged and now executing on fir (task ekrKC9dy, pgid 4062703, relay at /scratch/phyberos/msm_e2e/run-4-fir/relay/login1). Log notes "run param [gpuType] is read by no transform in this plan... changes nothing" -- harmless for prep (no GPU step). Note as minor.
14. Checked after ~9 min: GUI shows set-up run ekrKC9dy still running (executing). ssh fir squeue: 1 job pending (nf-p122__buildGanon2DB, Priority). Run dir /scratch/phyberos/msm_e2e/run-4-fir/runs/ekrKC9dy exists with PID.lock.
15. ~20 min into set-up ekrKC9dy: local task p106__downloadMetabuliDB running; slurm jobs running (buildGanon2DB, bakta_noncoding, semibin2, metadecoder, promotech, clean/rgi/bacmet/mobileog/vfdb pending). Set-up in progress.
16. ~29 min: set-up ekrKC9dy still running on fir; ~40 slurm jobs queued/running (psortm, interproscan, promotech, clean ...). No errors seen yet.
17. ~38 min: set-up ekrKC9dy queue down to 9 jobs; nxf.log shows COMPLETED cached tasks; no failure found (grep hits were debug noise).
18. ~47 min: set-up queue down to 4 running (promotech, clean, bakta_noncoding, buildGanon2DB). pgid 4062703 still alive.
19. [resume 03:05 MST] GUI PID 1356758 alive (HTTP 200). fir: 4 slurm jobs running (promot, clean, bakta, buildGanon2DB); pgid 4062703 alive at 55 min. Set-up still running. Waiting.
20. [03:15 MST] set-up still running: same 4 slurm jobs (promotech 46m, clean 44m, bakta 47m, buildGanon2DB 55m). pgid alive 65m.
21. [03:24 MST] still running, same 4 slurm jobs (buildGanon2DB 64m). pgid alive 74m.
22. [03:33 MST] still running, same 4 slurm jobs (buildGanon2DB 73m). pgid alive 83m.
23. [03:43 MST] progressing: slurm jobs write logs (ganon2 build, metabuli). Four jobs still RUNNING at 1h+. pgid alive 92m.
24. [03:53] bakta_noncoding finished (gone from queue). 3 slurm jobs running (promotech, clean, buildGanon2DB). pgid alive 102m.
25. [04:02] 4 slurm jobs running (promotech, clean, buildGanon2DB, buildMetabuliDB new). pgid alive 112m.
26. [04:11] still 4 slurm jobs running; pgid alive 120m.
27. [04:20] promotech done; 3 slurm jobs running (clean, buildMetabuliDB, buildGanon2DB). pgid alive 130m.
28. [04:29] 3 slurm jobs running (clean, buildMetabuliDB, buildGanon2DB). pgid alive 139m.
29. [04:38] still 3 slurm jobs running; pgid alive 148m.
30. [04:47] still 3 slurm jobs running; pgid alive 157m.
31. [04:56] still 3 slurm jobs running; pgid alive 166m.
32. [05:05] 2 slurm jobs running (clean, buildGanon2DB); buildMetabuliDB finished. pgid alive 175m.
33. [05:14] 2 slurm jobs running (clean, buildGanon2DB); pgid alive 184m.
34. [05:23] 1 slurm job running (clean). pgid alive 193m.
35. [05:35] set-up run 2Ja0d (task ekrKC9dy) FAILED in GUI: 'ignored step(s): p122__buildGanon2DB (1)' exit 1 at 05:24. Investigating logs.
36. Diagnosis of 2Ja0d failure. Job p122__buildGanon2DB (fir slurm 6826532, dir nxf_work/30/a960...) was OOM-killed (exit 137, oom_kill event, --mem 65536M) during `raptor build` after 3h. Doc: none covers CPU memory for this step (docs only have python resource_overrides in tutorials/custom_transforms.rst).
   ERROR: shipped slurm preset (envs/msm_env/.../nextflow_config/slurm.nf:127) errorStrategy uses `params.process.tries`, but `tries = 3` is set inside `process {}`, not `params.process`, so retry never happens and the step is 'ignored', failing the run.
37. WORKAROUND plan: add run param process_tries=3 (bootstrap.py ~line 587 maps process_X -> params.process.X) on agent raspberry-fir in GUI (Agents tab), then rerun set up. Completed steps are cached. Retry doubles memory on exit 137 (slurm.nf/workflow.resources.nf closure).
38. [05:40] Redeployed agent raspberry-fir with process_tries=3 (GUI Agents tab, param added, deploy clicked, completed). Re-solved tiny-kakapo, selected agent raspberry-fir, clicked set up -> confirmed 'fetch ~861 GB?'. Doc: setup/deployment.rst 'Set up a workflow before its first run'. WORKAROUND per step 36-37. Outcome: pending; check Runs tab.
39. [05:41] PROGRESS.md updated. Set-up run #2 is tiny-kakapo-7KRoz (started via GUI).
40. [05:43] run #2 7KRoz staging (params include process_tries=3), reusing ekrKC9dy cache. Waiting.
41. [05:46] set-up run #2 7KRoz RUNNING (executing) on task ekrKC9dy, process_tries=3 in params. WARNING from engine: lfs file quota 862,199/1,000,000 used on /scratch; 128-step run may hit limit and die mid-step. Doc: setup/deployment.rst 'File quotas' (free files under agent home or ask admins). Investigating usage.
42. [05:51] set-up run #2 (7KRoz, task ekrKC9dy) executing on fir (driver pid 3687706). Background watcher b1cq1bys5 waits for driver exit. Quota: project /scratch files 1.39M total; my run-4-fir 699k (nxf_work 449k, task_cache 190k). Not deleting while run active. Other home run-4-fir-lite (267k files, ufzXt67u, not mine) left alone.

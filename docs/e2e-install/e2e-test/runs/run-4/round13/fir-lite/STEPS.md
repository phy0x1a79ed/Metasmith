# STEPS

1. Read PROGRESS.md (empty), STEPS.md (absent), no prior logs. Fresh start.
   Command: ls / cat state files. Doc: no doc (session setup).
2. Read docs: setup/install.rst, setup/gui.rst, setup/deployment.rst, setup/ssh.rst, workflows/engcyc_metagenomics.rst.
   Command: cat docs/setup/*.rst docs/workflows/*.rst. Doc: docs/ (all). Outcome: install via `mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith`; GUI via `msm gui` (default 127.0.0.1:8090; `msm gui --help` for port); deploy via GUI; ssh config via ~/.ssh/config.
   Note: docs say GUI runs on 8090 by default; the task asks for 8094 -> will use `msm gui --help` to find port flag (docs/setup/gui.rst: "Run msm gui --help for the port").
3. Test `ssh fir` using sandbox ssh config (home/.ssh/config). Command: ssh -F home/.ssh/config -o BatchMode=yes fir true. Doc: docs/setup/ssh.rst (general ssh setup); no doc for the sandbox stub.
4. ssh fir check: `ssh -o BatchMode=yes fir 'hostname'` -> login1 OK. Cluster home /home/phyberos, /scratch/phyberos/msm_e2e exists, accounts def-shallam_cpu and def-shallam_gpu present, apptainer 1.3.5 via module path. Doc: docs/setup/ssh.rst (general), docs/setup/deployment.rst (apptainer on cluster via setup_commands).
   Note: sandbox home/.ssh/config has a ProxyCommand stub (.no-fresh-login) that always fails, but ssh still succeeded (likely a live ControlPath master). Not a problem so far.
5. Install metasmith: `mamba create -y -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith` (detached, log logs/install.log). Doc: docs/setup/install.rst "Conda" section. mamba found on PATH (2.5.0), CONDARC env already set to sandbox/home/.condarc (envs_dirs in sandbox/envs).
   Outcome: OK. metasmith-0.26.2 installed into sandbox/envs/msm_env. Log: logs/install.log. Warnings about hallamlab .zst repodata were non-fatal (fell back to .json).
   Note: I used a shell Monitor with `pgrep -f` that matched itself; replaced with PID wait. Not a project issue.
6. Check GUI options: `envs/msm_env/bin/msm gui --help` (no port flag yet). Doc: docs/setup/gui.rst ("Run msm gui --help for the port, the host and the project folder").
7. Start GUI: `cd metasmith_ws && msm gui --port 8094 --no-browser` detached (log logs/gui.log). Doc: docs/setup/gui.rst ("Start it from an empty workspace folder", "msm gui --help" for port). Note: --no-browser since no desktop browser; I'll open it with the browser tool. Bound to loopback (default).
8. Browser: navigate http://127.0.0.1:8094 via browser tools. Doc: docs/setup/gui.rst. Outcome: page loads, shows hosts list with `fir` (from ssh config), nav: Tutorials, SSH, Agents, Data, Workflows, Runs.
9. Click Agents tab to deploy agent. Doc: docs/setup/gui.rst (steps: ssh host, agent, data, plan, run, results); docs/setup/deployment.rst.
10. WORKAROUND: browser clicks timed out ("waiting for element to be visible, enabled and stable") and screenshot timed out right after first load. Reloading the page and waiting 3s fixed it. Not a doc issue.
11. Clicked Agents tab. Outcome: OK, URL #agents.
12. Agent form: created agent (auto-named lush-fir), set "a remote host" -> host fir, home /scratch/phyberos/msm_e2e/run-4-fir-lite, runtime apptainer (default), nextflow preset slurm. Doc: docs/setup/deployment.rst (Agents, SLURM), docs/setup/gui.rst. Outcome OK.
13. Default params: "+ a param" click did not add a visible row on first clicks; second click made a row. Filled slurmAccount=def-shallam_cpu. Then clicking "+ a param" again added no row (AMBIGUITY: unclear when rows appear).
14. ERROR (my mistake): clicked "remove this param" instead of blurring the field; removed slurmAccount row. Re-adding.
15. Added params via "+ a param": slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu, gpuType=h100 (gpuType per docs/setup/deployment.rst "fir" note). Doc: docs/setup/deployment.rst (SLURM section). Verified rows in GUI snapshot (rows re-ordered on re-render, values intact).
16. Clicked "deploy" in GUI (agent lush-fir). Log shows "starting ssh to [fir]". Waiting for deployed state.
17. Deploy OUTCOME: OK. Log "deployment complete relay-deployed deployed to [ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir-lite]". Agent state deployed.
18. Next: Workflows tab -> engcyc_prep_references_lite -> set up on agent lush-fir. Doc: docs/setup/gui.rst; docs/setup/deployment.rst "Set up a workflow before its first run".
19. Workflows tab -> "+ workflow" -> template engcyc_prep_references_lite -> create. Outcome: workflow tentacled-mussel created (GUI "not solved" state). Note: "create" button was disabled for a few seconds after template choice; waited 3s then clicked. Doc: docs/setup/gui.rst (steps 1-5), docs/workflows/engcyc_metagenomics.rst (prep references note).
20. Browser: workflow tentacled-mussel shows 4 inputs (template defaults) and 121 output targets. Clicking "solve" (doc: docs/setup/gui.rst step 4 "Solve"). Note: the GUI page snapshots are very large; used browser_find and screenshots instead.
21. Solve OUTCOME: plan success, 84 steps, "setup: ~168 GB of references, 12 images". Some env outputs (sylph.env, vibrant.env, etc.) show "nothing can make this" but plan still succeeded via pulled_container. AMBIGUITY: GUI label vs. plan success; accepted since plan says success.
22. Stage and run panel: agent=lush-fir, preset=slurm; params inherited from agent defaults. Clicking "set up" (doc: docs/setup/deployment.rst "Set up a workflow before its first run": "In the web GUI the same action is the workflow's set up button").
23. Clicked "set up" -> GUI asked "fetch ~168 GB?" -> confirmed. Outcome: navigated to run tentacled-mussel/tentacled-mussel-G591v (Runs tab). Doc: docs/setup/deployment.rst "Set up a workflow before its first run".
24. Checked cluster read-only (ssh fir ls/squeue/ps) to find the run's nextflow log. Outcome: runs/U3QhuEEA/_metasmith/logs.2026-11-28_01-00-04/nxf.log is the driver log. Note: a different phyberos run (ekrKC9dy, run-4-fir home) is also active; left alone.
25. Setup run status: staging done, executing (GUI shows running). Log warning: "run param [gpuType] is read by no transform in this plan... changes nothing; check its spelling". Harmless for prep (no GPU step); noting as GUESS-free observation.
26. Workflows -> "+ workflow" -> template engcyc_metagenomics_lite -> create. Outcome: workflow loud-woodlouse, cases short/hybrid/long/references. Doc: docs/workflows/engcyc_metagenomics.rst (case deletion, SRA accession, lite template).
27. Plan: delete hybrid and long cases (no samples, per engcyc_metagenomics.rst bullet 1); in short case change read_pair row type to ncbi::sra_short_read_accession, value SRR9658108, delete its two read rows (per engcyc_metagenomics.rst bullet 4). Keep references case with default targets.
28. Deleted hybrid and long cases (remove case x2). Outcome: cases now short + references.
29. Short case: read_pair row type set to ncbi::sra_short_read_accession and value SRR9658108. GUI issues: browser_type "fill" appends to the type box (produced junk type "sequences::read_pairncbi::..." and a junk parent on a read row); fixed by clearing with Ctrl+A/Backspace, typing slowly, picking option "ncbi sra_short_read_accession". WORKAROUND. Doc: docs/workflows/engcyc_metagenomics.rst (SRA accession bullet).
30. Deleting the two file read rows (zipped_reverse_short_reads and forward). Doc: engcyc_metagenomics.rst bullet 4 ("delete its two read rows").
31. Deleted both file read rows (click once -> ✓, click again to confirm). Outcome: short case inputs = sample_name short_1, read_metadata, SRA row SRR9658108; 44 outputs wanted.
32. Clicked solve (selector button:text-is("solve")). Solving in progress.
33. Solve OUTCOME: success, 112 steps, setup ~168 GB refs, 45 images. Next: check prep run finished before stage and run of metagenomics.
34. PREP RUN OUTCOME (verified on fir): nxf log "Execution complete", succeededCount=28 failed=0; runs/U3QhuEEA/results/references has 28 ref-/annotation- dirs; agent task_cache is 220G. Note: most steps show _cached names; references present. Treat setup as DONE.
35. Stage and run for loud-woodlouse: GUI asked GPU memory (GB); placeholder 16 ("largest ask"). Entered 16 (judgment: docs say enter memory of one GPU, field starts at largest ask; fir H100 has more than 16 GB). Clicked stage and run. Outcome: run YRjXN staging (task key ufzXt67u). GUI shows prep run G591v as "completed".
36. Metagenomics run ufzXt67u executing on fir (Slurm jobs submitted from 01:08). Polling.

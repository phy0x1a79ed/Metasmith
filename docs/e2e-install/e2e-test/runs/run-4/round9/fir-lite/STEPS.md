1. COMMAND: mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith -y  (run detached, log: logs/install.log)
   DOC: docs/setup/install.rst, section "Conda" (also prerequisite: Linux x86_64 OK)
   NOTE: mamba already configured (home/.condarc) so envs/pkgs stay in sandbox; no change needed.
   OUTCOME: OK. metasmith v0.26.2 installed at envs/msm_env (bin/msm). Mamba install log logs/install.log.
2. COMMAND: msm gui --help   (checking port/host/project-folder flags)
   DOC: docs/setup/gui.rst "Web GUI" ("Run msm gui --help for the port, the host and the project folder")
   OUTCOME: flags are --port/--host/--project/--no-browser. Note --no-browser chosen (headless host).
3. COMMAND: cd metasmith_ws && nohup setsid msm gui --port 8094 --no-browser > logs/gui.log &
   DOC: docs/setup/gui.rst "Web GUI" steps 1-2 (mkdir metasmith_ws; cd; msm gui); port 8094 from task brief
   OUTCOME 1: ERROR. Served transform compile then "E| PackageNotFoundError: No package metadata was found for werkzeug" and exited. werkzeug 3.1.9 IS installed (metadata resolves from env python); cause unknown.
   OUTCOME 2: foreground rerun (timeout 90) served OK at http://127.0.0.1:8094 with no error (logs/gui_fg.log). Retrying detached.
4. COMMAND: browser navigate to http://127.0.0.1:8094 (mcp__browser__browser_navigate)
   DOC: docs/setup/gui.rst "Web GUI" ("The page opens at http://127.0.0.1:8090"; we use 8094 per brief)
5. COMMAND (GUI): Agents tab -> "+ agent" (created default agent axiomatic-local, local). Next: switch to "a remote host", fir, home /scratch/phyberos/msm_e2e/run-4-fir-lite, runtime apptainer, preset slurm, params slurmAccount/slurmGpuAccount, setup_commands module load apptainer
   DOC: docs/setup/gui.rst; docs/setup/deployment.rst "Agents can also be deployed to remote machines", "SLURM", "Container Runtime"; tutorials/remote_agent.rst
   NOTE: Agents tab click via text timed out once; data-tour selector worked.
6. GUI: remote host = fir (agent auto-renamed axiomatic-fir); home = /scratch/phyberos/msm_e2e/run-4-fir-lite; nextflow preset = slurm; runtime apptainer (default)
   DOC: docs/setup/deployment.rst "SLURM" and "Container Runtime"
7. GUI: default params slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu. Setup commands left default (#!/bin/bash) since `which apptainer` on fir already resolves to 1.3.5 (checked via ssh fir: no-doc check, not an API call).
8. GUI: click "deploy" on axiomatic-fir
   OUTCOME: deploy clicked at ~20:17 UTC; button shows "deploying..." (in progress). Waiting.
9. OUTCOME (deploy): OK. GUI log logs/gui.log: "deployed to [ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir-lite]" at 13:17:27 (local time). No error.
10. GUI: click "ping" on axiomatic-fir
11. OUTCOME (ping): OK, green check on axiomatic-fir.
12. GUI: Workflows tab
13. GUI: Workflows > "+ workflow" > template engcyc_prep_references_lite > create
   DOC: docs/workflows/engcyc_metagenomics.rst (engcyc_prep_references* run first, once per agent); docs/setup/deployment.rst "Set up a workflow before its first run"
14. GUI: workflow brass-mayfly created from engcyc_prep_references_lite (inputs prefilled by template). Clicking "solve" (planner).
   DOC: docs/setup/gui.rst step 4 ("Solve. The GUI shows the plan as a graph of steps.")
15. OUTCOME (solve): plan success, 73 steps, "setup: ~162 GB of references, 11 images". Visual "nothing can make this" lines were stale.
16. GUI: run panel agent=axiomatic-fir, preset=slurm, params slurmAccount/slurmGpuAccount auto-filled from agent defaults. Clicking "set up" (setup run for prep references; no samples).
   DOC: docs/setup/deployment.rst "Set up a workflow before its first run"; docs/workflows/engcyc_metagenomics.rst bullet on engcyc_prep_references
17. GUI: "set up" button asked "fetch ~162 GB?" -> confirmed (user requested the setup run). Clicking confirm.
   OUTCOME: setup run started in GUI. run "lrLku", task key jaTvne6n, status staging -> "starting ssh to [fir]". Monitoring in Runs tab.
18. OUTCOME (monitoring): run jaTvne6n in GUI status "launching"/staging; relay started on fir (login1, PID 3870983); context sent; staging entries. No SLURM jobs yet at 13:2x. Monitor armed on logs/gui.log.
19. OUTCOME: stage/run triggered on fir: "triggering execution of [jaTvne6n]" at 13:20:18; run token jaTvne6n.2026-11-27_13-20-18, pgid 3954935 (login1). Executing nextflow driver.
20. OUTCOME: remote nextflow (logs.latest/main.log) shows jobs submitted to SLURM (buildMnxrLookup etc.); pullContainer retried once. Monitor b1pvzzgfg polls remote main.log.
21. GUI: Workflows tab, to create engcyc_metagenomics_lite workflow (while setup runs). DOC: docs/workflows/engcyc_metagenomics.rst
22. GUI: created workflow courageous-mandrill from engcyc_metagenomics_lite. Cases: short, hybrid, long, references. Plan: remove hybrid and long (no samples), keep short (SRA accession SRR9658108) and references; leave default targets.
   DOC: docs/workflows/engcyc_metagenomics.rst bullets 1 (delete read cases with no samples; keep references) and 3 (SRA run: change read_pair row type to ncbi::sra_short_read_accession, put run, delete the two read rows)
23. GUI: removed "hybrid" and "long" cases (no samples). Remaining: short, references.
24. GUI: short case: discarding "zipped_forward_short_reads" and "zipped_reverse_short_reads" rows (per engcyc_metagenomics.rst: delete the two read rows). Then read_pair row -> type ncbi::sra_short_read_accession, value SRR9658108.
25. GUI: short case: both read rows discarded (two-step confirm each). read_pair row type set to ncbi::sra_short_read_accession, value SRR9658108. (Note: an early discard click armed/cleared via the x button; verified final rows: sample_name, read_metadata, sra row. No other rows removed.)
26. GUI: clicking solve for courageous-mandrill
27. OUTCOME: setup run jaTvne6n healthy on fir: nextflow driver PID 3962775 (log _metasmith/logs.2026-11-27_13-20-18/nxf.log); SLURM job 6652695 p72__buildMnxrLookup RUNNING; downloadSwissProt COMPLETED. NOTE: login1 also runs other users'/other runs' nextflow (rP9w0ycI, PID 996336) — NOT ours, do not touch.
28. OUTCOME: courageous-mandrill solve: success, 91 steps, setup ~162 GB refs, 42 images. Run NOT started yet — waiting for setup run jaTvne6n to finish (same agent cache).
29. WORKAROUND: wrote watcher script to the wrong place (outside sandbox) by mistake; moved it to sandbox/scripts/watch_setup.sh and removed the outside copy. Started detached: nohup setsid bash scripts/watch_setup.sh > logs/watch_setup.log (polls remote nxf.log every 5 min; prints SETUP_DONE or SETUP_ERROR).
30. OUTCOME: waiting. Setup run progressing (watcher scripts/watch_setup.sh -> logs/watch_setup.log; background wait bobnss3yb).
[17:08] Setup run finished (SETUP_DONE). Verified nxf log 'Workflow completed', all tasks exit 0. Starting courageous-mandrill via GUI.
[17:09] GUI: clicked stage and run for courageous-mandrill (agent axiomatic-fir picked via select, slurm preset). OUTCOME: run l6Ly2 staging, task key nxsA1XR2.

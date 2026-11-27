# STEPS

1. Read PROMPT.md, PROGRESS.md (empty), STEPS.md (new). Read docs/setup/install.rst, gui.rst, deployment.rst, ssh.rst, workflows/engcyc_metagenomics.rst.
   Source: task instructions. Outcome: docs read. Note: docs/setup/ssh.rst says ~/.ssh/config; the sandbox has home/.ssh/config (HOME is sandbox/home).
   Also noticed sandbox/.no-fresh-login: an ssh stub that says "no connection to the cluster; ask the operator to reconnect" -- to verify with ssh sockeye.
2. Command: mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith -y  (source: docs/setup/install.rst, 'Conda' section)
3. Installed metasmith 0.26.2 (exit 0). Log: tmp/install.log. Binary: envs/msm_env/bin/msm
4. Started GUI: cd metasmith_ws; nohup setsid envs/msm_env/bin/msm gui --port 8091 --no-browser (source: docs/setup/gui.rst). Log: tmp/gui.log
5. First GUI start (with bootstrap) crashed during stdlib compile: "E| PackageNotFoundError: No package metadata was found for werkzeug" (tmp/gui.log). ERROR. werkzeug 3.1.9 dist-info exists in the env; importlib.metadata finds it directly.
6. WORKAROUND: foreground run with --no-bootstrap served at 127.0.0.1:8091 (tmp/gui2.log). Restarted detached with `msm gui --port 8091 --no-browser --no-bootstrap` (tmp/gui.log). Stdlib was already copied in step 5. Doc gap: gui.rst says the first start copies tutorials/stdlib; no mention of this error (docs/setup/gui.rst).
7. ssh sockeye: BatchMode connect OK (login02). Config: home/.ssh/config. (ProxyCommand .no-fresh-login did not block).
8. Loading browser tools; next: navigate http://127.0.0.1:8091 (docs/setup/gui.rst).
9. GUI open in browser at 8091; sockeye host already listed in GUI hosts panel. Clicked Agents tab (docs/setup/gui.rst; docs/setup/deployment.rst).
10. Agents tab > + agent (created 'enlightened-local' draft). Set 'a remote host' tab, host sockeye, home /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, apptainer runtime, slurm preset (docs/setup/deployment.rst: SLURM, module load gcc/9.4.0 apptainer/1.3.1; docs/workflows/engcyc_metagenomics.rst).
11. Agent 'enlightened-sockeye' configured via GUI: remote host sockeye, home /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, apptainer, slurm preset, setup commands 'module load gcc/9.4.0 apptainer/1.3.1' (deployment.rst note). '+ a param' click showed no visible row (GUI quirk, to revisit); slurm accounts to be supplied at run time. Clicked deploy.
12. Deploy via GUI succeeded: log says 'deployment complete relay-deployed deployed to ssh://sockeye:/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye' (GUI agent log). Took ~3 min. Note: the 'deployed' label is always visible in the progress bar; read the log panel for status.
13. Workflows tab > + workflow > template engcyc_prep_references_lite > create (docs/workflows/engcyc_metagenomics.rst; docs/setup/deployment.rst 'Set up a workflow before its first run').
14. Clicked solve on brass-barracuda (engcyc_prep_references_lite) (docs/workflows/engcyc_metagenomics.rst; GUI docs/setup/gui.rst steps 3-4). Note: snapshots of this page are very large (type lists); prefer screenshots.
15. Plan solved: success, 27 steps, 'setup: ~162 GB of references, 10 images'. Run panel: agent=enlightened-sockeye, preset=slurm, param slurmAccount=st-shallam-1 (GUI '+ a param' in run panel; docs/setup/deployment.rst SLURM).
16. Run panel params: slurmAccount=st-shallam-1, slurmGpuAccount=st-shallam-1-gpu; agent enlightened-sockeye; preset slurm. Clicked 'set up' (setup run for engcyc_prep_references_lite; deployment.rst 'Set up a workflow before its first run'; ~162 GB download).
17. Clicked 'set up' -> button turned into 'fetch ~162 GB?' confirm (GUI asks for large downloads); clicked to confirm the reference setup run (user asked for setup). Verify in Runs tab.
18. Setup run lk5ck (task pU61olfk) staging via GUI; monitoring tmp/gui.log for completion/errors.
19. Setup run is executing: GUI run lk5ck, engine task key ShUeUoct (run dir /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye/runs/ShUeUoct). Staged 08:30 local; state 'running' (executing) at ~08:33.
20. Setup run ShUeUoct (GUI lk5ck) COMPLETED: nxf.log workflow completed succeededCount=28 failedCount=0. results/references has 19 DB dirs (ref-gtdb, ref-kraken2_db, annotation-bakta_db, ...). Observation: scratch task_cache is 571G (may include pre-existing caches; not verified as this run's download only).
21. Workflows > + workflow > template engcyc_metagenomics_lite > create (docs/workflows/engcyc_metagenomics.rst).
22. In impartial-badger 'short' case, read_pair row type -> ncbi::sra_short_read_accession (combobox typing; see docs/workflows/engcyc_metagenomics.rst). Next: set SRR9658108 value, delete the two read rows, delete hybrid/long cases.
23. Set the sra row value (textbox originally 'hybrid_1') to SRR9658108 in impartial-badger. Caution: the DOM holds several cases; visible rows verified by screenshot. Next: delete the zipped_forward/zipped_reverse read rows in the short case.
24. Read rows delete: discard button is two-step (× then ✓ confirm). Clicking zipped_reverse discard (e3510) twice; then zipped_forward (e3542). Use find with maxResults small to avoid huge output.
25. Deleted hybrid and long cases (remove case button); cases now short + references. Short case: sra row SRR9658108, zipped read rows deleted. Next: solve.
26. Solved impartial-badger (engcyc_metagenomics_lite): success, 82 steps, setup ~162 GB / 38 images. Next: run panel params (slurmAccount st-shallam-1, slurmGpuAccount st-shallam-1-gpu), agent enlightened-sockeye, preset slurm; set up then stage and run.
27. Run panel for impartial-badger: params slurmAccount/slurmGpuAccount set; agent enlightened-sockeye; GPU memory field set to 16 (GUESS: plan's largest GPU ask is 16 GB per GUI placeholder; I don't know sockeye's GPU memory; docs/setup/gui.rst step 5 and docs/setup/deployment.rst 'GPU').
28. Run buttons (stage and run/set up) stayed disabled after setting params/agent/GPU. Suspect two empty file rows (/data/sample_01.fastq.gz placeholder, no value) in the short case. Discarding them (two-step: click x then ✓).
29. WARNING: my discard clicks removed the sra row holding SRR9658108 (SRR no longer in DOM). Re-creating it on the remaining read_pair row (value short_1): type -> ncbi::sra_short_read_accession, value -> SRR9658108. Also removed empty zipped_reverse/zipped_forward/long_reads file rows.
30. Re-created SRR9658108 sra row (type sra_short_read_accession). Next: re-solve (inputs changed), then check run buttons.
31. Re-solve OK (success, 82 steps, 39 images). Run buttons enabled. Clicking 'set up' for impartial-badger (metagenomics_lite) per docs/setup/deployment.rst. Then confirm the fetch button.
32. Confirmed 'fetch ~162 GB?' for impartial-badger setup run (references already staged by prep run; expect faster).
33. impartial-badger setup run ka5fw (engine IRSOPdtt) executing since ~08:48.
34. ERROR: setup run ka5fw (engine IRSOPdtt) failed: nextflow.extension NullPointerException "Cannot load from object array because this.keys is null" in Orchestrator._closed, after 39 pullContainer tasks stayed pending (0 succeeded). Log: runs/IRSOPdtt/_metasmith/logs.2026-11-27_08-48-52/nxf.log on sockeye. GUI still displayed 'running' (stale).
35. Retrying setup once via GUI (set up -> fetch confirm).
36. Retry of setup run confirmed via GUI (new run).
37. Navigating to the workflow dropped the run params; re-added slurmAccount/slurmGpuAccount (the first retry failed at launch with 'slurmAccount is <slurm_account>'). Clicked set up + confirm fetch again (retry 2). Note for REPORT: params do not persist across page reloads in the run panel.
38. Retry run qcqi7 launched (reusing staged runs/IRSOPdtt; same engine dir, may hit same failure).

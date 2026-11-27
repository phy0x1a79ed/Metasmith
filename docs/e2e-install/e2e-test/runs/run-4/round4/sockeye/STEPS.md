# STEPS

1. Command: `mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith -y` (detached, log logs/install.log)
   Doc: docs/setup/install.rst, section "Installation > Conda".
- Install OK: metasmith 0.26.2 in envs/msm_env (log logs/install.log)
   Outcome: success. Transaction finished, metasmith-0.26.2. hallamlab local channel warnings (no repodata) were harmless.
2. Command: mkdir metasmith_ws && cd metasmith_ws && nohup setsid msm gui --port 8091 --no-browser (env msm_env), log logs/gui.log
   Doc: docs/setup/gui.rst ('Start it from an empty workspace folder'); port 8091 per task, flags per 'msm gui --help'.
3. Command: mamba run -n msm_env msm gui --port 8091 --no-browser -> process exited after compile with 'E| PackageNotFoundError: No package metadata was found for werkzeug' (logs/gui.log line 68)
   Outcome: ERROR. Werkzeug 3.1.9 is installed in envs/msm_env. Suspect 'mamba run' env handling; retrying with envs/msm_env/bin/msm directly (same as docs' 'activate then msm gui').
   Outcome: GUI serving at http://127.0.0.1:8091 (PID 2718304). Next: browser.
4. Browser: navigate http://127.0.0.1:8091 (GUI). Doc: docs/setup/gui.rst. Outcome: page loads; SSH tab lists host 'sockeye' (sockeye.arc.ubc.ca). Next: Agents tab.
5. Browser: Agents tab -> '+ agent' (created 'interesting-local' default). Outcome: form shown. Next: set remote host sockeye, home path, runtime, setup modules (docs/setup/deployment.rst: 'module load gcc/9.4.0 apptainer/1.3.1' on Sockeye), slurm preset with slurmAccount st-shallam-1.
6. Browser: agent 'interesting-sockeye' configured: remote host sockeye, home /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, runtime apptainer (default), preset slurm, default param slurmAccount=st-shallam-1, setup commands 'module load gcc/9.4.0 apptainer/1.3.1' (docs/setup/deployment.rst Sockeye note). Outcome: form saved ('all changes saved'). Next: deploy.
7. Browser: deploy button on agent interesting-sockeye. Outcome: SUCCESS, log 'deployment complete relay-deployed deployed to ssh://sockeye:/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye' (agent log state 'done'). Next: Workflows tab, find engcyc_prep_references_lite. NOTE docs only name engcyc_prep_references / engcyc_metagenomics (no _lite) -> AMBIGUITY, verify in GUI template list.
8. Browser: Workflows > '+ workflow' > template engcyc_prep_references_lite (in GUI list, confirming _lite names) > create -> workflow 'perfect-alligator' (default 20 outputs, no samples). Outcome: created. Next: solve.
9. Browser: solve on perfect-alligator -> PLAN success, 27 steps, 'setup: ~162 GB of references, 10 images' (doc: docs/setup/deployment.rst 'Set up a workflow before its first run'). Then selected agent interesting-sockeye, preset slurm, param slurmAccount=st-shallam-1 (inherited). Clicking 'set up' (doc: setup run, first step before real run).
10. Browser: 'set up' on perfect-alligator -> confirm 'fetch ~162 GB?' -> setup run started, run id UnyqV, task key pU61olfk, state staging (logs/setup_run.png). Next: monitor in Runs tab; then recreate or reuse workflow for engcyc_metagenomics_lite.
11. Monitoring setup run via Monitor (squeue on sockeye every 45s). Cluster: agent home /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye has container_images, lib, msm, relay, runs, task_cache. Run UnyqV in GUI reached 'launching', staging ~ workflow sent (logs/setup_run.png).
12. Monitor event 22:37:33: Slurm job 14221258 nf-p35__buildRefseqViralDB_(1) PENDING. Setup run UnyqV proceeding (first compute job submitted).
13. 22:38 monitor: queue empty. sacct: buildRefseqViralDB 14212018/14221258, buildMnxrLookup, buildLabelTransferLan, buildGtdbDB, buildKofamDB COMPLETED. Note: rescue jobs 14208732/14208733 TIMEOUT (3h) exist on txyliu, not submitted by this run (earlier attempt?) -> noted, not touched. GUI run UnyqV still 'running'.
14. Monitor b09inqt8n expired (7 events). Re-armed as bszairm5n. Status 22:52: GUI UnyqV running; sacct 14221359 buildMnxrLookup RUNNING 3:41.
15. 22:46 queue empty; sacct 14221359 buildMnxrLookup COMPLETED 7:30. GUI UnyqV still running. Run dir runs/ShUeUoct has results/ and _metasmith/.
16. 23:11 queue empty; sacct 14221544 buildLabelTransferLandmarks COMPLETED 21:52. GUI UnyqV running. Remaining setup steps pending.
17. 23:23 queue empty for 10+ min is expected: driver is running local login-node download step downloadGtdbDB (task c8/c0baf4..., ~90% at ~22MB/s, actively writing). Not stuck. Nothing killed.
18. 23:33 downloadGtdbDB finished exit 0 (1.75GB part saved). Driver should next submit Slurm jobs.
19. 00:30 buildKofamDB 14222168 COMPLETED (51:22, exit 0). Queue empty. Browser page was about:blank; re-navigating to run UnyqV to read state.
20. 00:41 queue empty; Slurm: buildKofamDB done 00:30. Local login-node download still running (task 51/6a32ae..., 54%, ~1 MB/s, ETA ~1h40m, writing as of 00:40). Expected slow, not stuck. Waiting.
21. 00:52 monitor silent (expected; download running). Replaced with background wait that exits when a Slurm job appears for txyliu (logs/wait_job.log).
22. 00:51 resume: checked GUI alive, Slurm queue empty, sacct shows GTDB/Kofam completed. Next: check browser state of run UnyqV.
23. 00:52 browser: run UnyqV page shows 'running', run log empty; checking agent log on sockeye.
24. 00:52 wait for UniRef50 wget (5.7GB so far). Sleeping 540s.
25. 00:5x check: UniRef50 part size + queue (see output)
26. 00:55 started background waiter (logs/wait_job2.log) that exits when a Slurm job appears for txyliu. UniRef50 wget still running (5.8GB @00:54).
27. 00:5x Monitor bsajc3kpj expired with no events (no Slurm job yet). Checking download + queue.
28. 01:1x Monitor bx5q84e9v expired, no Slurm job yet. Checking.
29. 01:2x Monitor bu2oglvg1 expired, no Slurm job. Checking.
30. 01:3x Monitor bmnmis37a expired, no Slurm job. Checking.
31. 01:4x Monitor bdxfdh91b expired, no Slurm job. Checking.
32. 01:5x Monitor b132dxpsc expired, no Slurm job. Checking.
33. 01:55 uniref50.fasta.gz download complete (9.18GB); finalizing mv in progress. Driver moving on. Queue still empty.
34. 01:57 Slurm job appeared on queue (monitor b6xov96px). Checking which job.
35. 02:0x Monitor b34uvd7hw expired; checking jobs.
36. 02:11 queue empty; buildUniRef50DB finished (checking sacct).
37. 02:2x Monitor bpyeur76p expired, no new Slurm job. Checking.
38. 02:3x Monitor b0gjtuyu3 expired, no Slurm job. Checking.
39. 02:4x Monitor b39cv9dyq expired, no Slurm job. VirSorter2 setup still running locally.
40. 02:5x Monitor bzmebo2nb expired, no Slurm job. Checking.
41. 02:52 10 Slurm jobs named 'rescue' RUNNING (14229317-26) on txyliu. Checking origin (not in my run's logs so far).
42. 02:53 'rescue' jobs 14229317-26 are from /scratch/st-shallam-1/txyliu/rescue/sockeye.sbatch, NOT from this run's runs/ShUeUoct. Not my jobs; not touching them. Note for REPORT.
43. 03:0x Monitor bsaudat40 expired. Checking run state.
44. 03:02 VirSorter2 setup process gone; execute_transform step 26 (downloadVirsorter2DB) still running in driver. No setup-run Slurm jobs queued.
45. 03:1x Monitor btanqdy07 expired, no setup job. Checking.
46. 03:2x Monitor b3filllme expired, no setup job. Checking.
47. 03:20 setup run completed per agent log ('run completed at 2026-11-27_03-20-23'). Verifying in GUI.
48. 03:2x GUI: run UnyqV status 'completed' (finished 03:20). Next: Workflows > + workflow > engcyc_metagenomics_lite. Setup run results are references, not needed in ./results.
49. 03:2x GUI: Workflows > + workflow > template engcyc_metagenomics_lite > create -> workflow 'ancient-cricket' (no doc: GUI, docs/workflows/engcyc_metagenomics.rst). Next: solve.
50. 03:3x read docs/setup/gui.rst steps (template, samples, deselect targets, solve, run) and setup/deployment.rst (setup run must use same agent+task). Note: metagenomics workflow ancient-cricket is a different task from perfect-alligator; refs may not hit cache -> GUESS to flag. Next: add SRR9658108 sample via GUI.
51. 03:4x GUI: ancient-cricket samples: 'paste' takes CSV 'sample,forward,reverse' (file paths/URLs). No SRA input type visible in GUI. GUESS: use ENA FASTQ URLs for SRR9658108. Checking ENA filereport (outside GUI; allowed).
52. 03:5x GUI: pasted sample CSV (sample,forward,reverse; ENA https FASTQ URLs for SRR9658108, PAIRED per ENA filereport) into ancient-cricket short case -> 'peek pasted 1 row x 3 col'. Next: map input columns (18 rows) on short case, then solve.
53. 03:5x solve #1 -> 'no plan' (solver could not find a complete plan). Template spec (envs/.../vendor/templates/engcyc_metagenomics/spec.yml, read as WORKAROUND to learn case rules; GUI description says 'Delete a case you have no samples for' and 'keep references case'). Plan: remove hybrid and long cases in GUI, map short case sample columns (forward/reverse/sample_name), re-solve.
54. 04:0x GUI: removed hybrid and long cases; short case mapped (sample_name->sample, zipped_reverse->reverse, zipped_forward->forward, 2nd sample_name->sample; shared clicks on constant rows uncertain). Re-solve clicked ('solve again').
55. 04:1x GUI: sheet paste replaced literal value boxes with column selectors; constant rows (media, medium_name, contig_study, eggnog_source, read_metadata) register nothing -> solver says 'no given input matches'. Investigating file-mode for constants (WORKAROUND needed).
56. 04:2x Stopping GUI mapping: constant inputs (medium table, medium_name, contig_study JSON, eggnog JSON, read_metadata) need literal values or file uploads; literal fields disappeared after the sample sheet was pasted. Metagenomics solve still 'no plan'. Writing REPORT/PROGRESS; not running the metagenomics workflow.

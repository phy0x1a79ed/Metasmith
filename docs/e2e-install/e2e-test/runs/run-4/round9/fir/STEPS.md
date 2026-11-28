# STEPS
1. Command: `mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith -y`. Doc: docs/setup/install.rst, section "Installation > Conda".
2. Result: exit 0, metasmith-0.26.2 linked into envs/msm_env. Output in install.log.
3. Command: `cd metasmith_ws && nohup setsid envs/msm_env/bin/msm gui --port 8092 --no-browser > gui.log 2>&1 &`. Doc: docs/setup/gui.rst ("Start it from an empty workspace folder") and `msm gui --help` for --port. Port 8092 per task (docs default is 8090). Outcome: running, PID 3594911, log gui.log. Note: pgrep also showed another run's GUI on 8091 (not mine, not touched).
4. Browser (mcp__browser playwright): navigate http://127.0.0.1:8092 -> GUI loaded, host `fir` already listed under SSH hosts. No doc: GUI navigation (docs/setup/gui.rst).
5. Browser: Agents tab -> '+ agent' created default local agent 'artichoke-local' (home ~/msm.*, runtime apptainer, preset local). Doc: docs/setup/deployment.rst. Will switch to remote host fir.
6. Browser: agent artichoke-local -> 'a remote host' tab, host=fir, home=/scratch/phyberos/msm_e2e/run-4-fir, preset=slurm. Doc: docs/setup/deployment.rst (Agents remote via SSH; SLURM preset). Checked on fir (ssh): apptainer module available (apptainer/1.3.5, 1.4.5 etc.), `which apptainer` resolves on login shell; so setup command planned: `module load apptainer` (GUESS: default version).
7. Browser: agent artichoke-fir (GUI auto-renamed from artichoke-local): default params slurmAccount=def-shallam_cpu, slurmGpuAccount=def-shallam_gpu; setup commands "#!/bin/bash\nmodule load apptainer" (GUESS: default apptainer module version). Doc: docs/setup/deployment.rst (setup_commands module load; SLURM params docs/setup/deployment.rst "SLURM" section incl. slurmGpuAccount).
8. Browser: click 'deploy' on artichoke-fir.
9. Outcome: deploy OK. gui.log: "deployment complete", "deployed to [ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir]". Binds show /scratch/phyberos/msm_e2e/run-4-fir mounted as /msm_home.
10. Browser: Workflows -> '+ workflow' -> template engcyc_prep_references -> create (workflow 'lime-waxbill'; 4 input rows: media, medium_name, contig study, eggnog release; no samples). Doc: docs/workflows/engcyc_metagenomics.rst (prep first). AMBIGUITY: workflow auto-named; template name not visible in header, verified by dropdown only.
11. Browser: click 'solve' (plan). 
12. Outcome: solved, 120 steps (library 0.26.2). 
13. Browser: agent=artichoke-fir, preset=slurm, params slurmAccount/slurmGpuAccount carried over. Clicked 'set up' -> GUI asked "fetch ~860 GB?" (docs/setup/deployment.rst "Set up a workflow before its first run": GUI asks again when size is large). Confirmed it (user requested the setup run). NOTE: ~860 GB onto fir scratch; file quota may matter (docs: File quotas).
14. Outcome: setup run started; GUI route #runs/lime-waxbill%2Flime-waxbill-WqS4V.
15. Outcome: run page shows staging, task key sgYnCPSD.
16. Outcome: run executing (pgid 978412, started 12:08:04). Monitor on fir pgid started.
17. Armed Monitor bztgh5cas on background watcher b5yo0019o (ends when pgid 978412 gone). Meanwhile building engcyc_metagenomics workflow in GUI (docs/workflows/engcyc_metagenomics.rst: SRA via ncbi::sra_short_read_accession on read_pair row, delete unused read cases).
18. Browser: created workflow 'colorful-starling' from template engcyc_metagenomics. Removed hybrid and long cases (no samples; doc: docs/workflows/engcyc_metagenomics.rst "Delete each read case you have no samples for"). Kept short + references. In short case: read_pair row type -> ncbi::sra_short_read_accession, value SRR9658108; deleted zipped_forward/zipped_reverse_short_reads rows. WORKAROUND: first JS-click on discard buttons did not remove rows (red check appeared); deleted via Playwright click on discard button index. Outputs: 68 wanted.
19. Outcome: engcyc_metagenomics solved, 176 steps (colorful-starling).
20. Check 12:19: prep pgid 978412 alive (6 procs); GUI log last staging line 12:11 (no new lines); fir login load high (ssh slow). Still waiting.
21. Background ssh check bdyus6hx7 (hung on login load) was stopped by harness; not the run itself. Prep run still alive as of 12:22.
22. 12:43 check: prep run ACTIVE on fir: nextflow executing step under /msm_home/runs/rP9w0ycI/nxf_work/f0/abedc039e1a0e774671c9090330295 (java pid 996336, apptainer). GUI log not updated since 12:11 (GUI log only shows staging).
23. 13:51 tick: prep run still active (pgid 978412 alive, 48 nxf_work dirs). Latest task dirs modified 12:16-12:13 per listing; no obvious stall but no clear progress since ~12:17 either. Investigating not yet conclusive; heartbeat continues.
24. Watcher b5yo0019o was killed by harness time limit; re-arming a new watcher on pgid 978412.
25. 14:29 tick: prep run ACTIVE: step f0/abedc039 is a ganon DB build, log still growing (14:29:15). nxf_work count 48 unchanged because the step is long-running, not stalled. Also seen on the same agent home: another run jaTvne6n (not started by me).
26. 15:56 tick (resumed after restart): GUI pid 3594911 alive, log last line 15:36 W "probe failed for run [lime-waxbill/lime-waxbill-WqS4V]: run 1 out of range (1..0)". Prep run rP9w0ycI java pid 996336 still alive on fir (ganon step). Another agent's runs (m3WECrQg, jaTvne6n, run-4-fir-lite) share fir; not mine, not touched.
26. Watcher b60x6ezhx stopped by harness time limit at ~16:33; re-arming new watcher.
16:39 tick: setup run executing; buildMetabuliDB done; ganon still running.
27. Watcher b0jc2e5kq stopped by harness time limit (~30 min). Re-arming.
28. Watcher bdl0zt3b1 stopped by time limit.
29. Watcher bvpyh7qdp stopped by time limit.
30. Watcher bc4btjqk2 stopped by time limit.
31. 18:39: prep run alive; active step f0/abedc039 = downloadGanon2DB staging; downloads succeeded (last write 18:13), no error found in .command.err (error strings are set -e trace lines). Quiet since 18:13, likely in a long build.
18:46 tick: ganon mv in IO wait, still running; no action.
32. Watcher bv3o8imr2 stopped by time limit; re-arming.
33. Watcher birhkr4yf stopped by time limit.
34. 19:40 diagnosis: ganon step (step_index=15, downloadGanon2DB staging) is in a cross-mount 'mv' of the ganon download files dir from task_cache into the workspace (copy over Lustre), process in I/O wait, copying GCF_029983095 etc. Not crashed; slow I/O-bound copy. No error in logs. Expected to take a long time. Stopped my find probe b4wvxjfge (too slow).
35. 19:57 resume. Probing ganon mv I/O rate on fir (ssh, bg b3z1mfu97; first probe hit 120s timeout).
36. 20:01 probe: /proc/2777246/io rchar sampled 30s apart => ~18 MB/s. Measuring source size in background (du on fir, log /tmp/ganon_du.txt).
37. 20:10 Monitor bcjhav9nu waiting for /tmp/ganon_du.txt. No other action possible until ganon copy ends.
38. 20:12 monitor bcjhav9nu expired silently; re-armed as bw1ollakw (pid exit watch). du source size still pending.
35. 20:13 tick: prep run alive; ganon mv (pid 2777246) still running in I/O wait, elapsed ~2h. Not intervening (killing a mv could corrupt the cache). Heartbeat.
39. 20:52 ganon copy finished (mv exited); prep still running. Re-armed exit watch.
40. 21:12 status check: prep alive, ganon step post-mv; no error seen. Watch bo2qenmih.
36. 21:15: ganon step (f0/abedc039) FINISHED exit 0 at 21:05; nxf_work now 50 task dirs; prep run pgid 978412 still alive. Re-arming completion watcher.

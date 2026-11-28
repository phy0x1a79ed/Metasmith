# PROGRESS
- DONE: metasmith 0.26.2 installed in envs/msm_env (install.log).
- RUNNING: msm GUI on http://127.0.0.1:8092, PID 3594911, log gui.log, workspace metasmith_ws/.
- DONE: agent artichoke-fir deployed to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir (slurm preset, module load apptainer setup).
- RUNNING: engcyc_prep_references setup run, GUI run WqS4V (lime-waxbill), task key rP9w0ycI, pgid 978412, java pid 996336 on fir, started 12:08. Active at 15:56: downloadGanon2DB (local) + slurm buildMetabuliDB job 6706536. Nextflow log: /scratch/phyberos/msm_e2e/run-4-fir/runs/rP9w0ycI/_metasmith/logs.2026-11-27_12-08-04/nxf.log
- GUI glitch: run log/steps panels empty; gui.log 15:36 "probe failed ... run 1 out of range (1..0)". Real run is fine; only GUI view stale. Not restarting GUI yet.
- NEXT: when prep finishes, GUI run WqS4V -> results. Then engcyc_metagenomics workflow 'colorful-starling' (solved, 176 steps) on agent artichoke-fir, slurm params, run on SRR9658108.
- Other agents' runs on fir (m3WECrQg, jaTvne6n, run-4-fir-lite) are not mine; do not touch.
- watcher: prep_watch.log gets PREP_PROCESS_ENDED when java 996336 exits (started 15:57)
- 16:39: buildMetabuliDB (slurm 6706536) finished OK (1h17m). ganon download still running. NF pid 996336 alive.
- 18:46: ganon step (f0/abedc039) in a long mv of files/ dir (pid 2777246, 32min, IO-wait). Not dead. Nextflow still alive. Watching.
- 19:29: ganon mv (pid 2777246) progressing ~14MB/s, ~64GB copied so far (cross-fs copy). Slow, not stuck.
- 19:40 prep run in ganon staging mv (slow Lustre copy). Heartbeat only.
- 19:57 resume: GUI pid 3594911 alive; prep pid 996336 alive; ganon mv pid 2777246 (state I) 1h43m. Measuring copy rate (ssh probe b3z1mfu97, output in /tmp/claude-1001/.../tasks/b3z1mfu97.output).
- 20:01 copy rate ~18 MB/s (rchar 96.4GB cumulative at 20:00). Checking source size (bg).
20:10 status: prep run alive (ganon copy ~18MB/s, ~100GB+ copied). Waiting on source-size result (/tmp/ganon_du.txt). Next: when prep finishes, GUI run WqS4V results, then metagenomics colorful-starling run via GUI.
20:12 ganon copy ~20MB/s, rchar 109GB. du of source still not returned (ganon_du.txt empty). Monitor bw1ollakw watches prep java pid 996336 exit (poll every 9 min).
20:52 ganon mv pid 2777246 exited (copy done). Prep pid 996336 still ALIVE, Nextflow step f0/abedc039 running post-copy. Watch buk06uytc.
- 20:52: downloadGanon2DB reported SUCCESS (20:44). Prep run rP9w0ycI still alive (NF pid 996336); continuing remaining steps.
21:12 prep pid 996336 alive; ganon step dir has only staging subdir 1-1-1.* (mv done 20:44). Watch bo2qenmih re-armed.
- 21:15 ganon step done (exit 0). prep run continuing.

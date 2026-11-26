# STEPS
1. mamba create -n msm_env -c hallamlab -c bioconda metasmith  | source: docs/setup/install.rst, section 'Installation > Conda'
2. msm --help (look for GUI launch) | no doc: guess-free; docs contain no GUI launch command (grep gui/serve/port found none in docs/)
3. nohup setsid msm gui --port 8091 --no-browser > gui.log  | source: no doc (docs have no GUI launch); GUESS from 'msm --help'/'msm gui --help'. Labelled GUESS/AMBIGUITY
4. ssh -o ConnectTimeout=20 sockeye hostname  | source: setup/ssh.rst (test connectivity) + setup/deployment.rst
5. ssh sockeye check OK (login02, txyliu). scratch path exists. | source: setup/ssh.rst, setup/deployment.rst. NOTE: ssh works via existing ControlMaster socket; .no-fresh-login ProxyCommand stub would block a fresh connection
6. GUI: click Agents tab, look at sockeye host | source: user task; GUI found via snapshot (no doc)
7. GUI: + agent -> created draft 'primitive-local' (local, apparently auto-created on this machine at sandbox/home/msm.HK2LUUU9; leave or delete later). Switching location to 'a remote host' | source: setup/deployment.rst 'Deploying agents' (remote via SSH)
8. GUI agent form: host=sockeye, home=/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, preset=slurm, setup_commands='module load gcc/9.4.0 apptainer/1.3.1' | source: setup/deployment.rst 'Additional setup commands' + Sockeye note; slurm preset: setup/deployment.rst 'SLURM'
9. GUI: default param slurmAccount=st-shallam-1 | source: setup/deployment.rst 'SLURM' (slurmAccount param) + task text
10. GUI: click 'deploy' on primitive-sockeye | source: setup/deployment.rst 'Deploying agents' (deploy via SSH); user task
11. observed: GUI param row name 'slurmAccount' was only a placeholder; GUI says '[st-shallam-1] has no param name, so it is not saved'. ERROR/WORKAROUND: must type name explicitly. Will fix after deploy completes | source: setup/deployment.rst 'SLURM' params
12. GUI deploy completed: 'deployment complete relay-deployed deployed to ssh://sockeye:/scratch/...'. Now re-adding param slurmAccount explicitly | source: GUI
13. GUI: param slurmAccount=st-shallam-1 saved; ping -> 'reachable, ok login02' | source: GUI; setup/deployment.rst 'SLURM'
14. GUI Workflows > + workflow > template engcyc_prep_references_lite (template list in GUI; docs say engcyc_prep_references, the _lite variant is in the GUI list) | source: workflows/engcyc_metagenomics.rst + setup/deployment.rst 'Set up a workflow before its first run'. AMBIGUITY: docs name engcyc_prep_references (no _lite); used the _lite name the task asks for
15. GUI: workflow delectable-heron created from engcyc_prep_references_lite; clicked 'solve' | source: GUI; setup/deployment.rst 'Set up a workflow before its first run' (set up button in GUI)
16. GUI: solve OK ('setup: ~162 GB of references, 10 images', 27 steps). Selecting agent primitive-sockeye in run panel | source: GUI
17. GUI: clicked 'set up' (preset slurm, agent primitive-sockeye, slurmAccount param) | source: setup/deployment.rst 'Set up a workflow before its first run' (button asks again when size is large)
18. set up clicked (earlier 3 clicks had no effect; the 4th showed inline confirm 'fetch ~162 GB?'). Confirmed it (user asked for prep references; docs: setup asks again when size is large) | source: setup/deployment.rst 'Set up a workflow before its first run'
19. set up + confirm 'fetch ~162 GB?' via in-page click sequence (confirm reverts after a few seconds) | source: setup/deployment.rst 'Set up a workflow before its first run'
20. checked: setup run appears in GUI at #runs/delectable-heron%2Fdelectable-heron-ZDVb2
21. setup run staging on cluster (rsync into runs/drvPib87, relay running). Waiting via Monitor until-loop | source: setup/deployment.rst 'Set up a workflow'
22. Monitor bbdkjqp3p armed: polls cluster for active procs (rsync/nextflow/relay) every 30s
23. setup run is ACTIVE on cluster (driver PID 2078146, java 2079866, nxf tasks running; 15G container_images). Earlier wait ended at 60min cap with broad pgrep match (49). Now waiting on driver PID 2078146 | source: GUI run delectable-heron-ZDVb2
24. setup run drvPib87 FINISHED WITH FAILURE: 4 ignored failed steps (downloadGtdbRrna, downloadVirsorter2DB, downloadVibrantDB, downloadUniRef50DB) and p09__pullContainer (1) failed -> run failed at 15:50 | source: runs/drvPib87/_metasmith/logs.latest/main.log
25. Diagnosis of drvPib87 failures (cluster logs):
   - downloadGtdbRrna x2 and downloadUniRef50DB/Vibrant aborted: apptainer 'mount source /ws/1-1-1.<hash> doesn't exist' (WORKAROUND-candidate: transient bind/workdir issue; no fix applied)
   - downloadVirsorter2DB: snakemake conda creation failure inside container (virsorter setup-retry.smk, CRITICAL) - not a mount issue
   - p09__pullContainer was RUNNING when driver was killed ("Killing running tasks (3)"); ERROR attributed to it
   source: runs/drvPib87/_metasmith/logs.latest/{main.log,nxf.log}, nxf_work/*/.command.err | doc: setup/deployment.rst 'Downloads run on the login node' (resume from partial download on rerun)
26. Plan: retry 'set up' once from GUI (same agent, same task o8AJkrYB), per docs failed downloads resume on rerun
27. GUI retry of set up launched: run key delectable-heron-05RpS (agent reselected via select change after reload; set up + confirm). | source: setup/deployment.rst 'Set up a workflow'
28. background wait bg5zl6ikg: waits for retry driver (key drvPib87) to appear and exit

# STEPS

1. Read PROMPT.md, PROGRESS.md (empty), STEPS.md (absent): fresh start. Read docs/setup/{install,gui,ssh,deployment}.rst.
   Source: no doc (orientation). Outcome: docs say GUI defaults to port 8090; `msm gui --help` lists port option.
2. Test cluster access: `ssh -o BatchMode=yes fir hostname`. Source: docs/setup/ssh.rst (ssh config). Outcome: see entry 3.
- ssh fir works (hostname=login1)
3. Outcome: `ssh -o BatchMode=yes fir hostname` -> login1, exit 0. (ProxyCommand .no-fresh-login did not block it; ControlMaster/live connection apparently in use.)
4. Install per docs/setup/install.rst "Conda": `mamba create -n msm_env -c conda-forge -c bioconda -c hallamlab metasmith`. Source: docs/setup/install.rst, section Installation > Conda.
5. Outcome: mamba install ok; msm v0.26.2 at sandbox/envs/msm_env/bin/msm.
6. Start GUI per docs/setup/gui.rst ("Start it from an empty workspace folder... start from same folder each time"; `msm gui --help` for port). Command: `cd sandbox/metasmith_ws && nohup setsid msm gui --port 8094 --no-browser > sandbox/tmp/gui.log 2>&1 &`. Source: docs/setup/gui.rst; port flag from `msm gui --help`.
7. Outcome: GUI serving at http://127.0.0.1:8094 (HTTP 200), project = sandbox/metasmith_ws. Log: tmp/gui.log. Pid 641552 (may be the setsid wrapper; check with pgrep -f "msm gui").
8. Next: drive the GUI with mcp__browser__ tools (Playwright MCP, from .browser-mcp.json). No doc: guess (PROMPT says use browser tools).
9. Browser: navigate to http://127.0.0.1:8094 (no doc: guess; docs/setup/gui.rst says page opens at 8090 by default, we used --port 8094).
10. Browser: clicked "Agents" tab in GUI nav. Source: GUI UI; docs/setup/gui.rst lists steps ssh host, agent, data, plan, run.
11. Browser: Agents tab (click via [data-tour="tab-agents"]; plain ref click timed out, WORKAROUND). Outcome: "no agents yet".
12. Browser: click "+ agent" to create an agent. Source: docs/setup/deployment.rst (Deploying agents) and docs/setup/gui.rst.
13. Outcome: GUI auto-created local agent "precious-local" (home sandbox/home/msm.TD7ehxc8, apptainer, local preset). Not the wanted agent; will use the "a remote host" tab for fir instead. Local agent left in place (harmless, GUI-created). Note: GUI auto-creates agent on "+ agent".
14. Browser: click "a remote host" tab. Source: GUI; docs/setup/deployment.rst "Agents can also be deployed to remote machines through SSH by changing their home."
15. Remote check on fir (no doc: guess, to choose runtime): `which apptainer` -> /cvmfs/.../apptainer/1.3.5/bin/apptainer (on login PATH, no module load needed); /scratch/phyberos/msm_e2e exists; slurm accounts include def-shallam_cpu, def-shallam_gpu. Scratch file count 965534 used (files quota unknown).
16. Browser: set agent host=fir (select). Next: home=/scratch/phyberos/msm_e2e/run-4-fir-lite, runtime=apptainer (default), preset=slurm on run.
17. Browser: agent renamed automatically to precious-fir; home=/scratch/phyberos/msm_e2e/run-4-fir-lite; preset=slurm. Source: docs/setup/deployment.rst (SLURM preset, slurmAccount param) and PROMPT. The local agent is no longer listed.
18. Browser: default param slurmAccount=def-shallam_cpu (docs/setup/deployment.rst SLURM; PROMPT). Adding slurmGpuAccount=def-shallam_gpu next (docs: "Set the slurmGpuAccount param when GPU jobs bill a different account").
19. Browser: param rows: name slurmAccount=def-shallam_cpu; name slurmGpuAccount=def-shallam_gpu (GUI showed "has no param name, so it is not saved" until names were typed). Source: docs/setup/deployment.rst SLURM section.
20. Browser: clicked "deploy" on agent precious-fir. Source: docs/setup/gui.rst step 5 / docs/setup/deployment.rst (Deploying agents). Form: host fir, home /scratch/phyberos/msm_e2e/run-4-fir-lite, apptainer, slurm preset, params slurmAccount/slurmGpuAccount.
21. Outcome: deploy in progress, GUI log shows staging to fir and sif build (pull -> build -999 -no-fragments -> unpack). Waiting.
22. Outcome: deploy DONE. GUI log: "deployment complete relay-deployed deployed to [ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir-lite]". Built via apptainer -no-fragments path.
23. Browser: open Workflows tab to find engcyc_prep_references_lite. Source: docs/setup/gui.rst (template list) and docs/workflows/engcyc_metagenomics.rst.
24. Browser: Workflows tab (no workflows yet). Clicking "+ workflow" to pick a template. Source: docs/setup/gui.rst step 1 ("Pick a template").
25. Browser: template select = engcyc_prep_references_lite (combobox). Create button was disabled briefly, then enabled. Clicking "create". Source: docs/setup/gui.rst; docs/setup/deployment.rst "Set up a workflow before its first run".
26. Outcome: workflow created at #workflows/interesting-cassowary from template engcyc_prep_references_lite (screenshot tmp/workflow_page.png). Inputs prefilled; 121 outputs wanted. Full snapshot too large (113k chars) -> WORKAROUND: use screenshots + small targeted snapshots.
27. Browser: scroll to find the solve/plan and setup buttons. Source: docs/setup/gui.rst steps 3-4 (deselect targets, Solve).
28. Browser: scrolling did not work; located "solve" button via page button list (WORKAROUND: evaluate listing button labels, used only to find elements). Clicking "solve". Source: docs/setup/gui.rst step 4 ("Solve. The GUI shows the plan as a graph of steps.").
29. Outcome: solve succeeded: 84 steps; PLAN "success", setup ~168 GB of references, 12 images. Buttons present: solve again, stage and run, set up, environments only.
30. Browser: click "set up" (docs/setup/deployment.rst "Set up a workflow before its first run": setup run downloads references on the agent before the real run).
31. Outcome of set up click: button disabled until an agent is chosen (WORKAROUND: scrolled to panel "STAGE AND RUN").
32. Browser: stage-and-run panel: agent=precious-fir, preset=slurm. Source: docs/setup/gui.rst step 5 and docs/setup/deployment.rst SLURM section.
33. Browser: params slurmAccount/slurmGpuAccount auto-filled from agent defaults; clicking "set up" (docs/setup/deployment.rst "Set up a workflow before its first run": `workflow setup` then `wait`, then real run on the same agent).
34. Outcome: "set up" changed to "fetch ~168 GB?" (size confirmation per docs/setup/deployment.rst: "the button asks again when the size is large"). Confirming: user asked for prep references, so this is the authorized step.
35. Outcome: setup run started in GUI: Runs > 9hZcR, task key ggoTKczc, agent precious-fir, preset slurm, staging over ssh to fir. Pulls 12 images and downloads ~168 GB (downloadTcdbDB, downloadPredictfDB, ...).
36. Remote: run dir on fir = /scratch/phyberos/msm_e2e/run-4-fir-lite/runs/ggoTKczc; trace at _metasmith/trace.jsonl (session_start seen). Armed Monitor on that trace for failures/completion (no doc: guess for the trace path; found via ls).
37. Outcome: setup run ggoTKczc running on fir (nextflow started; trace has session_start only at 17:59 local). Started background poll (up to 2 h) for session_end/run_end/task_end.
38. Browser: while setup runs, creating second workflow from template engcyc_metagenomics_lite (docs/workflows/engcyc_metagenomics.rst: "Pick it in the GUI"; SRA: change read_pair row type to ncbi::sra_short_read_accession, put run, delete the two read rows).
39. Browser: template dialog set to engcyc_metagenomics_lite (one select was set via DOM script, then verified visually), clicking "create". Note: a DOM-level select set was used once; WORKAROUND, outcome verified by screenshot.
40. Outcome: workflow radical-magpie created (template engcyc_metagenomics_lite). Cases: short, hybrid, long, references. Working on SRA: docs/workflows/engcyc_metagenomics.rst bullet "To start a short-read sample from an SRA run...". Attempting read_pair type row click (screenshot tmp/wf2_readpair.png).
41. Browser: short-case sample (snapshot tmp/wf2_snapshot.yml). Setting its read_pair row type (e11525) to ncbi::sra_short_read_accession. Source: docs/workflows/engcyc_metagenomics.rst SRA bullet. Next: value -> SRR9658108, discard the two zipped_*_short_reads rows.
42. Outcome: type-ahead combobox appended text instead of replacing ("sequences::read_pairncbi::sra_short_read_accession", no match). Clearing it with Ctrl+A + Backspace, then retyping. WORKAROUND.
43. Outcome: type set to ncbi::sra_short_read_accession (screenshot tmp/wf2_type.png). Setting its value textbox (e11515) to SRR9658108. Source: docs/workflows/engcyc_metagenomics.rst ("put the run in it").
44. Outcome: value now SRR9658108 (screenshot tmp/wf2_acc.png). Discarding the zipped_reverse_short_reads row (e11549) per docs "delete its two read rows".
45. Outcome: first click on the row's discard button only armed it (× became ✓). WORKAROUND: clicking ✓ to confirm discard of zipped_reverse_short_reads row. Then do the same for zipped_forward_short_reads.
46. Outcome: reverse zipped row discarded. Forward zipped row armed then confirmed with the same two-click pattern. Next: remove hybrid and long cases with no samples (docs: "Delete each read case you have no samples for").
47. Browser: selecting "hybrid" case tab to remove it (no samples; docs/workflows/engcyc_metagenomics.rst "Delete each read case you have no samples for"). Then "remove case". Long case after.
48. Outcome: hybrid case removed (no confirm). Removing long case next (same button).
49. Outcome: long case removed. Cases now: short (SRR9658108 as ncbi::sra_short_read_accession, zipped rows removed) and references. Clicking solve on radical-magpie.
50. Outcome: radical-magpie (engcyc_metagenomics_lite, SRR9658108 short case, references case) SOLVED: 112 steps, plan success, setup ~168 GB refs, 45 images. Screenshot tmp/wf2_solved.png.
51. Remote: setup run ggoTKczc still downloading references (results/references populated with annotation-*, ref-* dirs). nextflow java + squashfuse mounts seen. Background poll br64mpxyt active (2 h).
52. Outcome: references at 216 GB on fir, 23 entries under results/references (download continuing). Background poll on RUN.pgid started (exits when run process group is gone).
53. Outcome: setup run ggoTKczc EXITED cleanly; main.log "run completed" at 19:46; 0 failures/errors in logs.latest; 26 reference dirs, 219G. Next: real run radical-magpie via GUI stage and run.
54. Browser: reloaded GUI (navigate to root then Workflows tab). radical-magpie present, SRR9658108 persisted. Stage-and-run panel: agent=precious-fir, preset=slurm, params slurmAccount/slurmGpuAccount, GPU memory 16 GB (pre-filled, plan's largest GPU ask). Clicked "stage and run". Source: docs/setup/gui.rst step 5; docs/setup/deployment.rst GPU note.
55. Outcome: real run started in GUI: Runs > 5lIWO, task key OGOoRAke, agent precious-fir, slurm, GPU 16 GB. Staging. Setup run 9hZcR shows completed in GUI.
56. Remote: real run OGOoRAke is live on fir (run_workflow pid 2398758 started 19:49:15 local, java running). An earlier poll exited immediately (false positive: checked RUN.pgid before run started). Re-armed poll keyed on process presence for key=OGOoRAke.
57. Remote: real run OGOoRAke progressing (buildMnxrLookup, buildLabelTransferLandmarks submitted). NOTE in main.log 19:52:31: p36__seqkit_reads exited status 1 -- "Error is ignored" (Nextflow policy). Recorded for the report; investigate when run ends.

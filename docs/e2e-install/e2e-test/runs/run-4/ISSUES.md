# run-4 (release candidate 0.26.0+ea75c3f, 2026-11-24)

Goal: install the release candidate from a local conda channel and SIF, start `msm gui`, and drive it in a headless browser. Two stations ran at once, one Haiku agent each, both on sample SRR9658108. Station A on sockeye ran `engcyc_prep_references_lite`, then `engcyc_metagenomics_lite`. Station B on fir ran `engcyc_prep_references`, then `engcyc_metagenomics`, unsplit. Both started at 17:19.

- fir gave up at 17:31 (`fir/REPORT.md`, `CONTROL.json` give_up).
- sockeye was stopped by the operator at 17:40 (`sockeye/STOP.json`). Its setup could not run, so its compute jobs could not pull images, and its downloads had reached 35.6 GB.

Kept beside this file, per station: the agent's `STEPS.md` and `PROGRESS.md`, the watcher's `watch.csv`, and fir's `REPORT.md` and sockeye's stop record.

## What happened

1. Both installed the candidate, started `msm gui` and deployed. On fir the first deploy failed: the image tag `0.26.0-ea75c3f` is unpublished, and the staged SIF was not where the deploy looked. The agent changed the tag to `0.26.0` and deployed the old release image.
2. Both prep templates solved, then flagged five empty inputs: `ref::mnxr_lookup`, `ref::label_transfer_landmarks`, `ref::lane_calibration`, `modelling::media` and `modelling::medium_name`. The GUI refuses to run a plan with an empty row. fir stopped here.
3. sockeye deleted the five rows (no prep step reads them) and pressed set up. Setup died at staging with "spec not found for the module 'buildAspireLiteratureContaminants'" (steps 14 to 16).
4. sockeye ran the prep as a real run instead. Its downloads ran on the login node. Its first compute job could not pull its image, because sockeye compute nodes have no route to quay.io and only setup pulls images (step 18).

## Issues, ranked by how far each blocks a new user

| # | class | where | issue | fix |
|---|---|---|---|---|
| 1 | error | setup run | Setup never worked on a staged workflow. The staged bundle prunes its transform libraries to the plan's steps, but keeps the full index. Setup walked the whole index to find `pullContainer`, loaded a pruned file, and died. `pullContainer` itself was never staged. | 2d3c6af5: staging always keeps `pullContainer`; setup finds it by key |
| 2 | error | engcyc templates | Both main templates plan the GPR, ProteinBERT and CarveMe lanes, which read five inputs no step makes. Three are fabfos bake products with no download, and the other two are a growth medium. A new user cannot run either template. The prep templates copied the five empty rows although no prep step reads them. | feat/engine/gpr-refs: port the `mnxr_lookup` and `label_transfer_landmarks` builds from fabfos and ship `lane_calibration` as a resource. feat/engine/complete-medium: CarveMe gapfills on a supplied complete medium by default |
| 3 | error | e2e harness | The harness staged the candidate SIF in `<home>/container_images`. fir's login shell sets `APPTAINER_CACHEDIR`, which the engine's image store follows, so the deploy pulled from quay and failed. | 2d3c6af5: stage under the remote `${APPTAINER_CACHEDIR:-<home>/container_images}` |
| 4 | guess | docs | No docs page launches the web GUI. Both agents found `msm gui --port` from `--help`. | T16 docs page (run 3 issue 5) |
| 5 | ambiguity | GUI recipe rows | Removing a row takes two clicks ("click again to confirm"). The sockeye agent's first pass only armed the crosses. | none: the confirm is deliberate (run 3 issue 1) |

## Not tested yet

Setup as steps, the size warning against the measured footprint, the second-setup re-link, split SRA accessions through the GUI, and every workflow step. All wait on the next round.

# Round 2 (release candidate 0.26.0+07c4db2, 2026-11-26)

Both stations ran the prep templates through the GUI from 13:30. Setup ran as steps on both. The operator stopped fir at 16:55 to relaunch on a newer candidate. The watcher stopped sockeye at 16:06 on a false cap crossing (row 4). Records are in `round2/`.

| # | class | where | issue | fix |
|---|---|---|---|---|
| 1 | error | downloadGtdbRrna (sockeye) | The step bound its output by `.local`, which is the agent container's `/ws/...` path. The tool container starts from the host, so the mount source did not exist. It failed three times. | 6cd7ec31: bind `.external`. ezpred had the same bind |
| 2 | error | downloadVirsorter2DB (sockeye) | `virsorter setup` failed to create its `vs2` conda env after about 4 min, with 2.2 GB of packages fetched. snakemake hides conda's message. The same image passed on fir. | open: watch round 3 |
| 3 | error | downloadDbcanDB, buildMeropsDB (fir) | The dbCAN host returned 503, because dbCAN moved to S3. MEROPS `pepunit.lib` has CRLF line ends and a stray space, which DIAMOND refuses. | a44d3707, 127c2c04 |
| 4 | harness | watcher | The watcher summed bytes per filename. A product is hardlinked from its work dir, the cache and the run's results, so it counted each one up to three times: 563 GB on sockeye where `du` gave 187 GB. It killed sockeye on that. The setup estimate (~162 GB) was close to the truth. | watcher counts each inode once |
| 5 | ambiguity | GUI set up button | Both agents clicked "set up" 3 times with no effect before the size confirm appeared. The confirm reverts after a few seconds. fir launched only on a double click. | open |
| 6 | guess | CLI | `metasmith workflow wait <agent> <key>` wants the agent YAML path, not the agent name. The docs are silent. | open |

# Round 3 (release candidate 0.26.0+28876c1, 2026-11-26)

Both stations relaunched with `--warm` at 18:05. fir kept running. The operator stopped sockeye at 21:45 and relaunched it on 0.26.2+630bf27. Records are in `round3/`.

| # | class | where | issue | fix |
|---|---|---|---|---|
| 1 | error | cache, every station | `--warm` gave 0 hits in 53 steps. A leaf's id was its absolute path and mtime on the client. The GUI clones the standard library afresh per install, so every env file got a new id and every key changed. A user who reinstalls re-downloads every reference. | ce14980e: a file of 1 MiB or less is keyed by its library path and bytes. Directory leaves are still stat-keyed |
| 2 | error | downloadVirsorter2DB (sockeye) | The vs2 conda env took ~100 min on sockeye's Lustre. The protocol reported success at 1 h 50 min, and wrap-up crossed the 2 h limit. Nextflow's local executor killed it and reported `IllegalThreadStateException: process hasn't exited`, not a time limit. Round 2's failure was likely the same. | a57295e8: 8 h |
| 3 | harness | watcher caps under `--warm` | A warm round starts with the earlier rounds' cache on disk, which counts against the cap. fir started at 888 GB against 1.5 TB. | open: replace the watcher by hand (fir 4 TB, sockeye 900 GB) |
| 4 | ambiguity | GUI set up button | Again, the size confirm reverted before the agent clicked it (sockeye). | open, round 2 row 5 |
| 5 | error | downloadAntiSmashDB (fir) | The download and data prep passed in 10 min. The `antismash --check-prereqs` that followed tests every module's tools. CASSIS needs meme and fimo, which antismash/standalone:7.1.0 omits, so the step failed twice. No lane enables CASSIS. | drop the check. `download-antismash-databases` already runs `prepare_module_data` |
| 6 | watch | setup, failed download | Nextflow ignored the failed step and setup carried on. Check that the GUI reports the missing reference at the end of setup, and what the main workflow does without it. | open |
| 7 | slow | downloadGanon2DB (fir) | genome_updater fetches 105k RefSeq assemblies with `-t 4` on the login node: 57% after 4.4 h, so ~7.5 h in all, the last setup step. Each file logs a progress line plus a perl locale warning, 60 MB of logs. | open, after run 4 (an edit re-keys the step): raise `-t`, export `LC_ALL=C` |
| 8 | slow | downloadVirsorter2DB (sockeye, round 4) | `virsorter setup` built its conda env for 2 h 50 min on Lustre before the database fetch began. The 8 h limit holds it. | open, after run 4: an image with the env baked in |

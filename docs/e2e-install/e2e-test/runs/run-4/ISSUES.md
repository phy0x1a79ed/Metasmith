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

Both stations ran the prep templates through the GUI from 13:30. Setup ran as steps on both. The operator stopped fir at 16:55 to relaunch on a newer candidate. The watcher stopped sockeye at 16:06, when it crossed the 450 GB cap at 563 GB. Records are in `round2/`.

| # | class | where | issue | fix |
|---|---|---|---|---|
| 1 | error | downloadGtdbRrna (sockeye) | The step bound its output by `.local`, which is the agent container's `/ws/...` path. The tool container starts from the host, so the mount source did not exist. It failed three times. | 6cd7ec31: bind `.external`. ezpred had the same bind |
| 2 | error | downloadVirsorter2DB (sockeye) | `virsorter setup` failed to create its `vs2` conda env after about 4 min, with 2.2 GB of packages fetched. snakemake hides conda's message. The same image passed on fir. | open: watch round 3 |
| 3 | error | downloadDbcanDB, buildMeropsDB (fir) | The dbCAN host returned 503, because dbCAN moved to S3. MEROPS `pepunit.lib` has CRLF line ends and a stray space, which DIAMOND refuses. | a44d3707, 127c2c04 |
| 4 | error | size warning | The setup estimate counts download sizes only. sockeye's lite prep estimate was ~162 GB, and its footprint passed 563 GB. fir's was ~861 GB, and its footprint passed 2.1 TB. Unpacked and built databases sit in `nxf_work` beside their `task_cache` copy until publish. | open: estimate peak disk, not downloads |
| 5 | ambiguity | GUI set up button | Both agents clicked "set up" 3 times with no effect before the size confirm appeared. The confirm reverts after a few seconds. fir launched only on a double click. | open |
| 6 | guess | CLI | `metasmith workflow wait <agent> <key>` wants the agent YAML path, not the agent name. The docs are silent. | open |
| 7 | harness | watcher caps | The caps (sockeye 450 GB, fir 1.5 TB raised to 4 TB) sat below the real footprint. | 6cd7ec31: sockeye 900 GB, fir 4 TB |

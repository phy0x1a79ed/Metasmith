# metasmith 0.24.1 — tutorial navigator fixes

## Context

The user walked the GUI tutorial on 0.24.0 and hit two faults in the tutorial navigator (the
floating step card). This patch fixes both. It ships as 0.24.1 through the standard release
protocol, and retires the published 0.20.0.

## What you said

> step 10 doesnt auto complete after scrolling. needs to manually click next in the nav box, this should never happen.

> the nav box also jumps across the screen at times, please make it just move out of the way when necessary, but otherwise no drastic movements

> please make these changes and push 0.24.1, delete 0.20.0 if possible, otherwise direct me to do so at the end.

> and the nav box expand button should expand the box, not take me to the tutorial page

> compact before starting patch. maybe dont run all tests if can help it

## Issues

- I1. Step 10 ("See what it builds", id `template-preview`) does not advance after the user scrolls or drags the preview, so the user must click next.
- I2. Other steps may also carry `advance: false` (agent-runtime, plan, the last chapter), so the same stall can recur elsewhere.
- I3. The navigator card sometimes jumps across the screen instead of moving just enough to clear what it covers.
- I4. The navigator's expand button leaves the current page for the Tutorials tab instead of enlarging the card in place.
- I5. 0.20.0 is still published and the user wants it gone.

## High-level goals

- G1. A tutorial step that the user has completed always moves on by itself.
- G2. The navigator stays put, and only slides aside by the least amount needed when it covers the thing the user must use.
- G3. Users get these fixes as 0.24.1 from quay and anaconda.
- G4. 0.20.0 is no longer offered, or the user knows exactly how to remove it.
- G5. The navigator's expand button enlarges the card where it is, and the user stays on the page they are working in.

## Acceptance criteria

- Scrolling or dragging the step-10 preview marks the step done and advances without a click, in the running GUI.
- No step whose `done` can become true is left without auto-advance, unless the run log records why.
- The navigator's movement: it does not change sides or corners when a small nudge clears the overlap, and it returns to its home spot when the overlap ends.
- Clicking the navigator's expand button enlarges the card in place. The section and the page do not change, and a second click collapses it.
- Targeted frontend and tutorial tests pass. The full 30-min gate and 40-min docker lane are not re-run.
- quay `0.24.1-<hash>`, `0.24.1` and `latest` share one digest. Anaconda has `metasmith 0.24.1`. `release` and annotated `v0.24.1` are on origin. PR #68 is retitled "Release 0.24.1".
- Consumer gate on the published 0.24.1: conda and pulled image, 12/12 templates, backend rust, and the served GUI bundle contains the fix.
- 0.20.0 is removed from anaconda (and quay if the credentials allow), or the report names the exact commands for the user.

## Tasks

- T1. Compact (G1, G2)
- T2. Make a completed step always advance, starting with step 10 (G1)
- T3. Make the navigator move only as far as the overlap requires (G2)
- T4. Make the navigator's expand button enlarge the card in place (G5)
- T5. Verify all three fixes in the running GUI and with targeted tests (G1, G2, G5)
- T6. Commit, push `feat/gui-tutorials`, and fast-forward `feat/dev` (G3)
- T7. Compact (G3)
- T8. Release 0.24.1 through RELEASE_PROTOCOL.md: merge, bump, build, publish, tag, push, retitle PR #68 (G3)
- T9. Gate the published 0.24.1 as a consumer and check the served GUI bundle (G3)
- T10. Remove 0.20.0 from the registries, or prepare the user's commands (G4)
- T11. Debrief (G1, G2, G3, G4, G5)

## Approach by task

### T1. Compact

Handoff: this plan file, the todo list mirrored from it, and the 0.24.0 plan filed at
`data/metasmith/plans/11-release-0-24-0.md` for the release mechanics (tmp scripts
`publish.sh`, `gate.sh`, `consumer_gate.py`, `gate_compare.py`, `r10.sh` in
`/home/tony/.claude/jobs/b91fea18/tmp`). Worktree `engine/gui/.claude/worktrees/tutorials`,
branch `feat/gui-tutorials` at b86ce317. The GUI server b411gurd2 on :8095 serves this worktree's
source, and the awm lease b8zq7jeso fronts it at `/msm-tutorial`.

Gotchas: the worktree guard refuses `cd` into the shared checkout and variable-heavy bash.
Write scripts to the job tmp dir and run them by literal path.

### T2. Make a completed step always advance

Layer: the tutorial script `frontend/src/lib/tutorials/localPangenome.js` and the advance logic
in `frontend/src/components/TourLayer.svelte` (the `advanceTimer` block near line 136). Step 10
sets `advance: false`, so it never advances. First confirm whether its `done` (the
`data-moved` attribute on the preview) fires at all after a wheel zoom, and not only after a
drag. Then remove the opt-out. If the opt-out existed to avoid yanking the view mid-gesture,
delay the advance until the gesture settles rather than skipping it. Audit the other three
`advance: false` steps against the same rule.

Gotchas: a step advancing mid-zoom could change section and lose the user's gesture. `done`
may be satisfied by a stale `data-moved` from an earlier visit. `tourEdit` and `armed` also gate
the timer.

### T3. Make the navigator move only as far as the overlap requires

Layer: the card placement in `TourLayer.svelte`. The card now avoids the target only when the two
overlap on both axes (e776e058). But on overlap it may re-place to a far corner. Change it to
compute the smallest shift that clears the target rect along one axis, keep the card's home spot
otherwise, and animate the shift. Hysteresis stops it flickering on the boundary.

Gotchas: target rects change on scroll and resize. A shift must keep the card on screen. The
card must not end up covering the `do` target it is pointing at.

### T4. Make the navigator's expand button enlarge the card in place

Layer: the expand control in `TourLayer.svelte` (or `TourButton.svelte`), which now routes to the
Tutorials tab (`TutorialView.svelte`). Replace the navigation with a local expanded state. The
expanded card shows the full step list and the step body at a larger size, in the same place. The
Tutorials tab stays reachable from the nav bar.

Gotchas: the expanded card is larger, so it overlaps more. T3's shift logic must use its current
size. The expanded state must survive a step change but not a reload.

### T5. Verify all three fixes

Build the bundle (`dev/metasmith.sh` has the GUI build flag, check `--help`). Drive the
tutorial to step 10 in headless Chrome against :8095. Wheel over the preview and confirm it
advances. Exercise a step where the card overlaps its target and record the card's position
before and after. Click expand and confirm the section and URL do not change. Run only the frontend unit tests and the Python tests that cover the GUI
bundle or tutorials.

Gotchas: the :8095 server may serve a stale bundle until rebuilt. Headless wheel events may
not reach a zoom handler that listens for pointer events.

### T6. Commit, push, fast-forward `feat/dev`

Stage by path. Push `feat/gui-tutorials` to origin. Fast-forward `feat/dev` to it and push.

Gotchas: never push main or master. Never force-push.

### T7. Compact

Handoff: the commit SHA, the verification evidence, and the next step, T8.

### T8. Release 0.24.1

Follow RELEASE_PROTOCOL.md exactly as in 0.24.0. Fast-forward `release` to `feat/dev`, then
commit a version.txt bump. Build every artifact in protocol order. Then publish with `-ud` and
`-uc`. Next, write an annotated `v0.24.1` tag listing the digest and package, and push `release`
and the tag. Finally, retitle PR #68 if it is still open. Run only the version-to-tag unit
tests after the bump.

Gotchas: the anaconda token check uses the msm env's `anaconda org whoami`. The post-merge DVC
hook failure on `data/fabfos/runs/aska/gpr` is known and harmless. Run builds detached with a
Monitor.

### T9. Gate the published 0.24.1

Reuse `gate.sh` with the version changed to 0.24.1. Add a check that the published package's
GUI bundle contains the T2 to T4 changes. The GUI is the only thing that changed, so a pangenome rerun
through `r10.sh` on the new env is the real-run control. It should be mostly cache hits.

Gotchas: rmi every 0.24.1 tag before the pull. Keep `env -u PYTHONPATH`.

### T10. Remove 0.20.0

Check what 0.20.0 exists as: anaconda `hallamlab/metasmith/0.20.0`, and quay tags `0.20.0*`.
Remove the anaconda release with the msm env's `anaconda remove`. Quay tag deletion needs a
quay API token or the web UI. Try the token and hand the user the steps if there is none. Leave
the git tag `v0.20.0` in place, since the source history stays valid.

Gotchas: removal cannot be undone. Confirm the exact version string before deleting, and never
touch 0.20.x siblings such as 0.20.4.

### T11. Debrief

Journal to `metasmith/engine/gui` and `metasmith/engine/release`. Copy this plan to
`data/metasmith/plans/12-release-0-24-1.md` and commit it.

## Callouts

- "delete 0.20.0" is read as the published artifacts (anaconda and quay), not the git tag.
- The full gate and docker lane are not re-run, per the user. The change is Svelte and JS only.

## Autopilot

**Guardrails:**
- Never push to main or master, never force-push, and never delete a git tag.
- Stage by path.
- Run git, mamba and docker unsandboxed.
- Run long jobs detached (setsid nohup) with a Monitor, never piped through tail.
- Do not re-run the full gate or the docker lane. Run targeted tests only.
- Publishing 0.24.1 and removing 0.20.0 are authorised by the user's message.

**Resume handles:**
- Worktree `engine/gui/.claude/worktrees/tutorials`, branch `feat/gui-tutorials` at b86ce317.
- GUI server b411gurd2 on 127.0.0.1:8095 serves this worktree's `src/`. awm lease b8zq7jeso fronts it at `/msm-tutorial`.
- Job tmp `/home/tony/.claude/jobs/b91fea18/tmp` holds the 0.24.0 scripts to reuse: `publish.sh`, `gate.sh`, `consumer_gate.py`, `gate_compare.py`, `r10.sh`, `r10_pangenome.py`, `tag_msg.txt`, `pr_body_final.md`.
- Release mechanics and their gotchas are in the 0.24.0 run log, `data/metasmith/plans/11-release-0-24-0.md`.

### Live state

Finished. T8 released 0.24.1 (tag v0.24.1 on e96f63b9, image sha256:9942e1ca…, anaconda 0.24.1). T9 gated it 12/12 in both lanes with the fix in the served bundle. T10 found nothing to delete. T11 filed this plan as `data/metasmith/plans/12-release-0-24-1.md` and added the tutorial-step bullet to the architecture brief. Earlier state follows.

T2-T6 done. The fixes are e8c9da16 plus the review and step-21 follow-up 2222f0d2. `feat/gui-tutorials` and `feat/dev` are both 2222f0d2 on origin; the `engine/dev` worktree was fast-forwarded by `tmp/ff_dev.sh`. Verification: `tmp/tour_fix.py` passes on the final bundle, apart from the expected enlarged-box overlap on the plan step. `tmp/tour_slide.py` passes, the live step-21 run `pragmatic-mule-zHy2p` advanced on its own 7s after completing, and `-tg` gave 380 passed. T10 found nothing to delete. Next: T8, the release from the `engine/release` worktree (release is 695e7938). Reuse `tmp/build.sh`, `publish.sh`, `gate.sh`, `tag_msg.txt` and `pr_body_final.md`, bumping 0.24.0 to 0.24.1.

### Run log

- 2026-09-29: plan written. Step 10 is `template-preview` in `localPangenome.js` and carries `advance: false`, as do agent-runtime, plan and one step near line 397. `TourLayer.svelte` advances through `advanceTimer` near line 136.
- 2026-09-29: T2. Removed all four `advance: false`. The advance now waits for ADVANCE_MS of quiet wheel, drag, key and input events, so a long zoom is never cut off. agent-runtime's select is pre-filled, so its done was true on arrival and it would have skipped itself; it now completes on a pointerdown or change on the select (new `touchOn` field). The outro sets `dim: false` so its scrim does not cover the heatmap the step before opens.
- 2026-09-29: T3. The navigator keeps its home spot while that is clear. When it is not clear, it keeps a previous slid spot that is still clear, and otherwise takes the nearest spot flush against an obstacle edge. The first drag test left a 466 px² overlap with the callout: clientWidth excludes the border. Switched to offsetWidth/offsetHeight and added an 8px callout margin.
- 2026-09-29: T4. The header ☰ (which opened the Tutorials tab) is now ⤢/⤡ toggling a 420px card that lists every step. It survives step changes.
- 2026-09-29: T5 evidence at 1440x900: step 10 held through 2s of wheel and advanced 0.8s after; runtime not done on arrival; expand kept `#tutorials` and grew 300x184 to 420x610; the largest navigator move over 19 steps was 24px (height change only). At 1280x760, dragging onto `+ agent` slid 260px straight down, clear of ring and callout, and held still; it went home on the next step. `-tg`: 380 passed in 46s.
- 2026-09-29: T10 finding, ahead of order: 0.20.0 is not published anywhere reachable. Anaconda hallamlab has 0.20.3/0.20.4 only. The quay tag 0.20.0-3499dfa expired 2026-08-04 (manifest 404). PyPI and TestPyPI have no 0.20.x. No v0.20.0 tag exists on origin or upstream, and there are no GitHub releases. Nothing to delete; ask the user where they saw it.
- 2026-09-29: adversarial review of e8c9da16, triage:
  - (1) VERIFIED by reasoning, not reproducible headless: a native select's open list swallows page events, so the runtime step advanced 0.9s after the press that opened it. Fix: a pointerdown on a select holds the advance until a key, change, focusout or pointer move is heard (10s cap). Test: 3s of silence after pressing held the step; moving the pointer advanced it 1.0s later.
  - (2) VERIFIED: a hover on the way past ended the plan step. Fix: `touchOn: ['pointerdown']` and reworded `do`. Test: 2s after a hover it was still open; a click advanced it.
  - (3) VERIFIED: a zoom during step 9 made step 10 arrive done. Fix: the preview's `data-moved` is now the last-move timestamp and step 10's `enter` records its open time. Test: zooming from the pick through 1s after the image appeared kept step 9 open, and step 10 was not done 2.5s after arriving.
  - (4) VERIFIED: the enlarged list's scroll effect ignored step changes. Fix: it depends on `tour.step`. Test: the current row stayed inside the list after an advance.
  - (5) PARTLY: when nothing clears, it took the least overlap wherever that was (a 1177px jump on the plan step when enlarged). Fix: it stays put when no spot clears everything, and slid spots stay below the tab bar. The enlarged box at 1440x900 still overlaps the plan on the plan step, by choice of the user who enlarged it.
  - (6) VERIFIED: the runtime select chosen by keyboard never completed. Fix: `keydown` added to its `touchOn`.
- 2026-09-29: the user added: "same with step 21: please make sure it auto advances, unless the user clicks on that step directly". Step 21 is `watch-run`. Probes on the completed run: arriving by Next advanced in 1.1s; a reload advanced only because the runs list had not loaded yet (a race); a click in the list held, as asked. The rule is now: arrived by `back` or `jump` waits if already done; `forward` and `restore` advance. A live run test is under way (`tmp/step21_live.py`).
- 2026-09-29 T8: `release` cannot fast-forward to 2222f0d2, because it holds the 0.24.0 bump 695e7938 that `feat/dev` lacks. Merged instead (02b0aa3f, no conflicts: `feat/dev`'s version.txt is still 0.23.0), then bumped to 0.24.1 (e96f63b9). The DVC hook failed again on the known `data/fabfos/runs/aska/gpr`. The version-to-tag tests gave 11 passed. The build launched at 17:45 (`tmp/build.log`, Monitor b9160b5zz); 0.24.0's logs are kept as `build_0240.log` and `publish_0240.log`.
- 2026-09-29 T8: every build step exited 0, from 17:45 to 18:14. The image is `0.24.1-95aaa6f` with real relays and vendored library 6b72441 (12 templates). The bundle is `index-DMdRNYCd.js`, the one verified at T5. The build hash printed before `-bp` still read 95e78da because `build_hash.txt` was stale; `-bp` regenerated it. `tmp/publish.sh` ran from 18:14 to 18:20 and exited 0. `0.24.1-95aaa6f`, `latest` and `0.24.1` share sha256:9942e1ca87944fd14ecfb088a5718bf4b5417e9faba140c6325ea623368a712b. The clean-room install reported backend=rust, then `hallamlab/metasmith/0.24.1/noarch/metasmith-0.24.1-py_0.tar.bz2` was uploaded. Annotated `v0.24.1` (0386669) is on e96f63b9. `release` was pushed 695e7938..e96f63b9 with the tag. PR #68 is now "Release 0.24.1" at e96f63b9, with body `tmp/pr_body_0241.md`.
- 2026-09-29 T9: `tmp/gate_0241.sh 95aaa6f` ran from 18:45 to 18:49 and exited 0. The conda lane installed the new env `msm_gate_0241` from anaconda.org. The installed bundle and the one `msm gui` served on :8097 are both `index-DMdRNYCd.js`, which contains "enlarge this window". The docker lane rmi'd `0.24.1`, `0.24.1-95aaa6f` and `latest`, then pulled `0.24.1-95aaa6f` back at sha256:9942e1ca…, and that image's bundle carries the fix too. Both lanes: 0.24.1+95aaa6f, backend rust, library 0.24.1+9182483, 12/12 templates. Per-template ok, steps and drops are identical between the lanes and to 0.24.0. The r10 real-run control was skipped: the change is GUI-only, and the live step-21 run already went end to end on this source.
- 2026-09-29 T10: closed with nothing to delete (see the earlier entry). The report asks the user where they saw 0.20.0.

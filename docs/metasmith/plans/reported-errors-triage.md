# Reported errors, triaged against current code

This is a punch list of the errors that users (Antonio, Rokaiya) and agents hit while using metasmith. Each entry is checked against the code at `feat/dev` `e8d23191`. Statuses:

- **OPEN**: still present in the code today.
- **FRICTION**: works as designed, so the design or the docs should change.
- **UNVERIFIABLE**: not reproduced, or nothing in the code to check.
- **FIXED**: the fixing commit is named.

Code locations name a file and function or area. Line numbers drift, so use them only to find code.

Sources:

- the metasmith scope journals (engine/fix-issues-from-antonio, engine/dev, engine/gui, engine/release, engine/direct-run, engine/patch-0222, engine/data-import, engine/process-management, engine/solver, engine/cami*);
- `consolidation-followups.md`;
- Rokaiya's support logs at `data/support/rokaiya_2026-10-06/` in the `feat/fix-issues-from-antonio` worktree. These are untracked and not DVC-pinned.

The journals record only item 9 of Antonio's 11-item DM of 2026-08-10. The other items need the DM text.

## OPEN

| id | symptom | source / date | surface | evidence |
|---|---|---|---|---|
| O1 | `stage_workflow returned but launcher missing at .../start.sh`. Staging logs `staging failed` and returns, so `msm api stage_workflow` exits 0 and the cause never reaches the GUI. About 10 local runs failed this way | Rokaiya 2026-10-06 | GUI, CLI | `agents/runner.py` staging returns after logging; `agents/workflow_ops.py` asserts the launcher exists |
| O2 | MAMBA runtime accepts a `docker://` container. The stub becomes `mamba run -n docker://...`, no relay is installed, and deploy "succeeds" | Rokaiya 2026-10-06 | GUI, deploy | `env/environment.py` emits `mamba run -n {image}`; `gui/api.py` `create_agent` validates nothing |
| O3 | Commands for local agent A run in agent B's home. The relay workspace is keyed only by host and user | Rokaiya 2026-10-06 | local agents, relay | `src/bash_relay/src/main.rs` `msm_{host}_{user}` |
| O4 | A Nextflow abort (`Executor 'local' does not support job arrays`) shows as `completed` with zero tasks | Rokaiya 2026-10-08 | GUI, HPC | `agents/runner.py` `_failed_steps` returns `[]` for an empty task table |
| O5 | `ssh connection failed []` on fir (wrong key, then Duo). The probe failure has no diagnosis | Rokaiya 2026-10-06 | GUI, deploy | `agents/agent.py` asserts with empty `res.err` |
| O6 | The GUI ssh editor writes a generated key fir rejects, and no `ControlMaster`/`ControlPersist`, so MFA hosts never pass the probe | Rokaiya 2026-10-06 | GUI, ssh | `gui/sshconfig.py`; no `controlmaster` anywhere in `src/metasmith` |
| O7 | Docs say `PreferredAuthentications publickey`, which blocks Duo on Alliance hosts | Rokaiya 2026-10-06 | docs | `setup/ssh.rst`, `tutorials/remote_agent.rst` |
| O8 | Input paths are unchecked at entry and solve. A nonexistent file is caught only at stage, then swallowed by O1 | Rokaiya 2026-10-06 | GUI | input routes in `gui/api.py`; only `agents/runner.py` checks at stage |
| O9 | A 240 GB workflow solves and stages on a 16 GB laptop. The host-ceiling refusal comes only at launch | Rokaiya 2026-10-06 | GUI, local | `check_launch` in `agents/workflow_ops.py`; nothing in `gui/` consults `agents/ceiling.py` |
| O10 | `check_launch` reads config before per-step `resource_overrides` are appended, so capped callers are still refused | engine/dev 2026-08-30 | CLI, Python | `agents/workflow_ops.py` launch check |
| O11 | Cancel in a run's first minute does nothing: `PID.lock` lands after `RUN.token` | engine/release 2026-08-30 | GUI | `agents/run_control.py` cancel returns `noop` without `PID.lock` |
| O12 | Deploy cannot be cancelled, and there is no progress during a cold apptainer pull plus `mksquashfs` | Rokaiya 2026-10-08 | GUI, deploy | `gui/jobs.py` has no cancel |
| O13 | The `msm` stub carries no agent setup commands, so `ssh host ./msm --version` fails on fir | Rokaiya 2026-10-08 | deploy, ssh | `agents/agent.py` runs `setup_commands` only in the deploy shell |
| O14 | A failed provisioning step ends at `relay binary missing`, and an unknown exit code counts as success | Rokaiya 2026-10-08 | deploy | `agents/agent.py` accepts `exit_code in (0, None)` |
| O15 | `Agent.Deploy` raises a bare `AssertionError` when remote home resolution drops a line | followups | deploy, HPC | `agents/agent.py` home resolution |
| O16 | Two agents can be saved with the same home | Rokaiya 2026-10-08 | GUI | no uniqueness check in `create_agent` |
| O17 | Changing an agent's home orphans the old deployed home. Deploying into a data folder warns nothing | Rokaiya 2026-10-06 | GUI, deploy | no home check in `create_agent` or `Agent.Deploy` |
| O18 | A "local" agent saved with an SSH home and an empty host: `ssh://:~/msm.X` | Rokaiya 2026-10-08 | GUI | `create_agent` passes the home through unchecked |
| O19 | `metasmith build all` drops a library's `pinned:` block and moves every member id | followups | CLI, libraries | `models/build_libraries.py` builds a fresh library instead of loading |
| O20 | A library staged against an older agent image dies in every task (`ExecWithEnv() got an unexpected keyword argument 'env'`) | campaign 2026-09 | HPC | no staging-time library/image version check |
| O21 | An unsatisfiable requirement is reported against unrelated targets | campaign 2026-09 | Python, solve | `models/workflow/diagnostics.py` ranks dead ends by search frontier |
| O22 | A corrupt product is promoted into the cache and served as a hit | campaign 2026-09 | HPC, cache | `caching/promote.py` attests existence only |
| O23 | The `METASMITH_DRIVER_SLURM` driver on a compute node finds no relay socket and submits nothing | campaign 2026-09 | HPC | relay path keyed on node hostname |
| O24 | The straddle-mounts message says metasmith refuses to compile, but codegen forces `copy` and proceeds | engine/gui 2026-09-29 | HPC, cache | `caching/fs.py` vs `models/workflow/nextflow_codegen.py` |
| O25 | Docs call removed API, and `my_first_agent` hits `GivenNotImportedError` | engine/gui 2026-09-29 | docs, Python | user docs; covered by the docs overhaul |
| O26 | The local executor ignores `-params-file` for its memory cap | engine/dev 2026-08-21 | local preset | `_render_executor_config` in `agents/workflow_ops.py` |

## FRICTION

| id | symptom | source / date | surface | evidence |
|---|---|---|---|---|
| F1 | `msm gui` takes its project from the cwd, so two start directories make two workspaces | Rokaiya 2026-10-08 | GUI | `coms/cli/legacy.py` `--project` default |
| F2 | `setup_commands` defaults to `#!/bin/bash`. fir needs `module load apptainer` | Rokaiya 2026-10-08 | GUI, HPC | site-specific: needs a hint, not a default |
| F3 | `slurm.nf` ships a `<slurm_account>` placeholder and says compute nodes have no network, which is false on fir | Rokaiya 2026-10-08 | HPC presets | `nextflow_config/slurm.nf` |
| F4 | A run param silently beats the preset default, and the GUI does not show which won | Rokaiya 2026-10-08 | GUI | display only |
| F5 | The GUI allows DOCKER on a cluster host without warning | Rokaiya 2026-10-06 | GUI | `AgentFields.svelte` |
| F6 | Any mtime rewrite re-keys a stat-addressed resource library | followups (accepted risk) | libraries, cache | followups |
| F7 | Changing bytes beneath a pool entry is invisible until re-import | followups | cache, pool | followups |
| F8 | A transform whose product extends its required type self-loops in the solver | followups | solver | followups |
| F9 | A cache hit copies gigabytes when one directory is bind-mounted twice | followups | HPC, cache | followups |
| F10 | The user must start and tunnel the GUI, so docs links cannot reach it | docs overhaul | GUI, docs | docs-overhaul plan, seekable tutorials |

## UNVERIFIABLE

| id | symptom | source / date | surface | evidence |
|---|---|---|---|---|
| U1 | Antonio item 9: after kill and relaunch, outputs carry different hashes and `group_by` fails | Antonio 2026-08-10 | CLI, HPC | never reproduced; 358b8a85 limits the driver to its own session |
| U2 | Antonio items 1-8, 10, 11 | Antonio 2026-08-10 | unknown | DM text in no journal |
| U3 | A stage passed verify with missing input paths | Rokaiya 2026-10-06 | local | suspect O3; needs repro on the support logs |
| U4 | KBase library refused by the witness: 27 transforms declare two identical input slots | engine/solver 2026-09-05 | solver | `models/solver_wire.py` interning |
| U5 | E3 driver: hybrid pairings sharing files build 6 of 17 assemblies | E3 run log | Python | research driver |

## FIXED

| id | symptom | fix |
|---|---|---|
| X1 | SLURM preset aborts at the first cache twin | bdd8e5b7, on `feat/dev`, not in v0.24.1 |
| X2 | `msm workflow run --params/--override` land in the wrong parameters | `feat/engine/docs`, with `tests/metasmith/unit/test_cli_workflow_run_args.py` |
| X3 | Container step `exitcode.XXXX: Permission denied` after a bare `cd` | 5060bc7f |
| X4 | Directory product uncacheable; an unservable hit emitted an empty channel | 1343ccad |
| X5 | Adding one sample reruns everything | 2cebd921 |
| X6 | `BrokenPipeError` on GUI deploy | c38c8d8c |
| X7 | Shared task index race; `scratch` lost task metadata | bcac1be9, 4b7e1ea3, 5d679c36, 0fc55ac6 |
| X8 | Direct run died with `lin entry carries no KEY` | f402c68f |
| X9 | `msm run` could not answer `context.SourceOf` | 1ae3d278 |
| X10 | `msm cache gc --delete` reclaimed nothing after an epoch bump | 2cebd921 |
| X11 | `WaitForWorkflow` reported `errored` while the driver was still collecting | 1343ccad |
| X12 | `clone_stdlib` never re-synced | 3f000f75 |
| X13 | werkzeug banner and browser-launcher stderr leak | efe8e0aa, af349b68 |
| X14 | Download transforms silently re-fetched 5.5 GB | 5060bc7f |
| X15 | Unpinned large target sets blew the solver past 12-70 GB | 16d1980f, 46d43db4 |
| X16 | An unschedulable launch aborted an hour in | 5060bc7f (refused up front; side effects O9, O10) |

## Candidate for tutorial 6

The best candidate is `sequences::orfs_shard` (or any embedding target: `ankh`, `prott5`, `esmfold`, `saprot`):

- Four embedding transforms consume it.
- Its only producer, `transforms/logistics/_disabled/shardFasta.py`, is disabled, and no given matches it.
- The solver therefore emits the `missing_input` hint. `build_templates.py` records this as `BLOCKED["dl_embeddings_from_orfs"]`.

Recheck with `dev/libraries.sh -b` before writing the page. A requirement in a library the driver omits is unsuitable until O21 is fixed.

# Operation registry and project layer: design contract

Paths are under `src/metasmith/` unless noted. Verified against the worktree; "today" means HEAD of `feat/engine/docs`.

## Findings that shape the design

- `ops/__init__.py` is empty and `ops/cache.py` and `ops/data.py` import only `caching/*`, `models/*` and `hashing`, so the "pool.py -> ops cycle" is not a real import cycle today. `agents/pool.py` imports them lazily inside methods. It becomes a real cycle the moment a registry is populated from `ops/__init__` (it would pull in `ops/agent.py`, which imports `agents`). `tests/metasmith/unit/test_no_import_cycles.py` only parses top-level imports, so it hides the lazy ones.
- `pool.py` builds remote CLI strings by hand (`"cache tag"`, `--cache-root`, `--replace`, `data import`, `data forget`, `cache list` flags). That is the wire protocol the golden test must pin.
- `msm gui` already has `--project` (default cwd). The `Project` class (`gui/store.py`) has no Flask dependency; `gui/names.py` imports `coolname` lazily.
- A solved workflow directory `workflows/<name>/` already holds `task.yml`, and `ops/workspace.py:task_path` accepts any task directory. So `ops.runtime.stage(agent_path, wf_dir, ...)` is already usable by name once a resolver exists.
- T2 appears landed: `coms/cli/workflow.py:_cmd_run` passes keywords, and `tests/metasmith/unit/test_cli_workflow_run_args.py` pins it.
- `Agent.Deploy` is pinned by `tests/metasmith/deploy/test_deploy_skip_marker.py` (it forbids a home-exists or `lib/agent.yml` short-circuit and requires the `assertive` flag and the relay gate). Only `Deploy`'s own source block is inspected.

## 1. The `@op` registry

Home: `ops/_registry.py`, a leaf module (stdlib only, no `metasmith` imports). It holds the decorator and a dict of entries. `ops/__init__.py` stays empty. A separate `ops/catalog.py` imports every op module to fill the registry; only the CLI builder, `metasmith.api`, the docs extension and tests import it. Op modules import only `_registry`.

One entry records:
- Identity: group, verb (defaults to the function name, underscores to dashes), and the function.
- Scope: `path` (arguments are files and homes, as today) or `project` (first parameter is the `Project`, injected by the surface).
- Per-parameter overrides, only where the default rule is wrong: flag spelling and short flags (`--agent/-a`, `--home` dest), repeatable, required-as-flag, choices, metavar, and a parser name: `name_value` (NAME=VALUE, JSON-tolerant, as `agent.py:_parse_params`), `json`, or `step_kv` (`step=cpus:4,memory_gb:8`, as `_cmd_run`). Parsers are named functions in the registry, so Python callers pass real dicts and never see them.
- Hidden parameters: `on_phase`, `on_progress`, `resolve_pool`, model objects (`Spec`, `DataInstanceLibrary`). Hidden means no flag; Python callers can still pass them.
- Presentation: `gui=("section", "data-tour-anchor")` or `gui=None` (shown as "no GUI action" in the reference and tutorials 7-8), and `hidden=True` for internal verbs.

Default CLI rule, derived from the signature: a required parameter without a default is a positional; everything else is `--kebab-case`; `bool` defaults to `store_true`; `list[str]` is `nargs="+"` positional or a repeatable flag; `Literal`/enum annotations give choices. Every deviation from the rule must be written as an override, and the golden test is what catches a missing one.

Docstring convention: Google style. The first line is the argparse `help` and the Sphinx summary; an optional paragraph is the long description; an `Args:` block gives one line per parameter, which becomes that flag's `help`. Reasons: napoleon already renders it in Sphinx, a 20-line stdlib parser (`inspect.getdoc` plus one regex) avoids a dependency, and it keeps help beside the signature instead of inside `Annotated[...]` noise. A fast-lane test requires a summary line and an `Args:` line for every non-hidden parameter of every registered op. Porting rule from T7: copy today's argparse `help=` strings verbatim.

Hand-written commands (`run`, `e2e`, `gui`, `lab`, `get`, `api`) keep their own `register(subs)` and are added to the parser after the generated groups. They appear in the snapshot (it is taken from the parser, not the registry) and in the reference as "hand-written" entries with a docstring on their `_cmd_*`. `api` stays hidden.

## 2. CLI generation and the golden snapshot

`coms/cli/_main.py:_build_parser` calls `registry.build_subparsers(subs)` for generated groups, then the hand-written registrations. Each group parser gets `set_defaults(func=print_group_help)`, so `msm cache` prints the cache help instead of the top-level help (today `main()` falls back to `parser.print_help()` of the root, `_main.py:66`).

Snapshot test (`tests/metasmith/unit/test_cli_surface.py`, fast lane). `dump_surface(parser)` walks the argparse tree through `_SubParsersAction._name_parser_map` recursively, in sorted verb order, and for each leaf records: verb path, positionals in declared order (dest, nargs), options sorted by first spelling (all `option_strings`, action kind, nargs, type name, choices, required, metavar, and the default only when it is a JSON primitive). Help text is excluded: it may change freely, spelling may not. Output is `json.dumps(sort_keys=True, indent=1)` in `tests/metasmith/unit/snapshots/cli_surface.json`, regenerated only with `MSM_UPDATE_SNAPSHOT=1`.

First snapshot: the first commit of T7 adds only the dump function and the snapshot generated from HEAD's hand-written parser, before any `@op` exists. Every later step must leave the file byte-identical, except additive new verbs (T8, T9), which the test reports separately: a removed or changed entry fails; an added entry fails with "update the snapshot deliberately". A second small test round-trips the remote spellings: `registry.render_cli(op, **kwargs)` (used by `pool.py`) is fed through the parser and must bind the same keyword arguments.

## 3. Python facade: `metasmith.api`

`metasmith.api.<group>.<verb>` is the decorated function itself, so docstrings and signatures are the same objects the CLI is built from. Path-scoped ops are used directly: `api.cache.list(agent_home=...)`. Project-scoped ops hang off a handle: `proj = api.open_project(".")`, then `proj.agent.deploy("pangenome-agent")`; the handle binds `project` as the first argument. Returns stay plain JSON-able dicts and lists, identical to `--json`, because the CLI emitter and the GUI both serialise them and tutorials show the same keys in every tab. Model objects appear only as optional input parameters (`Spec`, `DataInstanceLibrary`) and as an escape hatch: `proj.agent.load(name)` returns the `Agent` object for authoring (tutorials 7-8). `Agent` stays below ops; ops wrap it, the facade never changes `python_api.py`'s exports. Tutorial Python blocks are a runnable script: `import metasmith.api as msm; proj = msm.open_project(...)`, one statement per step, no hidden state besides the project directory.

## 4. Project layer

- `gui/store.py` moves to `ops/project.py` (`Project`, `WorkflowRecord`, `RunRecord`, `ProjectError`, `LIVE_RUN_STATES`), and `gui/names.py` moves with it. `gui/store.py` becomes a re-export until T8 ends. On-disk layout is unchanged, so existing GUI projects keep working.
- Addressing: hosts by SSH alias, agents by `agents/<name>.yml`, workflows by `workflows/<name>/`, runs by `<workflow>/<run>`, templates by name (library and `user_templates/`), sample sheets by workflow. Ops take names plus the injected `Project`; they resolve to paths and call the existing path ops, so path-addressed ops are untouched.
- Coexistence in the CLI: existing positional `agent` arguments accept a YAML path or, when the value is not an existing file and has no `/` or `.yml`, a name in the current project (one `AgentRef` parser, shared by every agent-taking op). The `workflow plan/stage/run/collect` task-key flow (workspace `~/.metasmith/workspace`, `--workspace`) is unchanged; a project workflow's solved directory is also accepted anywhere a task reference is, because `task_path` already takes directories.
- `--project`: a global flag beside `--workspace`. Resolution order: flag, then `METASMITH_PROJECT`, then the nearest ancestor of the cwd that is a project (has `.metasmith_gui.yml` or both `agents/` and `workflows/`). Project-scoped ops with no project refuse with that list; only `project init` creates one. `msm gui --project` keeps its own default (cwd) and is not rewritten.
- Get-or-create forms for tutorial fast-forward: every create-style project op takes `exist_ok` (CLI `--exist-ok`): `agent.create`, `host.add`, `workflow.create`, `template.save`. With it a repeat returns the existing object with `"created": false` and never rewrites a differing definition silently (it reports `"differs"`). Tutorial objects get stable names (`tutorial-<id>-agent`, `-workflow`).
- Deploy that skips when ready: a new op `agent.ensure(name)` composes `ping` + a ready probe + `deploy`; it is not a flag on `Agent.Deploy`. The probe is a separate `Agent` method (`IsDeployed`: checks `AgentPaths.to_definition(home)` and the relay path on the agent, and compares the recorded version) and `ops.agent.ensure` calls `Deploy` only when the probe fails or `assertive=True`. This leaves `Deploy`'s block, and so `test_deploy_skip_marker.py`, untouched; a new test must show `ensure` skips the call when ready and `deploy` never does. Runs are not get-or-create (each gets a new name), and fast-forward never recreates the tutorial workflow, since a fresh one re-mints value ids and misses the cache (T14).

## 5. Moving GUI-only code

| From | To (op module) | Travels with it |
|---|---|---|
| `gui/store.py`, `gui/names.py` | `ops/project.py` | none beyond name validation and `LIVE_RUN_STATES` (a live run is not deletable) |
| `gui/sshconfig.py` (440 lines) | `ops/hosts.py` (group `host`) | managed block first in `~/.ssh/config`; markers kept; `--ssh-config` path override |
| `gui/share.py` | `ops/share.py` (group `share`; T9 builds file export on its `export_*`/`import_*`) | string payload with version prefix and digest; lineage by row id never path; best-effort name resolution |
| `gui/recipe.py` (`rows_of`) and request writing | `ops/recipe.py` (group `recipe`) | adopt-once, row ownership recorded server-side |
| `gui/stdlib.py` (`discover`, `type_index`, `bootstrap_project`, `resync_workflow_types`) | `ops/stdlib.py` (group `library`) | none beyond `type_index` cache |
| template routes (`_templates`, `_user_templates`, `save_as_template`, `render_template_dag`) | `ops/templates.py` (group `template`) | template DAG cache keyed by `GEOMETRY_VERSION` stamp |
| route bodies `generate_workflow`, `fork_workflow`, `put_workflow`/`create_workflow` | `ops/recipe.py` (`solve`, `fork`, `create`) | incremental `inputs.sync` called unconditionally at the top of every solve; recipe fingerprint stored verbatim in the result; input problems recorded at solve time; stale-file cleanup before replan; `_plan_lock` serialises planning |
| route body `create_run` and `_runnable`/`_ensure_preset` | `ops/launch.py` (`start`, `list`, `log`, `cancel`, `collect`) | run verdict comes from the solve record, not the page; run state machine and `on_exist` |
| `_checked_params`, `_checked_overrides`, `_agent_problems`, `_agent_payload` | `ops/agent.py` and `ops/launch.py` | incompleteness reported not refused until launch |

`ops/samples.py` and `ops/inputs.py` are already ops; they gain `@op` (the GUI-only status is a `gui` anchor, not a different layer). The GUI keeps only what is genuinely HTTP: `JobRunner`, `LogCapture`, SSE, the file/zip download routes, theme and DAG-drawing routes, the watcher. Long ops take a hidden `on_phase`; the route turns it into `job.emit("PHASE:...")` as `deploy_agent` already does. The remaining `architecture.md` "Web GUI" invariants (PUT-whole-object saves, section-id spelling, relative `api/` path, DAG geometry, `data-tour` anchors, `?tourEdit` ids) stay with the frontend and the routes. The `data-tour` anchor named in an `@op` entry is a new coupling, and the fast lane checks it exists in `frontend/src`.

## 6. Migration order and risk

1. Registry module and the snapshot test, snapshot taken from the untouched parser (green).
2. Cycle break: leave `ops/__init__` empty, add `_registry` as a leaf, add a test that `_registry` has no `metasmith` imports, then let `pool.py` import `ops.cache`/`ops.data` at top level and build remote strings with `render_cli`. Only then add `catalog.py`.
3. Convert one group at a time (`cache`, `data`, `agent`, `types`, `transforms`, `workflow`, `build`, `source`, `task`), replacing that module's `register`; snapshot green after each. Do groups with custom parsers (`agent`, `workflow run`) last.
4. Add `--project`, `AgentRef`, `ops/project.py` (store moved, shim left).
5. T8 slices in the order hosts, templates, stdlib, share, recipe, launch; each slice keeps the gui lane green and adds new verbs to the snapshot deliberately.
6. T9 export/import on top of `ops/share.py`.

Risks: (a) golden test passes but a verb binds the wrong op parameter (the T2 bug class); mitigate with the remote round-trip test plus one binding test per verb that a flag changes. (b) Defaults in the dump: lambdas and `Path` defaults must be normalised or excluded. (c) T8 is large; each slice ships alone behind the gui lane. (d) `AgentRef` name fallback could mask a typo as "no such agent" instead of "no such file"; the error must name both lookups.

## 7. Open questions for the user

1. Group names for the new project-scoped CLI verbs: `host`, `template`, `recipe` (editable workflow plus inputs and solve), `launch` (runs), `library`, `share`: acceptable, or should project workflows reuse `workflow` with a `--project` switch?
2. Should name-or-path fallback for agent arguments (`AgentRef`) be accepted everywhere, or only behind an explicit `--project`?
3. Is a marker-based cwd project discovery acceptable as the default, or should a project always require `--project` or `METASMITH_PROJECT`?
4. Should Python ops return plain dicts only (my default), or TypedDicts per op for editor help (more annotation work in T7)?
5. May the CLI snapshot permit additive new verbs without a manual update flag, or must every addition be a deliberate regeneration?

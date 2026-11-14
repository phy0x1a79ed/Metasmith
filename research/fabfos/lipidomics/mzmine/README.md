# MZmine 4

## Purpose & Contents

How this lane runs MZmine 4 to build per-injection ion tables from the raw timsTOF runs. `run_mzmine.sh` is the entry point. `batches/` holds the committed batch files.

## Setup

1. Create the env from `envs/fabfos/mzmine.yml`.
2. Log in once: run `~/lib/miniforge3/envs/mzmine/bin/mzmine --login-console` in a real terminal. Use the mzio account (https://auth.mzio.io, academic email for the non-profit license).
3. Confirm the user file with `mzmine --list-users`. It lands in `~/.mzmine/users/`.

## Rules

- Call the binary by path, not through `mamba run`. Start-up is about 5 s. One batch call processes every input, so start-up is paid once per batch.
- **CAUTION:** `--login` falls back to a console password prompt on a headless node. Never route that prompt through an agent session.
- Keep the `.mzmine` project as the full record of a run. Derive analysis files from its exports.

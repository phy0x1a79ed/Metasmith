#!/usr/bin/env bash
# Run one MZmine batch headless on a set of raw runs.
# Usage: run_mzmine.sh <batch.mzbatch> <input-glob-or-list.txt> <output-base>
set -euo pipefail
MZMINE="${MZMINE:-$HOME/lib/miniforge3/envs/mzmine/bin/mzmine}"
USER_FILE="${MZMINE_USER:-$(ls "$HOME"/.mzmine/users/*.mzuser 2>/dev/null | head -1)}"
[[ -f "$USER_FILE" ]] || { echo "no mzmine user file; run: $MZMINE --login-console" >&2; exit 2; }
batch="$1" input="$2" out="$3"
mkdir -p "$(dirname "$out")"
exec "$MZMINE" -user "$USER_FILE" -batch "$batch" -input "$input" -output "$out" -memory none

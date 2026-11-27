#!/bin/bash
# The whole pilot: stage chunks, run every chunk offline in parallel, summarise.
# usage: run_pilot.sh <psortm.sif> <genomes_dir> <work_dir> [jobs] [chunk_size]
set -euo pipefail
HERE=$(dirname "$(realpath "$0")")
SIF=$(realpath "$1"); GENOMES=$2; WORK=$3; JOBS=${4:-12}; CHUNK=${5:-1000}
python3 "$HERE/make_inputs.py" "$GENOMES" "$WORK" "$CHUNK"
ls "$WORK"/*/chunks/chunk_*.faa \
  | xargs -P "$JOBS" -I{} sh -c 'f={}; bash '"$HERE"'/run_psortm.sh '"$SIF"' "$f" "${f%.faa}.out" > /dev/null'
python3 "$HERE/summarise.py" "$WORK"

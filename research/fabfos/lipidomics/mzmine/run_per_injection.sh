#!/usr/bin/env bash
# Run a batch once per .d injection, in parallel; outputs land in <out>/<polarity>/<injection>.
# Usage: run_per_injection.sh <batch.mzbatch> <out-dir> <jobs> <run.d>...
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
batch="$(realpath "$1")" out="$2" jobs="$3"; shift 3
one() {
  d="$1"; pol=$(basename "$(dirname "$d")"); name=$(basename "$d" .d | tr ' ' '_')
  dir="$out/$pol"; mkdir -p "$dir"
  [[ -s "$dir/${name}_full_feature_table.csv" ]] && return 0
  realpath "$d" > "$dir/$name.txt"
  "$here/run_mzmine.sh" "$batch" "$dir/$name.txt" "$dir/$name" > "$dir/$name.log" 2>&1 \
    && echo "ok $pol/$name" || echo "FAIL $pol/$name"
}
export -f one; export here batch out
printf '%s\0' "$@" | xargs -0 -P"$jobs" -n1 bash -c 'one "$0"'

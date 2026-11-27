#!/bin/bash
# Run the lane's psortm.sh on one psortm_prep.py chunk in the pinned image, timed and offline.
# usage: run_psortm.sh <psortm.sif> <chunk.faa> <out_dir>
set -euo pipefail
SIF=$1; FAA=$(realpath "$2"); OUT=$3
mkdir -p "$OUT"
OUT=$(realpath "$OUT")
cp "$FAA" "$OUT/chunk.faa"
cp "$(dirname "$(realpath "$0")")/../../src/metasmith_libraries/resources/lib/psortm/psortm.sh" "$OUT/"
/usr/bin/time -f "wall_s %e user_s %U sys_s %S maxrss_kb %M" -o "$OUT/time.txt" \
  apptainer exec --cleanenv --net --network none -B "$OUT:/work" --pwd /work "$SIF" \
  bash psortm.sh chunk.faa psortm_results.tsv > "$OUT/log.txt" 2>&1
cat "$OUT/time.txt"

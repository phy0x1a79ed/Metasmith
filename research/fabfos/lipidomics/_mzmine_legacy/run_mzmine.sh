#!/usr/bin/env bash
# Headless MZmine 4 lipidomics batch driver.
#
# Usage:
#   bash research/fabfos/lipidomics/run_mzmine.sh pos                    # full POS batch
#   bash research/fabfos/lipidomics/run_mzmine.sh neg                    # full NEG batch
#   bash research/fabfos/lipidomics/run_mzmine.sh pos --smoke 'Clone1_*' # smoke test on matching .d
#
# Output: data/fabfos/runs/scadc_lipidomics/processed/{pol}/aligned_features_{pol}.csv
#         data/fabfos/runs/scadc_lipidomics/processed/{pol}/mzmine.log
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

POL="${1:?usage: run_mzmine.sh {pos|neg} [--smoke <glob>]}"
shift || true

case "$POL" in
    pos) RAW_DIR="data/fabfos/runs/scadc_lipidomics/msms/POS"; BATCH="research/fabfos/lipidomics/pipeline_pos.mzbatch" ;;
    neg) RAW_DIR="data/fabfos/runs/scadc_lipidomics/msms/NEG"; BATCH="research/fabfos/lipidomics/pipeline_neg.mzbatch" ;;
    *)   echo "polarity must be pos or neg" >&2; exit 2 ;;
esac

SMOKE_GLOB=""
if [[ "${1:-}" == "--smoke" ]]; then
    SMOKE_GLOB="${2:?--smoke requires a glob like 'Clone1_*'}"
    shift 2
fi

OUT_DIR="data/fabfos/runs/scadc_lipidomics/processed/${POL}"
mkdir -p "$OUT_DIR"

if [[ -n "$SMOKE_GLOB" ]]; then
    INPUT_GLOB="${RAW_DIR}/${SMOKE_GLOB}"
    OUT_BASE="${OUT_DIR}/smoke"
else
    INPUT_GLOB="${RAW_DIR}/*.d"
    OUT_BASE="${OUT_DIR}/aligned_features_${POL}"
fi

LOG="${OUT_DIR}/mzmine.log"
echo "polarity=$POL  input=$INPUT_GLOB  out=$OUT_BASE  log=$LOG"

# MZmine 4 requires a (free) user login even for headless runs. The CLI accepts
# a saved user file via -user. The first time, do one of:
#   mamba run -n lipidomics mzmine --login-console
#   (or --login to open a browser; or run the GUI once and log in)
# After login a file lands at ~/.mzmine/users/*.mzuser — point MZUSER at it.
MZUSER="${MZUSER:-$HOME/.mzmine/users/$(ls -t "$HOME/.mzmine/users" 2>/dev/null | head -1)}"
USER_ARG=()
if [[ -f "$MZUSER" ]]; then
    USER_ARG=(-user "$MZUSER")
else
    echo "WARNING: no .mzuser file found at $MZUSER — MZmine will fail at the first" >&2
    echo "         post-import step. Run 'mamba run -n lipidomics mzmine --login-console' once." >&2
fi

# --ignore-parameter-warnings is appropriate here: our batch was derived from
# the upstream 4.8.8 reference but the env ships 4.7.30; warnings on cross-
# version parameter changes fall back to safe defaults (vetted upstream).
mamba run -n lipidomics mzmine \
    --batch "$BATCH" \
    --input "$INPUT_GLOB" \
    --output "$OUT_BASE" \
    --metadata research/fabfos/lipidomics/metadata.csv \
    --memory all \
    --ignore-parameter-warnings \
    "${USER_ARG[@]}" 2>&1 | tee "$LOG"

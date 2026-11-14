#!/usr/bin/env bash
# Autonomous MS-DIAL 5 lipidomics driver.
#
#   bash research/fabfos/lipidomics/run_msdial.sh pos                       # full POS batch
#   bash research/fabfos/lipidomics/run_msdial.sh neg                       # full NEG batch
#   bash research/fabfos/lipidomics/run_msdial.sh pos --smoke 'Clone1_S_*'  # smoke on matching .d
#
# Stages:
#   1. msconvert (ProteoWizard via Docker) each Bruker .d → mzML.
#      Uses --combineIonMobilitySpectra + --ddaProcessing so the PASEF
#      sub-scans collapse into the standard DDA layout MS-DIAL expects.
#      Skips files whose mzML already exists.
#   2. MSDIALCUI lcms -i <mzml_dir> -o <out_dir> -m <param.txt>.
#   3. Normalize the alignment matrix to `aligned_features_{pol}.csv` so the
#      _io.py loader contract stays intact.
#
# Why msconvert + Docker and not timsconvert:
#   MS-DIAL 5.5 Linux hangs reliably between "Peak picking" and
#   "Deconvolution started" when fed timsconvert mzML — the 4D-PASEF layout
#   that timsconvert emits is not compatible with MS-DIAL's deconvolution.
#   msconvert (via the chambm/pwiz Docker image, which bundles the Windows
#   Bruker SDK + Wine) produces a 3D LC-MS mzML that MS-DIAL deconvolves
#   correctly.
#
# Output: data/fabfos/runs/scadc_lipidomics/processed/{pol}/aligned_features_{pol}.csv
#         data/fabfos/runs/scadc_lipidomics/processed/{pol}/msdial.log
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

POL="${1:?usage: run_msdial.sh POL_pos_or_neg [--smoke GLOB]}"
shift || true

case "$POL" in
    pos) RAW_DIR="data/fabfos/runs/scadc_lipidomics/msms/POS"; PARAM="research/fabfos/lipidomics/pipeline_pos.msdial_param.txt" ;;
    neg) RAW_DIR="data/fabfos/runs/scadc_lipidomics/msms/NEG"; PARAM="research/fabfos/lipidomics/pipeline_neg.msdial_param.txt" ;;
    *)   echo "polarity must be pos or neg" >&2; exit 2 ;;
esac

SMOKE_GLOB=""
SUFFIX=""
if [[ "${1:-}" == "--smoke" ]]; then
    SMOKE_GLOB="${2:?--smoke requires a glob like 'Clone1_S_*'}"
    SUFFIX="_smoke"
    shift 2
fi

OUT_DIR="data/fabfos/runs/scadc_lipidomics/processed/${POL}${SUFFIX}"
MZML_DIR="${OUT_DIR}/mzml"
LOG="${OUT_DIR}/msdial.log"
mkdir -p "$MZML_DIR"

MSDIAL_BIN="lib/msdial/MSDIALCUI"
PWIZ_IMAGE="chambm/pwiz-skyline-i-agree-to-the-vendor-licenses"
if [[ ! -x "$MSDIAL_BIN" ]]; then
    echo "MS-DIAL binary not found at $MSDIAL_BIN" >&2
    echo "Run: bash lib/msdial/install.sh" >&2
    exit 3
fi
if [[ ! -f "$PARAM" ]]; then
    echo "param file not found at $PARAM" >&2
    echo "Run: mamba run -n lipidomics python research/fabfos/lipidomics/build_msdial_param.py" >&2
    exit 4
fi
if ! command -v docker >/dev/null; then
    echo "docker not installed — required for msconvert" >&2
    exit 5
fi
if ! docker image inspect "$PWIZ_IMAGE" >/dev/null 2>&1; then
    echo "pulling $PWIZ_IMAGE (~2.4 GB image, ~9 GB on disk)"
    docker pull "$PWIZ_IMAGE"
fi

echo "polarity=$POL  raw=$RAW_DIR  param=$PARAM  out=$OUT_DIR  log=$LOG"
echo "smoke_glob=${SMOKE_GLOB:-<none>}"
exec > >(tee "$LOG") 2>&1

# ---- 1) Convert .d → mzML (msconvert, idempotent per-file) ----
shopt -s nullglob
if [[ -n "$SMOKE_GLOB" ]]; then
    mapfile -t SOURCE_D < <(compgen -G "${RAW_DIR}/${SMOKE_GLOB}" || true)
else
    mapfile -t SOURCE_D < <(compgen -G "${RAW_DIR}/*.d" || true)
fi
shopt -u nullglob

if [[ ${#SOURCE_D[@]} -eq 0 ]]; then
    echo "no .d directories matched in ${RAW_DIR}" >&2
    exit 6
fi

echo "$(date -Iseconds) [convert] ${#SOURCE_D[@]} .d directories queued"
TO_CONVERT=()
for d in "${SOURCE_D[@]}"; do
    base="$(basename "$d" .d)"
    if [[ -s "${MZML_DIR}/${base}.mzML" ]]; then
        continue
    fi
    TO_CONVERT+=("$d")
done

if [[ ${#TO_CONVERT[@]} -gt 0 ]]; then
    echo "$(date -Iseconds) [convert] msconvert on ${#TO_CONVERT[@]} new file(s)"
    RAW_ABS="$(cd "$RAW_DIR" && pwd)"
    MZML_ABS="$(cd "$MZML_DIR" && pwd)"
    UID_GID="$(id -u):$(id -g)"
    # Don't pass --user: Wine inside the container needs /wineprefix64
    # writable by its in-container UID (root). Run as root inside, then
    # chown the resulting mzML back to the host user as the last step.
    for d in "${TO_CONVERT[@]}"; do
        base="$(basename "$d")"
        echo "$(date -Iseconds) [convert] ${base}"
        docker run --rm --entrypoint /bin/sh \
            -v "${RAW_ABS}":/data:ro \
            -v "${MZML_ABS}":/out \
            "$PWIZ_IMAGE" \
            -c "wine msconvert --mzML --64 \
                    --combineIonMobilitySpectra --ddaProcessing \
                    --filter 'peakPicking true 1-' \
                    --outdir /out \
                    '/data/${base}' \
                && chown -R ${UID_GID} /out" \
            || { echo "msconvert failed on $d" >&2; exit 7; }
    done
else
    echo "$(date -Iseconds) [convert] all mzML already present in $MZML_DIR"
fi

ls -lh "${MZML_DIR}"/*.mzML | tail -10

# ---- 2) MS-DIAL lcms ----
echo "$(date -Iseconds) [msdial] launching $MSDIAL_BIN lcms"
"$MSDIAL_BIN" lcms \
    -i "$MZML_DIR" \
    -o "$OUT_DIR" \
    -m "$PARAM"

# ---- 3) Normalize alignment matrix → aligned_features_{pol}.csv ----
ALIGN_TXT="$(find "$OUT_DIR" -maxdepth 2 -type f \( -iname 'AlignResult*.mdalign' -o -iname 'AlignmentResult*.msdial' -o -iname 'AlignResult*.msdial' -o -iname 'AlignResult*.txt' \) | head -1 || true)"
if [[ -z "$ALIGN_TXT" ]]; then
    echo "ERROR: could not locate alignment output in $OUT_DIR" >&2
    find "$OUT_DIR" -maxdepth 2 -type f
    exit 8
fi
OUT_CSV="${OUT_DIR}/aligned_features_${POL}.csv"
cp -f "$ALIGN_TXT" "$OUT_CSV"
echo "$(date -Iseconds) [done] alignment ${ALIGN_TXT##*/} → $(basename "$OUT_CSV")"
ls -lh "$OUT_CSV"

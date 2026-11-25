#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
docker run --rm --network none --cpus 2 --memory 3g -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$HERE:/ladder:ro" -w /tmp bixbench-ladder/base:fhda-v1.5.0 \
    python /ladder/check_specs.py "$@"

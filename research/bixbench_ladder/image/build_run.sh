#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CONTEXT=$(mktemp -d)
trap 'rm -rf "${CONTEXT:?}"' EXIT
cp "$HERE/metasmith" "$HERE/../../../src/metasmith/coms/cli/workflow.py" "$CONTEXT/"
docker build -f "$HERE/Dockerfile.run" -t "${1:-bixbench-ladder/run:dev}" "$CONTEXT"

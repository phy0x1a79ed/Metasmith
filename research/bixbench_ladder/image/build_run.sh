#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CONTEXT=$(mktemp -d)
trap 'rm -rf "${CONTEXT:?}"' EXIT
cp "$HERE/metasmith" "$HERE/bx" "$HERE/../generate.py" "$HERE/../../../src/metasmith/coms/cli/workflow.py" "$CONTEXT/"
mkdir "$CONTEXT/specs"
cp -r "$HERE/../specs/types" "$HERE/../specs/tools" "$CONTEXT/specs/"
docker build -f "$HERE/Dockerfile.run" -t "${1:-bixbench-ladder/run:dev}" "$CONTEXT"

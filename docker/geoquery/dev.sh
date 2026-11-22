#!/bin/bash
# Build the geoquery image locally under the tag geoquery.oci names. Metasmith's docker
# runtime falls back to the local tag when the registry pull fails, so no push is needed.
# Bump the tag for every change. Metasmith keys a leaf input on its path and mtime, minted
# once, so editing geoquery.oci alone leaves every cached step valid: the Invalidate below
# re-mints the container's id so the new image reruns every step.
set -euo pipefail
HERE=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SRC=$HERE/../../research/geospatial_query/poc/geoquery
CONTAINERS=$HERE/../../research/geospatial_query/msm/resources/containers
IMAGE=$(sed 's|^docker://||' "$CONTAINERS/geoquery.oci")
rm -rf "$HERE/geoquery" && cp -r "$SRC" "$HERE/geoquery"
trap 'rm -rf "$HERE/geoquery"' EXIT
DOCKER_BUILDKIT=1 docker build "$@" -t "$IMAGE" -f "$HERE/dockerfile" "$HERE"
PYTHONPATH=$HERE/../../src "${MSM_PYTHON:-$HOME/lib/miniforge3/envs/msm/bin/python}" -c \
    "import sys; from metasmith.python_api import DataInstanceLibrary as L; print(L.Load(sys.argv[1]).Invalidate(['geoquery.oci'])['moved'])" \
    "$CONTAINERS"

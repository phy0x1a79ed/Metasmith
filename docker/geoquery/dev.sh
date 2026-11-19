#!/bin/bash
# Build the geoquery image locally under the tag geoquery.oci names. Metasmith's docker
# runtime falls back to the local tag when the registry pull fails, so no push is needed.
# Bump the tag for every change: it is part of each step's cache key.
set -euo pipefail
HERE=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SRC=$HERE/../../research/geospatial_query/poc/geoquery
IMAGE=$(sed 's|^docker://||' "$HERE/../../research/geospatial_query/msm/resources/containers/geoquery.oci")
rm -rf "$HERE/geoquery" && cp -r "$SRC" "$HERE/geoquery"
trap 'rm -rf "$HERE/geoquery"' EXIT
DOCKER_BUILDKIT=1 docker build -t "$IMAGE" -f "$HERE/dockerfile" "$HERE"

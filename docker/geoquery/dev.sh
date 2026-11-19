#!/bin/bash
# Build the geoquery image locally. Metasmith's docker runtime falls back to the
# local tag when the registry pull fails, so no push is needed on this host.
set -euo pipefail
HERE=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SRC=$HERE/../../research/geospatial_query/poc/geoquery
IMAGE=geoquery:local
rm -rf "$HERE/geoquery" && cp -r "$SRC" "$HERE/geoquery"
trap 'rm -rf "$HERE/geoquery"' EXIT
DOCKER_BUILDKIT=1 docker build -t "$IMAGE" -f "$HERE/dockerfile" "$HERE"

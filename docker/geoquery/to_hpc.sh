#!/bin/bash
# Ship the local geoquery image to an HPC agent home as the .sif metasmith's apptainer
# runtime looks for, so the cluster never pulls from a registry.
# usage: to_hpc.sh <host> <agent_home>
set -euo pipefail
HOST=$1 HOME_DIR=$2
HERE=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
URI=$(cat "$HERE/../../research/geospatial_query/msm/resources/containers/geoquery.oci")
TAG=${URI#docker://}
SIF=$HOME_DIR/container_images/$(echo "$URI" | sed 's|://|..|; s|:|..|g; s|/|_|g').sif
TAR=$HOME_DIR/container_images/${TAG//[:\/]/_}.tar.gz
ssh "$HOST" "mkdir -p $HOME_DIR/container_images"
docker save "$TAG" | gzip -1 | ssh "$HOST" "cat > $TAR"
# unpack on node-local /tmp: a Lustre unpack takes over 20 minutes
ssh "$HOST" "set -e; module load apptainer; T=\$(mktemp -d /tmp/sif.XXXX); trap 'rm -rf \$T' EXIT
  APPTAINER_TMPDIR=\$T timeout -k 30 1500 apptainer build --force $SIF docker-archive://$TAR
  rm -f $TAR; apptainer exec --no-home --cleanenv $SIF python -c 'import geoquery.registry as r; print(len(list(r.specs())), \"specs\")'"

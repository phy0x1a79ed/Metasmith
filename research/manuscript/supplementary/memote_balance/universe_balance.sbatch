#!/bin/bash
#SBATCH --account=rpp-shallam
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=2:00:00
#SBATCH --output=/scratch/phyberos/e4_balance/universe_balance.%j.out
set -euo pipefail
D=/scratch/phyberos/e4_balance; mkdir -p $D/ub; export HOME=$D
apptainer exec --cleanenv --env PYTHONNOUSERSITE=1,HOME=$D -B $D \
  /scratch/phyberos/cache/apptainer/docker..quay.io_biocontainers_memote..0.17.0--pyhdfd78af_0.sif \
  python $D/universe_balance.py $D/univ/universe_122.xml.gz $D/univ/universe_166.xml.gz $D/ub

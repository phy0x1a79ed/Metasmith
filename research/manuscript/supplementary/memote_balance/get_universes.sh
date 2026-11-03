#!/bin/bash
#SBATCH --account=rpp-shallam
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=0:20:00
#SBATCH --output=/scratch/phyberos/e4_balance/getuniv.%j.out
set -euo pipefail
D=/scratch/phyberos/e4_balance; A=/scratch/phyberos/cache/apptainer; mkdir -p $D/univ
for v in 122:docker..quay.io_hallamlab_external_carveme..1.2.2.sif 166:docker..quay.io_hallamlab_external_carveme..1.6.6-py312.sif; do
  n=${v%%:*}; s=$A/${v#*:}
  export HOME=$PWD
  PD=$(PYTHONNOUSERSITE=1 apptainer exec --cleanenv --env PYTHONNOUSERSITE=1 $s python -c 'import importlib.util,os;print(os.path.dirname(importlib.util.find_spec("carveme").origin))')
  echo $n $PD
  apptainer exec --cleanenv --env PYTHONNOUSERSITE=1 $s sh -c "grep -E 'default_universe|default_flavor' $PD/config.cfg; pip list 2>/dev/null | grep -i -E 'carveme|framed|reframed|cobra|libsbml' || true"
  apptainer exec --cleanenv --env PYTHONNOUSERSITE=1 -B $D/univ $s cp $PD/data/generated/universe_bacteria.xml.gz $D/univ/universe_$n.xml.gz
done
ls -la $D/univ

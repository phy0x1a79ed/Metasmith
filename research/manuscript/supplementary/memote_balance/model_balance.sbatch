#!/bin/bash
#SBATCH --account=rpp-shallam
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=2:00:00
#SBATCH --output=/scratch/phyberos/e4_balance/model_balance.%j.out
set -euo pipefail
D=/scratch/phyberos/e4_balance; N=${N:-300}; export HOME=$D
MEMOTE=/scratch/phyberos/cache/apptainer/docker..quay.io_biocontainers_memote..0.17.0--pyhdfd78af_0.sif
cd $D/arch
for spec in bigg:B:122:166:e4abl-model_bigg universe:U:166:122:e4abl-model_universe; do
    IFS=: read arch rung uni other dir <<< "$spec"
    mkdir -p models_$rung
    tar --zstd -tf $arch.tar.zst | grep "/$dir/.*\.xml$" | shuf -n $N --random-source=<(yes) > list_$rung
    tar -C models_$rung --zstd -xf $arch.tar.zst -T list_$rung
    (apptainer exec --cleanenv --env PYTHONNOUSERSITE=1,HOME=$D,PYTHONPATH=$D -B $D $MEMOTE \
        python $D/model_balance.py $rung $D/univ/universe_$uni.xml.gz $D/univ/universe_$other.xml.gz models_$rung/results/$dir $D/model_balance_$rung.jsonl \
        > $D/model_balance_$rung.log 2>&1) &
done
wait

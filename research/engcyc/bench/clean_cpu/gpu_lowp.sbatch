#!/bin/bash
#SBATCH --account=def-shallam_gpu
#SBATCH --job-name=clean_lowp
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/scratch/phyberos/engcyc_pipeline/bench/clean_cpu/logs/%x_%j.log
# ESM-1b below bf16 on one GPU: torch 2.5.1+cu124 and torchao 0.7.0 installed over the image's torch onto
# node-local $SLURM_TMPDIR. Usage: sbatch --gpus=<gres>:1 gpu_lowp.sbatch <plan.tsv>
# Plan rows: name mode toks n input(mg|dh) save(0|1) compile(0|1).
set -euo pipefail
B=/scratch/phyberos/engcyc_pipeline/bench/clean_cpu
IMG=/scratch/phyberos/cache/apptainer/docker..quay.io_hallamlab_external_clean..2026.06.14.sif
MG=/project/6004975/phyberos/cyanoverse/data/orfs_and_metabuli/sequences-open_reading_frames/SRR27911466.faa
PLAN=$1
module load apptainer
hostname; nvidia-smi -L
apptainer exec --cleanenv -B $B,$SLURM_TMPDIR $IMG pip install -q --no-deps --target $SLURM_TMPDIR/cu \
  $B/wheels/cu124/*.whl $B/wheels/torchao-0.7.0-*.whl $B/wheels/fsspec-2024.10.0-py3-none-any.whl
envs="OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK,TORCH_HOME=/opt/torch_cache,PYTHONPATH=$SLURM_TMPDIR/cu"
envs="$envs,TRITON_CACHE_DIR=$SLURM_TMPDIR/triton,TORCHINDUCTOR_CACHE_DIR=$SLURM_TMPDIR/inductor,HOME=$SLURM_TMPDIR"
case "${CUDA_VISIBLE_DEVICES:-}" in MIG-*) envs="$envs,CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" ;; esac
mkdir -p $B/out/gpu
tail -n +2 $B/$PLAN | while read -r name mode toks n input save comp; do
  FA=$MG; [ "$input" = dh ] && FA=$B/inputs/dh10b.faa
  extra=""; [ "$save" = 1 ] || extra="--no-save"; [ "$comp" = 1 ] && extra="$extra --compile"
  echo "### $name $(date +%T)"
  apptainer exec --nv --cleanenv --env "$envs" -B $B,/project/6004975/phyberos/cyanoverse,$SLURM_TMPDIR $IMG \
    timeout ${ROW_TIMEOUT:-1800} python $B/embed.py --device cuda --fasta $FA --n $n --mode $mode --procs 1 \
    --threads $SLURM_CPUS_PER_TASK --toks $toks $extra --out $B/out/gpu/$name || echo "### FAILED $name"
  if [ "$save" = 1 ] && [ -f $B/out/gpu/$name.npy ]; then
    apptainer exec --cleanenv -B $B,$SLURM_TMPDIR $IMG python $B/calls.py --prefix $B/out/gpu/$name \
      --work $SLURM_TMPDIR/ws_$name --threads 8 --skip-stock || echo "### FAILED calls $name"
  fi
done
echo "### done $(date +%T)"

#!/bin/bash
#SBATCH --account=rpp-shallam
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=1:00:00
#SBATCH --output=/scratch/phyberos/e4_balance/per_test.%j.out
set -euo pipefail
D=/scratch/phyberos/e4_balance
python3 $D/per_test.py $D/in/e4_ablation_memote.tar $D/per_test_asbuilt.tsv
python3 $D/per_test.py $D/in/e4_ablation_rewrite.tar $D/per_test_rewritten.tsv

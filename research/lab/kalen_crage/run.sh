#!/bin/bash
#SBATCH --account=def-shallam_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --job-name=kalen_crage
#SBATCH --output=%x.%j.log
# Compare Kalen's three Plasmidsaurus EPI300 colonies with EPI300 and locate the pw34 CRAGE cargo.
#   sbatch run.sh   (from /scratch/phyberos/kalen_crage, with compare.py beside it)
set -euo pipefail
ROOT=/scratch/phyberos/kalen_crage
IMG=/scratch/phyberos/cache/apptainer
MM="apptainer exec -B $ROOT $IMG/docker..community.wave.seqera.io_library_minimap2_samtools..33bb43c18d22e29c.sif"
BL="apptainer exec -B $ROOT $IMG/docker..quay.io_biocontainers_blast..2.16.0--hc155240_2.sif"
REF=$ROOT/ref/GCF_052692645.1_ASM5269264v1_genomic.fna
OUT=$ROOT/out
mkdir -p $OUT
cd $ROOT

python3 compare.py features ref/pw34_methylation.gb $OUT/pw34_features.fa $OUT/pw34.fa

fmt="6 qseqid sseqid pident length qlen qstart qend sstart send evalue bitscore"
for c in 1 2 3; do
  asm=$ROOT/plasmidsaurus/XQTPYV_${c}_Colony_${c}/XQTPYV_${c}_Colony_${c}_1_reference.fasta
  $BL blastn -query $OUT/pw34_features.fa -subject $asm -outfmt "$fmt" -evalue 1e-10 > $OUT/c${c}_features.blast
  $BL blastn -query $OUT/pw34.fa -subject $asm -outfmt "$fmt" -evalue 1e-10 > $OUT/c${c}_pw34.blast
  $MM minimap2 -t 4 -cx asm5 --cs $REF $asm > $OUT/c${c}_vs_epi300.paf
  $MM sh -c "sort -k6,6 -k8,8n $OUT/c${c}_vs_epi300.paf | paftools.js call -l 1000 -L 1000 - > $OUT/c${c}_vs_epi300.var"
  $MM minimap2 -t 4 -cx asm5 $asm $REF > $OUT/epi300_vs_c${c}.paf
done
$BL blastn -query $OUT/pw34_features.fa -subject $REF -outfmt "$fmt" -evalue 1e-10 > $OUT/epi300_features.blast
for a in 1 2 3; do for b in 1 2 3; do
  [ $a -lt $b ] || continue
  $MM minimap2 -t 4 -cx asm5 --cs \
    plasmidsaurus/XQTPYV_${a}_Colony_${a}/XQTPYV_${a}_Colony_${a}_1_reference.fasta \
    plasmidsaurus/XQTPYV_${b}_Colony_${b}/XQTPYV_${b}_Colony_${b}_1_reference.fasta > $OUT/c${b}_vs_c${a}.paf
done; done

python3 compare.py report $ROOT $OUT

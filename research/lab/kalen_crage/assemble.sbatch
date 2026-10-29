#!/bin/bash
#SBATCH --account=def-shallam_cpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --job-name=kalen_assemble
#SBATCH --output=%x.%j.log
# Assemble Kalen's colonies from his reads and re-run the insertion call on our own assemblies.
# Nanopore at median Q22, which is flye's --nano-hq tier; hifiasm-meta would be the wrong tool.
set -euo pipefail
ROOT=/scratch/phyberos/kalen_crage
IMG=/scratch/phyberos/cache/apptainer
FL="apptainer exec -B $ROOT $IMG/docker..staphb_filtlong..0.3.1.sif"
FLYE="apptainer exec -B $ROOT $IMG/docker..staphb_flye..2.9.6.sif"
MM="apptainer exec -B $ROOT $IMG/docker..community.wave.seqera.io_library_minimap2_samtools..33bb43c18d22e29c.sif"
cd $ROOT
mkdir -p filtered ours out_reads

for c in 1 3; do
  col=XQTPYV_${c}_Colony_${c}
  if [ ! -s filtered/$col.fastq.gz ]; then
    $FL filtlong --min_length 1000 --keep_percent 95 reads/$col.fastq.gz | gzip > filtered/$col.fastq.gz
  fi
  if [ ! -s ours/$col/${col}_1_reference.fasta ]; then
    $FLYE flye --nano-hq filtered/$col.fastq.gz --genome-size 4.7m --threads 16 --out-dir flye_$col
    mkdir -p ours/$col
    cp flye_$col/assembly.fasta ours/$col/${col}_1_reference.fasta
    cp flye_$col/assembly_info.txt ours/$col/assembly_info.txt
  fi
  echo "=== $col flye contigs"
  cat ours/$col/assembly_info.txt
done

ASM_DIR=ours python3 insertion_call.py . out_reads XQTPYV_1_Colony_1 XQTPYV_3_Colony_3

REF=$ROOT/ref/GCF_052692645.1_ASM5269264v1_genomic.fna
for c in 1 3; do
  col=XQTPYV_${c}_Colony_${c}
  $MM minimap2 -t 16 -cx asm5 --cs $REF ours/$col/${col}_1_reference.fasta > out_reads/${col}_vs_epi300.paf
  $MM sh -c "sort -k6,6 -k8,8n out_reads/${col}_vs_epi300.paf | paftools.js call -l 1000 -L 1000 - > out_reads/${col}_vs_epi300.var"
  $MM minimap2 -t 16 -cx asm5 ours/$col/${col}_1_reference.fasta $REF > out_reads/epi300_vs_${col}.paf
  # Our assembly against the vendor's, to see whether the two agree on this colony at all.
  $MM minimap2 -t 16 -cx asm5 plasmidsaurus/$col/${col}_1_reference.fasta ours/$col/${col}_1_reference.fasta \
    > out_reads/${col}_ours_vs_vendor.paf
done
echo DONE

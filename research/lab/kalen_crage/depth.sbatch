#!/bin/bash
#SBATCH --account=def-shallam_cpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --job-name=kalen_depth
#SBATCH --output=%x.%j.log
# Read depth over the region the two colony 3 assemblies disagree on, colony 1 as the control.
set -euo pipefail
ROOT=/scratch/phyberos/kalen_crage
MM="apptainer exec -B $ROOT /scratch/phyberos/cache/apptainer/docker..community.wave.seqera.io_library_minimap2_samtools..33bb43c18d22e29c.sif"
cd $ROOT; mkdir -p depth
REF=ref/GCF_052692645.1_ASM5269264v1_genomic.fna
CTG=$(head -1 $REF | cut -c2- | cut -d" " -f1)
for c in 1 3; do
  col=XQTPYV_${c}_Colony_${c}
  [ -s depth/$col.bam ] || $MM sh -c "minimap2 -t 16 -ax map-ont $REF filtered/$col.fastq.gz | samtools sort -@4 -o depth/$col.bam - && samtools index depth/$col.bam"
  $MM samtools depth -a -r $CTG:2500001-2580000 depth/$col.bam | awk -v c=$col "{b=int((\$2-1)/1000); s[b]+=\$3; n[b]++} END{for(k in s) printf \"%s\t%d\t%.1f\n\", c, k*1000+1, s[k]/n[k]}" | sort -k2,2n > depth/${col}_region.tsv
  $MM samtools depth -a depth/$col.bam | awk "{s+=\$3;n++}END{printf \"genome mean depth %.1f\n\", s/n}" > depth/${col}_mean.txt
done
echo DONE

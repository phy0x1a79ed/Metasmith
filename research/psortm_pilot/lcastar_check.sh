#!/bin/bash
# Small offline check of the LCA*-fed lane: 200 ORFs from each of three pilot genomes, a
# synthetic contig_lcastar table, psortm_prep.py, then psortm.sh in the pinned image.
# usage: lcastar_check.sh <psortm.sif> <pilot_work_dir from run_pilot.sh> <out_dir>
set -euo pipefail
SIF=$(realpath "$1"); PILOT=$(realpath "$2"); W=$3
LIB=$(dirname "$(realpath "$0")")/../../src/metasmith_libraries/resources/lib/psortm
rm -rf "$W" && mkdir -p "$W/work"
W=$(realpath "$W")
cd "$W"
for g in ecoli bsubtilis hvolcanii; do
  awk -v n=200 '/^>/{c++} c<=n' $PILOT/$g/orfs.faa
done > orfs.faa
# a fourth contig with no LCA* call at all
printf '>nocall_1 # x\nMKKLLPTAAAGLLLLAAQPAMAMDIGINSDP\n' >> orfs.faa
printf 'contig\tlineage\trank\n' > lcastar.tsv
printf 'ecoli\td__Bacteria;p__Pseudomonadota;c__Gammaproteobacteria;o__Enterobacterales\torder\n' >> lcastar.tsv
printf 'bsubtilis\td__Bacteria;p__Bacillota;c__Bacilli\tclass\n' >> lcastar.tsv
printf 'hvolcanii\td__Archaea\tdomain\n' >> lcastar.tsv
python3 $LIB/psortm_prep.py --orfs orfs.faa --contig-taxonomy lcastar.tsv --chunk-size 1000 --out-dir chunks
cp chunks/chunk_0000.faa $LIB/psortm.sh work/
/usr/bin/time -f "wall_s %e user_s %U sys_s %S maxrss_kb %M" -o work/time.txt \
  apptainer exec --cleanenv --net --network none -B $W/work:/work --pwd /work \
  $SIF bash psortm.sh chunk_0000.faa psortm_results.tsv 2 > work/log.txt 2>&1
cat work/time.txt
python3 - "$W/work/psortm_results.tsv" <<'EOF'
import collections, csv, sys
rows = list(csv.DictReader(open(sys.argv[1]), delimiter="\t"))
c = collections.Counter((r["contig"], r["envelope"], r["localization"] or "(not run)") for r in rows)
print(len(rows), "rows")
for k, v in sorted(c.items()):
    print(*k, v, sep="\t")
EOF

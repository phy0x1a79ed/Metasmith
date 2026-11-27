#!/bin/bash
# Fetch RefSeq protein FASTAs for the pilot genomes.
# usage: fetch_genomes.sh <genomes_dir>
set -euo pipefail
OUT=$1
mkdir -p "$OUT"
cd "$OUT"
while read -r name acc; do
  [ -s "$name.faa" ] && continue
  curl -sfL -o "$name.zip" "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/$acc/download?include_annotation_type=PROT_FASTA"
  mkdir -p "x_$name" && unzip -qo "$name.zip" -d "x_$name"
  find "x_$name" -name protein.faa -exec cp {} "$name.faa" \;
  rm -rf "x_$name" "$name.zip"
  echo "$name $acc $(grep -c '>' "$name.faa")"
done <<'LIST'
ecoli GCF_000005845.2
bsubtilis GCF_000009045.1
vparvula GCF_000024945.1
dradiodurans GCF_000008565.1
mtuberculosis GCF_000195955.2
macetivorans GCF_000007345.1
paeruginosa GCF_000006765.1
scoelicolor GCF_000203835.1
btheta GCF_000011065.1
cglutamicum GCF_000011325.1
mpneumoniae GCF_000027345.1
hvolcanii GCF_000025685.1
LIST

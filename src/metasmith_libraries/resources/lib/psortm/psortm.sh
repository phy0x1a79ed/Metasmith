#!/bin/bash
# PSORTm on one chunk psortm_prep.py wrote, inside the psortm image.
# usage: psortm.sh <chunk.faa> <out.tsv>
# out.tsv: orf, mag, gtdb, envelope, localization, score; one row per ORF of the chunk.
set -euo pipefail
FAA=$1; OUT=$2
W=$PWD/psortm_work
B=/usr/local/psortb/bin
rm -rf "$W"
mkdir -p "$W/bin/taxon_predictor/taxonomy_files" "$W/results"

# BioPerl's taxonomy flatfile ties its four index files O_RDWR, which a read-only image
# refuses, so they are copied out; the .dmp sources are only read when an index is missing.
T=$B/taxon_predictor/taxonomy_files
cp "$T/nodes" "$T/id2names" "$T/names2id" "$T/parents" "$W/bin/taxon_predictor/taxonomy_files/"
ln -s "$T/nodes.dmp" "$T/names.dmp" "$W/bin/taxon_predictor/taxonomy_files/"
cp "$B/taxon_predictor/Gram_stain_predictor_parser.pl" "$W/bin/taxon_predictor/"
cp "$B/psortb3.pl" "$W/bin/"
# psort writes under a hard-coded /tmp/results.
sed "s|^our \$resultsdir = '/tmp/results';|our \$resultsdir = '$W/results';|" "$B/psort" > "$W/bin/psort"
grep -q "resultsdir = '$W/results'" "$W/bin/psort"
chmod +x "$W/bin/"*.pl "$W/bin/psort" "$W/bin/taxon_predictor/"*.pl

# The splitter keys a protein to its taxonomy line by stripping a Prodigal `_<n> <desc>`
# tail from the header, so each ORF goes in as `<orf>_1 x` and its taxonomy line as `<orf>`.
awk -F'\t' -v OFS='\t' -v tax="$W/tax.csv" -v tag="$W/tags.tsv" '
  /^>/ { id=substr($1,2); print ">" id "_1 x"; print id "," $3 > tax; print id, $2, $4 > tag; next }
  { print }' "$FAA" > "$W/in.faa"

SEQFILE=$W/in.faa TAXFILE=$W/tax.csv MOUNT=$W/results perl "$W/bin/psort" -v

# One results table per envelope PSORTm ran; ORFs it put in `undetermined` were not run.
awk -F'\t' -v OFS='\t' '
  FILENAME ~ /tags\.tsv$/ { tag[$1]=$2 OFS $3; next }
  FNR==1 { env=FILENAME; sub(/.*[0-9]_/,"",env); sub(/_results\.tab$|\.fasta$/,"",env) }
  env=="undetermined" { if (/^>/) { id=substr($1,2); sub(/[ \t].*/,"",id); sub(/_1$/,"",id); print id, tag[id], env, "", "" }; next }
  FNR>1 && NF>=3 { id=$1; sub(/ .*/,"",id); sub(/_1$/,"",id); print id, tag[id], env, $2, $3 }
' "$W/tags.tsv" $(ls "$W"/results/*_results.tab) "$W"/results/*_undetermined.fasta > "$OUT.rows"
{ printf 'orf\tmag\tgtdb\tenvelope\tlocalization\tscore\n'; cat "$OUT.rows"; } > "$OUT"
rm -f "$OUT.rows"
cat "$W"/results/*_warnings.txt >&2 || true
rm -rf "$W"

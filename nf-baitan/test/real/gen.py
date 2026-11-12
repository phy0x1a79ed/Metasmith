"""Writes two separately generated workflows for the live sockeye run: E. coli K-12 -> prodigal -> DIAMOND UniRef50.
The inputs are imports held by the sockeye provider, so Nextflow sees empty local stubs; each process carries the
declared set (givens = the index YAML props) that makes it the same offer in both workflows.
Usage: gen.py OUT_DIR STUB_DIR"""
import os, sys
from metasmith.models.workflow.baitan_decl import ext_line

out, stub = sys.argv[1:3]
os.makedirs(stub, exist_ok=True)
genome, db = f"{stub}/ecoli.fna", f"{stub}/uniref50.dmnd"
for p in (genome, db):
    open(p, "a").close()

DATA = "/scratch/st-shallam-1/txyliu/baitan-data"
PRODIGAL = {"contract": "prodigal", "version": "2.6.3", "source": "", "params": {"mode": "single", "format": "gff"},
            "givens": {genome: {"kind": "assembly", "name": "GCF_000005845.2", "organism": "Escherichia coli K-12 MG1655"}}}
OUTFMT = "6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore"
DIAMOND = {"contract": "diamond_uniref50", "version": "2.1.11", "source": "",
           "params": {"outfmt": OUTFMT, "evalue": "1e-5", "max_target_seqs": "1", "sensitivity": "sensitive"},
           "givens": {db: {"kind": "refdb", "name": "uniref50", "format": "diamond"}}}


def workflow(publish: bool, tag: str) -> str:
    pub = "    publishDir 'results', mode: 'copy'\n" if publish else ""
    return f"""// {tag}
process prodigal {{
{pub}    cpus 1
    memory '4 GB'
    {ext_line(PRODIGAL)}
    input: path assembly
    output: path 'orfs.faa'
    script: "{DATA}/bin/prodigal -i $assembly -a orfs.faa -o orfs.gff -f gff -p single -q"
}}
process diamond {{
{pub}    cpus 8
    memory '64 GB'
    {ext_line(DIAMOND)}
    input: path orfs; path db
    output: path 'hits.tsv'
    script: "/arc/project/st-shallam-1/pwy_group/lib/diamond/diamondx blastp --query $orfs --db $db --out hits.tsv --threads 8 --block-size 10 --outfmt {OUTFMT} --max-target-seqs 1 --evalue 1e-5 --sensitive"
}}
workflow {{ diamond(prodigal(file('{genome}')), file('{db}')) }}
"""


os.makedirs(out, exist_ok=True)
open(f"{out}/wf1.nf", "w").write(workflow(True, "workflow 1: publishes both targets at sockeye"))
open(f"{out}/wf2.nf", "w").write(workflow(False, "workflow 2: same steps, nothing to place"))

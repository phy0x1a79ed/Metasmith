"""Writes a metasmith-style workflow into RUN: `binning` declares two metric axes and a CheckM checker, and the plan
then reaches its own `checkm` step on the same bins. The checkm declaration is built once and shared. Usage: gen_l3.py RUN"""
import os, sys
from metasmith.models.workflow.baitan_decl import ext_line

run = sys.argv[1]
os.makedirs(f"{run}/data")
db = f"{run}/data/checkmdb.dat"
open(db, "w").write("db\n")
CHECKM = {"contract": "checkm", "version": "1", "source": "c1", "params": {},
          "givens": {db: {"kind": "refdb", "name": "checkm", "version": "1"}}}
REPORT = r"printf 'Bin\tCompleteness\tContamination\nb1\t90\t2\nb2\t70\t4\n' > checkm.tsv"
binning = {"contract": "binning", "version": "1", "source": "b1", "params": {}, "givens": {},
           "axes": [{"name": "completeness", "column": "Completeness", "higher_better": True, "weight": 0.0},
                    {"name": "contamination", "column": "Contamination", "higher_better": False, "weight": 0.0}],
           "checker": {**CHECKM, "script": f"test -s input/bins/b1.fa\n{REPORT}", "report": "checkm.tsv", "input": "input"}}

open(f"{run}/wf_c.nf", "w").write(f"""
process binning {{
    {ext_line(binning)}
    output: path 'bins'
    script: "mkdir bins; echo a > bins/b1.fa; echo b > bins/b2.fa"
}}
process checkm {{
    publishDir 'out', mode: 'copy'
    {ext_line(CHECKM)}
    input: path bins; path db
    output: path 'checkm.tsv'
    script: "test -s bins/b1.fa; {REPORT.replace(chr(92), chr(92) * 2)}"
}}
workflow {{ checkm(binning(), file('{db}')) }}
""")

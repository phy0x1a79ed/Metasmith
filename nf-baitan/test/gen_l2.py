"""Writes two metasmith-style workflows into RUN: both run `shared` on one sample and one declared reference
database; the second adds `extra` on shared's output. Each process carries the `ext baitan` line
metasmith's generator emits. Usage: gen_l2.py RUN"""
import os, sys
from metasmith.models.workflow.baitan_decl import ext_line

run = sys.argv[1]
os.makedirs(f"{run}/data")
open(f"{run}/data/sample.txt", "w").write("sample\n")
open(f"{run}/data/toydb.dmnd", "w").write("db-v1\n")
DB = {"kind": "refdb", "name": "toy", "version": "1"}
shared = {"contract": "shared", "version": "1", "source": "s1", "params": {"mode": "fast"},
          "givens": {f"{run}/data/sample.txt": {"msm": "sample-1"}, f"{run}/data/toydb.dmnd": DB}}
extra = {"contract": "extra", "version": "1", "source": "e1", "params": {}, "givens": {}}

PROCS = f"""
process shared {{
    publishDir 'out', mode: 'copy'
    {ext_line(shared)}
    input: path sample; path db
    output: path 'shared.txt'
    script: "cat $sample $db > shared.txt"
}}
process extra {{
    publishDir 'out', mode: 'copy'
    {ext_line(extra)}
    input: path s
    output: path 'extra.txt'
    script: "cp $s extra.txt"
}}
"""
FLOW = "workflow {{ shared(file('{d}/sample.txt'), file('{d}/toydb.dmnd')){tail} }}"
open(f"{run}/wf_a.nf", "w").write(PROCS + FLOW.format(d=f"{run}/data", tail=""))
open(f"{run}/wf_b.nf", "w").write(PROCS + FLOW.format(d=f"{run}/data", tail=" | extra"))

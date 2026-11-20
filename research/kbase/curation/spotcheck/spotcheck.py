#!/usr/bin/env python3
"""Solve the metasmith equivalent of six randomly drawn KBase narratives.

The shapes come from curation/r1/shapes.jsonl: copies >= 2, every app in the catalog,
two to six scientific steps, drawn with random.seed(20261119). Each spec supplies what
the narrative's author started from and targets what the narrative ended with.

    PYTHONPATH=src mamba run -n msm python research/kbase/curation/spotcheck/spotcheck.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "research" / "metasmith_libraries"))

from probe_kbase_parity import DEFERRED, MLIB, Spec, _lib, _rnaseq_inputs, _types, run  # noqa: E402

GROUPS = ("logistics", "assembly", "metagenomics", "functionalAnnotation",
          "transcriptomics", "pangenome", "kbase")
LIBS = [MLIB / "transforms" / g for g in GROUPS]
RES = [MLIB / "resources" / "env", MLIB / "resources" / "lib"]


def _reads(lib, parent=None):
    meta = lib.AddValue("read_metadata.json", {"parity": "paired", "length_class": "short"},
                        "sequences::read_metadata", parents={parent} if parent else set())
    pair = lib.AddValue("read_pair.txt", "lib_1", "sequences::read_pair", parents={meta})
    lib.AddItem(DEFERRED, "sequences::zipped_forward_short_reads", parents={pair})
    lib.AddItem(DEFERRED, "sequences::zipped_reverse_short_reads", parents={pair})
    return meta


def _spec(inputs, targets):
    return Spec(input_library=_lib(inputs), sample_type=None, target_types=targets,
                transform_libraries=LIBS, resource_libraries=RES)


def s0205_tree_then_blast():
    def inputs(lib):
        _types(lib, "sequences", "annotation", "ref", "taxonomy")
        lib.AddItem(DEFERRED, "sequences::isolate_assembly")
        lib.AddItem(DEFERRED, "ref::gtdb")
    return _spec(inputs, ["taxonomy::gtdbtk_tree", "annotation::homolog_hits"])


def s0120_bin_then_checkm():
    def inputs(lib):
        _types(lib, "sequences", "ref", "taxonomy", "binning", "alignment")
        meta = _reads(lib)
        lib.AddItem(DEFERRED, "sequences::assembly", parents={meta})
    return _spec(inputs, ["sequences::metabat2_bin_fasta",
                          {"type": "taxonomy::checkm_stats", "parents": [0]}])


def s0182_annotate_tree_blast():
    def inputs(lib):
        _types(lib, "sequences", "annotation", "ref", "taxonomy")
        lib.AddItem(DEFERRED, "sequences::isolate_assembly")
        lib.AddItem(DEFERRED, "annotation::bakta_db")
        lib.AddItem(DEFERRED, "ref::gtdb")
    return _spec(inputs, ["annotation::bakta_annotated_proteins",
                          "sequences::gbk", "taxonomy::gtdbtk_tree",
                          "annotation::homolog_hits"])


def s0127_trim_qc_map():
    def inputs(lib):
        _types(lib, "sequences", "alignment", "ref")
        meta = _reads(lib)
        lib.AddItem(DEFERRED, "sequences::assembly", parents={meta})
    return _spec(inputs, ["sequences::fastqc_html_report", "sequences::clean_short_reads",
                          "alignment::bam"])


def s0186_rnaseq_de_go():
    def inputs(lib):
        _rnaseq_inputs(lib)
        lib.AddItem(DEFERRED, "ref::interproscan_data")
    return _spec(inputs, ["transcriptomics::bowtie2_bam",
                          {"type": "transcriptomics::stringtie_quant_gtf", "parents": [0]},
                          {"type": "transcriptomics::diff_count_table", "parents": [1]},
                          "annotation::go_overrepresentation"])


def s0186b_rnaseq_de_only():
    def inputs(lib):
        _rnaseq_inputs(lib)
    return _spec(inputs, ["transcriptomics::bowtie2_bam",
                          {"type": "transcriptomics::stringtie_quant_gtf", "parents": [0]},
                          {"type": "transcriptomics::diff_count_table", "parents": [1]}])


def s0195_annotate_classify():
    def inputs(lib):
        _types(lib, "sequences", "annotation", "ref", "taxonomy")
        lib.AddItem(DEFERRED, "sequences::isolate_assembly")
        lib.AddItem(DEFERRED, "annotation::bakta_db")
        lib.AddItem(DEFERRED, "ref::gtdb")
    return _spec(inputs, ["annotation::bakta_annotated_proteins", "taxonomy::gtdbtk"])


CASES = [s0205_tree_then_blast, s0120_bin_then_checkm, s0182_annotate_tree_blast,
         s0127_trim_qc_map, s0186_rnaseq_de_go, s0186b_rnaseq_de_only, s0195_annotate_classify]


def main() -> int:
    want = set(sys.argv[1:])
    out = HERE / "spotcheck.jsonl"
    recs = []
    for fn in CASES:
        if want and fn.__name__ not in want:
            continue
        print(f"[{fn.__name__}]", flush=True)
        rec = run(fn.__name__, fn, fn.__doc__ or "", "", "")
        recs.append(rec)
        print(f"  ok={rec['ok']} steps={rec['steps']} {rec['reason']} dropped={rec.get('dropped')}"
              f" {rec.get('error','')}", flush=True)
        for p in rec["picked"]:
            print(f"     {p}")
    out.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return 0


if __name__ == "__main__":
    sys.exit(main())

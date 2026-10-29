#!/usr/bin/env python3
"""Emit the `crage` mock library: its type file and one stub transform per TABLE row.

The stubs fill the gaps between the standard library's real transforms in the proposed pipeline
for Kalen's three Plasmidsaurus colonies. Each stub's model is the proposal; its body only
touches its outputs. A row names, in `src`, the existing script it stands in for, or `proposed`
when nothing does yet.

    python research/kalen_crage/mocklib/generate.py
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
TYPES_YML = HERE / "data_types" / "crage.yml"
TRANSFORMS = HERE / "transforms" / "crage"

FILE, DIR = "file", "dir"

# `_` is a matched property, so a distinct description keeps any two of these from standing in
# for one another.
TYPES: dict[str, tuple[str, dict]] = {
    "run": (FILE, {"_": "one Plasmidsaurus order: the colonies sequenced together", "ext": "txt"}),
    "insertion_plasmid": (FILE, {"_": "the CRAGE insertion plasmid as delivered by the depositor, annotated", "ext": "gb"}),
    "plasmid_features": (FILE, {"_": "each annotated feature of the insertion plasmid as its own nucleotide record", "ext": "fna"}),
    "cargo_hits": (FILE, {"_": "insertion-plasmid features aligned to one colony assembly, with coordinates", "ext": "tsv"}),
    "cargo_locus": (FILE, {"_": "where the cargo sits in one colony, its junctions, and which features survived", "ext": "tsv"}),
    "structural_diff": (FILE, {"_": "insertions, deletions and duplications of one colony against the parent genome", "ext": "tsv"}),
    "small_variants": (FILE, {"_": "SNPs and short indels of one colony against the parent genome, in gene context", "ext": "tsv"}),
    "clone_relatedness": (FILE, {"_": "every pair of colonies in one order, by aligned length and differing bases", "ext": "tsv"}),
    "modified_base_bam": (FILE, {"_": "basecaller alignment carrying per-read modified-base tags", "ext": "bam"}),
    "methylation_profile": (FILE, {"_": "per-site methylation fraction and read depth for one colony", "ext": "tsv"}),
    "motif_report": (FILE, {"_": "methylation at each motif the transferred methyltransferases target", "ext": "tsv"}),
    "annotation_summary": (FILE, {"_": "one colony's annotated genes, with the cargo's own genes marked", "ext": "tsv"}),
    "report": (FILE, {"_": "one readable account of the cargo, the genome differences and the methylation", "ext": "html"}),
}


@dataclass
class T:
    name: str
    src: str
    requires: list[tuple[str, str, list[str]]]
    products: list[tuple[str, str, list[str]]]
    group_by: str
    note: str = ""
    cpus: int = 2
    memory_gb: int = 4
    hours: int = 1


def r(var, dtype, *parents):
    return var, dtype, list(parents)


RUN = r("run", "crage::run")
META = r("meta", "sequences::read_metadata", "run")
# A colony's assembly descends from both the order and that colony's read metadata. Per-colony
# steps key on the metadata, so one colony's assembly never meets another's reads or alignment;
# the one run-level step keys on the order, so it sees all three at once. A deferred input cannot
# descend from an assembly the plan has yet to build, which is why the delivered alignment hangs
# off the metadata too.
ASM = r("asm", "sequences::flye_assembly", "meta")
ASM_RUN = r("asm", "sequences::flye_assembly", "run")
# The parent genome must be the published one, so it is required under the genome name that the
# accession hangs off: only the NCBI download descends from that. Asking for a bare
# isolate_assembly instead lets the planner satisfy the reference by assembling the colony's own
# reads a second way, which would compare each colony against itself.
NAME = r("name", "ncbi::genome_name", "run")
REF = r("ref", "sequences::isolate_assembly", "name")

TABLE: list[T] = [
    T("plasmid_features", "research/lab/kalen_crage/compare.py (features arm)",
      [r("plasmid", "crage::insertion_plasmid")],
      [("out", "crage::plasmid_features", ["plasmid"])], group_by="plasmid",
      note="""Each annotated feature becomes its own record, so a cargo that lost part of itself
      reports which part. Reading the features rather than the whole plasmid is what separates
      the integrated cargo from the delivery backbone, which should not be there at all."""),
    T("cargo_blast", "research/lab/kalen_crage/run.sh (blastn arm)",
      [RUN, META, ASM, r("features", "crage::plasmid_features", "run")],
      [("hits", "crage::cargo_hits", ["asm"])], group_by="asm",
      note="""blastn of each plasmid feature against one colony. The library's blast_homolog_hits
      is protein ORFs against an assembly; locating a cargo needs nucleotide alignment and the
      subject coordinates of every hit, which is what names the insertion site."""),
    T("cargo_locus", "proposed",
      [RUN, META, ASM, r("hits", "crage::cargo_hits", "asm"), NAME, REF],
      [("locus", "crage::cargo_locus", ["asm"])], group_by="asm",
      note="""The landing-pad answer. Merges the hits into one span, then reads the colony
      sequence just outside each end back onto the parent genome to name the junctions. Reports
      which features are present and at what identity, and which are missing. Both recombinase
      sites and an intact cargo between them is an insertion that went in as intended; a cargo
      with backbone attached, or only one site, is not. Assembly coordinates are circular, so a
      junction at a contig's origin must be resolved the long way round rather than reported as
      position zero."""),
    T("reference_diff", "research/lab/kalen_crage/compare.py (report arm)",
      [RUN, META, ASM, NAME, REF],
      [("structural", "crage::structural_diff", ["asm"]),
       ("small", "crage::small_variants", ["asm"])], group_by="asm",
      note="""minimap2 asm5 of one colony against the parent genome, then paftools.js call.
      Separates what the engineering did from what the strain already carried: the cargo span
      itself comes back as an insertion, so it is labelled as such rather than counted as a
      difference. Each difference is named by the genes it covers."""),
    T("clone_compare", "research/lab/kalen_crage/run.sh (pairwise arm)",
      [RUN, ASM_RUN],
      [("out", "crage::clone_relatedness", ["run"])], group_by="run",
      note="""Every pair of colonies in the order, aligned to each other. Colonies picked from
      one transformation are often siblings rather than independent events, and that changes what
      a difference in a single colony means."""),
    T("methylation_pileup", "proposed",
      [RUN, META, ASM, r("bam", "crage::modified_base_bam", "meta")],
      [("out", "crage::methylation_profile", ["asm"])], group_by="asm",
      note="""modkit pileup over the modified-base tags. Needs a basecaller alignment that
      carries those tags: plain FASTQ reads cannot answer this, and neither can an assembly."""),
    T("motif_methylation", "proposed",
      [RUN, META, ASM, r("profile", "crage::methylation_profile", "asm"),
       r("features", "crage::plasmid_features", "run")],
      [("out", "crage::motif_report", ["asm"])], group_by="asm",
      note="""Each transferred methyltransferase names its target motif in the plasmid
      annotation. Methylation at those motifs, and not elsewhere, is what shows the transferred
      enzymes are working rather than merely present."""),
    T("colony_annotation", "proposed",
      [RUN, META, ASM,
       r("uniref", "annotation::diamond_uniref50_descriptions", "asm"),
       r("kofam", "annotation::kofamscan_descriptions", "asm")],
      [("out", "crage::annotation_summary", ["asm"])], group_by="asm",
      note="""Requiring the annotation to descend from the colony's own assembly is what puts
      prodigal on the colony rather than letting the planner answer with the parent genome's
      ORFs, which arrive free with the reference download and would annotate the wrong genome.
      Marks the cargo's genes using the locus, so the apramycin marker and both
      methyltransferases are named from the colony's own calls rather than assumed."""),
    T("crage_report", "proposed",
      [RUN,
       r("locus", "crage::cargo_locus", "run"),
       r("structural", "crage::structural_diff", "run"),
       r("small", "crage::small_variants", "run"),
       r("relatedness", "crage::clone_relatedness", "run"),
       r("stats", "sequences::assembly_stats", "run"),
       r("motifs", "crage::motif_report", "run"),
       r("annotation", "crage::annotation_summary", "run")],
      [("out", "crage::report", ["run"])], group_by="run",
      note="""One page per order, written for the depositor: whether each colony carries the
      cargo, where it went, what else changed, and whether the colonies are siblings."""),
]

BANNER = "# generated by research/kalen_crage/mocklib/generate.py -- do not hand-edit\n"


def write_types() -> None:
    out = [BANNER, "types:\n"]
    for name, (_kind, props) in TYPES.items():
        out.append(f"  {name}:\n    properties:\n")
        for k, v in props.items():
            out.append(f"      {k}: {v!r}\n" if ":" in str(v) else f"      {k}: {v}\n")
    TYPES_YML.parent.mkdir(parents=True, exist_ok=True)
    TYPES_YML.write_text("".join(out))


def stub(row: T) -> str:
    head = [BANNER, f'"""{row.name} -- stands in for: {row.src}\n']
    if row.note:
        head.append("\n" + textwrap.fill(" ".join(row.note.split()), 90) + "\n")
    head.append('\nStub: the model is the proposal, the body only touches its outputs.\n"""\n\n')
    pad = max(len(v) for v, *_ in row.requires + row.products)
    body = ["from metasmith.python_api import *\n\n",
            "lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)\n",
            "model = Transform()\n"]
    for var, dtype, parents in row.requires:
        p = ", parents={%s}" % ", ".join(parents) if parents else ""
        body.append(f'{var:<{pad}} = model.AddRequirement(lib.GetType("{dtype}"){p})\n')
    for var, dtype, parents in row.products:
        p = ", parents={%s}" % ", ".join(parents) if parents else ""
        body.append(f'{var:<{pad}} = model.AddProduct(lib.GetType("{dtype}"){p})\n')
    dirs = {v for v, d, _ in row.products if d.startswith("crage::")
            and TYPES[d.split("::")[1]][0] == DIR}
    body += [
        "\n\ndef protocol(context: ExecutionContext):\n",
        "    made = {%s}\n" % ", ".join(f"{v}: context.Output({v})" for v, _, _ in row.products),
        "    for key, path in made.items():\n",
        "        make = 'mkdir -p' if key in _DIRECTORY_PRODUCTS else 'touch'\n",
        "        context.external_shell.Exec(f'{make} {path.external}')\n",
        "    return ExecutionResult(\n",
        "        manifest=[{k: v.local for k, v in made.items()}],\n",
        "        success=all(v.local.exists() for v in made.values()),\n",
        "    )\n\n\n",
        "_DIRECTORY_PRODUCTS = %s\n\n" % ("{%s}" % ", ".join(sorted(dirs)) if dirs else "set()"),
        "TransformInstance(\n",
        "    protocol=protocol,\n",
        "    model=model,\n",
        f"    group_by={row.group_by},\n",
        f"    resources=Resources(cpus={row.cpus}, memory=Size.GB({row.memory_gb}), duration=Duration(hours={row.hours})),\n",
        ")\n",
    ]
    return "".join(head + body)


def write_transforms() -> None:
    TRANSFORMS.mkdir(parents=True, exist_ok=True)
    for old in TRANSFORMS.glob("*.py"):
        if old.read_text().startswith(BANNER):
            old.unlink()
    for row in TABLE:
        (TRANSFORMS / f"{row.name}.py").write_text(stub(row))


if __name__ == "__main__":
    write_types()
    write_transforms()
    print(f"{len(TYPES)} types, {len(TABLE)} stubs")

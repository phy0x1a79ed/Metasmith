#!/usr/bin/env python3
import sys

import _authoring as A
from metasmith.python_api import DEFERRED, Spec, Template

NAME = "viromics_survey_from_assembly"
DESCRIPTION = """
Call viral contigs from an assembly with VirSorter2 and geNomad, and quantify
crAssphage coverage in the clean reads as a faecal-source marker. Cluster the
viral contigs into vOTUs and annotate each with DRAM-v, which reports its
auxiliary metabolic genes.
"""

TARGETS = [
    "annotation::virsorter2_viral_sequences",
    "taxonomy::genomad_virus_summary",
    "taxonomy::genomad_plasmid_summary",
    "annotation::crassphage_coverage",
    "annotation::dramv_amg_summary",
]


def build_template(rebuild: bool = False) -> Template:
    def inputs(lib):
        for tl in ("sequences.yml", "annotation.yml", "taxonomy.yml", "ref.yml",
                   "viromics.yml"):
            lib.AddTypeLibrary(A.TYPES / tl)
        study = lib.AddValue("contig_study.json", {"logistics": "contig study"},
                             "viromics::contig_study")
        meta = lib.AddValue("sample_reads_metadata.json",
                            {"parity": "paired", "length_class": "short"},
                            "sequences::read_metadata", parents={study})
        lib.AddValue("eggnog_source.json", {"release": "emapperdb-5.0.2"},
                     "annotation::eggnog_source")
        asm = lib.AddItem(DEFERRED, "sequences::assembly", parents={meta})
        lib.AddItem(DEFERRED, "sequences::clean_short_reads", parents={asm})

    return Template(
        name=NAME, description=DESCRIPTION.strip(),
        cases=[Spec(
            input_library=A.deferred_inputs(NAME, inputs, rebuild=rebuild),
            shared_input_paths=["contig_study.json", "eggnog_source.json"],
            target_types=TARGETS,
        )],
        transform_libraries=A.transforms(
            "logistics", "metagenomics", "functionalAnnotation", "viromics"),
        resource_libraries=[A.envs(), A.MLIB / "resources" / "lib", A.MLIB / "resources" / "ref"],
    )


if __name__ == "__main__":
    A.cli(sys.modules[__name__])

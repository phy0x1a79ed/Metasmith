"""PSORTm's envelope comes from the taxon name it is handed, so the GTDB-to-PSORTm translation
decides every protein's envelope, and a wrong row is silent."""

import subprocess
import sys

import pytest

from conftest import MLIB

PREP = MLIB / "resources" / "lib" / "psortm" / "psortm_prep.py"
sys.path.insert(0, str(PREP.parent))
import psortm_prep  # noqa: E402


@pytest.mark.parametrize("lineage, taxon", [
    ("d__Bacteria;p__Pseudomonadota;c__Gammaproteobacteria", "Proteobacteria"),
    ("d__Bacteria;p__Desulfobacterota_I;c__Desulfovibrionia", "Proteobacteria"),
    ("d__Bacteria;p__Bacillota_C;c__Negativicutes;o__Veillonellales", "Firmicutes"),
    ("d__Bacteria;p__Bacillota;c__Bacilli;o__Mycoplasmatales", "Tenericutes"),
    ("d__Bacteria;p__Actinomycetota;c__Actinomycetes", "Actinobacteria"),
    ("d__Bacteria;p__Deinococcota;c__Deinococci", "Deinococcus-Thermus"),
    ("d__Archaea;p__Halobacteriota;c__Methanosarcinia", "Archaea"),
    ("d__Bacteria;p__Patescibacteriota;c__Paceibacteria", "Patescibacteriota"),
    ("d__Bacteria;p__;c__", "Bacteria"),
    ("Unclassified Bacteria", None),
])
def test_gtdb_lineage_becomes_the_name_psortm_resolves(lineage, taxon):
    assert psortm_prep.psortm_taxon(lineage) == taxon


def test_every_orf_is_chunked_and_only_a_phylum_call_is_run(tmp_path):
    (tmp_path / "orfs.faa").write_text(
        ">k141_1_1 # 1 # 90 # 1\nMKV*\n>k141_2_1 # 1 # 90 # 1\nMAA\n>k141_9_1 # 1 # 90 # 1\nMGG\n")
    (tmp_path / "lcastar.tsv").write_text(
        "contig\tlineage\trank\n"
        "k141_1\td__Bacteria;p__Bacteroidota;c__Bacteroidia\tclass\n"
        "k141_2\td__Archaea\tdomain\n")
    subprocess.run([sys.executable, str(PREP), "--orfs", str(tmp_path / "orfs.faa"),
                    "--contig-taxonomy", str(tmp_path / "lcastar.tsv"), "--chunk-size", "1",
                    "--out-dir", str(tmp_path / "chunks")], check=True)
    records = sorted(p.read_text() for p in (tmp_path / "chunks").glob("chunk_*.faa"))
    # `Bacteria` is a name PSORTm leaves undetermined: the domain-only and uncalled ORFs keep a row
    assert records == [
        ">k141_1_1\tk141_1\tBacteroidetes\td__Bacteria;p__Bacteroidota;c__Bacteroidia\nMKV\n",
        ">k141_2_1\tk141_2\tBacteria\td__Archaea\nMAA\n",
        ">k141_9_1\tk141_9\tBacteria\t\nMGG\n",
    ]

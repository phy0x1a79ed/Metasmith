"""PSORTm's input chunks: every ORF, each tagged with the taxon PSORTm reads for it.

PSORTm picks a protein's envelope from the NCBI phylum of the taxon name it is given, against an
NCBI taxonomy of 2017 and a 27-row phylum table. Each ORF takes its contig's LCA* GTDB lineage,
translated into the NCBI-era name PSORTm resolves; a phylum it has no row for is passed through
as-is and PSORTm leaves its proteins undetermined. An ORF whose contig has no LCA* call at phylum
or deeper is tagged `Bacteria`, which PSORTm also leaves undetermined, so it keeps a row.

    psortm_prep.py --orfs ORFS.faa --contig-taxonomy CONTIG_LCASTAR.tsv --chunk-size N --out-dir DIR

Each chunk record is `>orf<TAB>contig<TAB>psortm taxon<TAB>LCA* lineage`.
"""
import argparse
import csv
import math
import os
import re

# GTDB phylum (suffix such as _A dropped) -> the NCBI 2017 phylum PSORTm's table names.
# Pre-r220 GTDB spellings are kept so an older GTDB-Tk database resolves too.
GTDB_TO_PSORTM = {
    "Acidobacteriota": "Acidobacteria",
    "Actinomycetota": "Actinobacteria", "Actinobacteriota": "Actinobacteria",
    "Aquificota": "Aquificae",
    "Bacteroidota": "Bacteroidetes",
    "Chlamydiota": "Chlamydiae",
    "Chloroflexota": "Chloroflexi",
    "Cyanobacteriota": "Cyanobacteria", "Cyanobacteria": "Cyanobacteria",
    "Deinococcota": "Deinococcus-Thermus",
    "Dictyoglomota": "Dictyoglomi",
    "Elusimicrobiota": "Elusimicrobia",
    "Bacillota": "Firmicutes", "Firmicutes": "Firmicutes",
    "Fusobacteriota": "Fusobacteria",
    "Nitrospirota": "Nitrospirae",
    "Planctomycetota": "Planctomycetes",
    # NCBI 2017 kept the delta and epsilon classes inside Proteobacteria.
    "Pseudomonadota": "Proteobacteria", "Proteobacteria": "Proteobacteria",
    "Desulfobacterota": "Proteobacteria", "Myxococcota": "Proteobacteria",
    "Bdellovibrionota": "Proteobacteria", "Campylobacterota": "Proteobacteria",
    "Spirochaetota": "Spirochaetes",
    "Thermotogota": "Thermotogae",
    "Verrucomicrobiota": "Verrucomicrobia",
}
# GTDB files the Mollicutes as orders of Bacilli; NCBI 2017 had them as the phylum Tenericutes,
# which PSORTm runs as Gram-negative without an outer membrane.
MOLLICUTES_ORDERS = {"Mycoplasmatales", "Acholeplasmatales", "Entomoplasmatales",
                     "Anaeroplasmatales"}


def _rank(lineage, prefix):
    for part in lineage.split(";"):
        part = part.strip()
        if part.startswith(prefix) and len(part) > len(prefix):
            return re.sub(r"_[A-Z]+$", "", part[len(prefix):])
    return None


def psortm_taxon(lineage):
    domain = _rank(lineage, "d__")
    if domain == "Archaea":
        return "Archaea"
    if domain != "Bacteria":
        return None
    if _rank(lineage, "o__") in MOLLICUTES_ORDERS:
        return "Tenericutes"
    phylum = _rank(lineage, "p__")
    if phylum is None:
        return "Bacteria"
    return GTDB_TO_PSORTM.get(phylum, phylum)


def contig_lineages(table):
    with open(table) as fh:
        rows = csv.DictReader(fh, delimiter="\t")
        if not rows.fieldnames or not {"contig", "lineage"} <= set(rows.fieldnames):
            raise SystemExit("[psortm] " + table + " is not an LCA* contig table with `contig` "
                             "and `lineage` columns")
        return {row["contig"]: row["lineage"] for row in rows}


def read_fasta(path):
    name, seq = None, []
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(seq)
                name, seq = line[1:].split()[0], []
            else:
                seq.append(line.strip())
    if name is not None:
        yield name, "".join(seq)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--orfs", required=True)
    p.add_argument("--contig-taxonomy", required=True)
    p.add_argument("--chunk-size", type=int, required=True)
    p.add_argument("--out-dir", required=True)
    a = p.parse_args()

    lineage_of = contig_lineages(a.contig_taxonomy)
    records, placed = [], 0
    for orf, seq in read_fasta(a.orfs):
        # Prodigal names each protein <contig>_<n>.
        contig = orf.rpartition("_")[0]
        lineage = lineage_of.get(contig, "")
        taxon = psortm_taxon(lineage) if _rank(lineage, "p__") else None
        placed += taxon is not None
        records.append((orf, contig, taxon or "Bacteria", lineage, seq.rstrip("*")))
    print("[psortm] " + str(placed) + " of " + str(len(records)) + " ORFs lie on a contig LCA* "
          "placed at phylum or deeper", flush=True)
    if not records:
        raise SystemExit("[psortm] the ORF FASTA has no records")
    if not placed:
        print("[psortm] no ORF's contig has a phylum; every row will be Unknown. Check that the "
              "LCA* table and the ORFs come from one assembly and the ORF ids are `<contig>_<n>`",
              flush=True)

    os.makedirs(a.out_dir, exist_ok=True)
    n_chunks = math.ceil(len(records) / a.chunk_size)
    for k in range(n_chunks):
        with open(os.path.join(a.out_dir, "chunk_%04d.faa" % k), "w") as out:
            for orf, contig, taxon, lineage, seq in records[k::n_chunks]:
                out.write(">" + "\t".join((orf, contig, taxon, lineage)) + "\n" + seq + "\n")


if __name__ == "__main__":
    main()

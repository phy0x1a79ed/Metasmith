"""PSORTm's input chunks: the ORFs on quality MAG contigs, each tagged with the taxon PSORTm reads.

PSORTm picks a protein's envelope from the NCBI phylum of the taxon name it is given, against an
NCBI taxonomy of 2017 and a 27-row phylum table. GTDB-Tk names a MAG in GTDB, so each MAG's
GTDB lineage is translated into the NCBI-era name PSORTm resolves; a phylum it has no row for is
passed through as-is and PSORTm leaves its proteins undetermined. ORFs on contigs outside every
quality MAG have no taxonomy and are not chunked.

    psortm_prep.py --orfs ORFS.faa --mags MAGS.tsv --chunk-size N --out-dir DIR

MAGS.tsv: mag, fasta, gtdbtk (a GTDB-Tk summary table for that MAG). Each chunk record is
`>orf<TAB>mag<TAB>psortm taxon<TAB>gtdb classification`.
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


def gtdb_lineage(table):
    with open(table) as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if not rows or "classification" not in rows[0]:
        raise SystemExit("[psortm] " + table + " is not a GTDB-Tk summary table with a "
                         "`classification` column")
    return rows[0]["classification"]


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
    p.add_argument("--mags", required=True)
    p.add_argument("--chunk-size", type=int, required=True)
    p.add_argument("--out-dir", required=True)
    a = p.parse_args()

    contig_tag = {}
    with open(a.mags) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            lineage = gtdb_lineage(row["gtdbtk"])
            taxon = psortm_taxon(lineage) or "Bacteria"
            print("[psortm] " + row["mag"] + ": " + lineage + " -> " + taxon, flush=True)
            for contig, _ in read_fasta(row["fasta"]):
                contig_tag[contig] = (row["mag"], taxon, lineage)

    # Prodigal names each protein <contig>_<n>.
    records, n_orfs = [], 0
    for orf, seq in read_fasta(a.orfs):
        n_orfs += 1
        tag = contig_tag.get(orf.rpartition("_")[0])
        if tag is not None:
            records.append((orf, tag, seq.rstrip("*")))
    print("[psortm] " + str(len(records)) + " of " + str(n_orfs) + " ORFs lie on "
          + str(len({t[0] for t in contig_tag.values()})) + " quality MAGs", flush=True)
    if not records:
        raise SystemExit("[psortm] no ORF lies on a quality MAG contig; the ORFs and the MAGs "
                         "come from different assemblies, or the ORF ids are not `<contig>_<n>`")

    os.makedirs(a.out_dir, exist_ok=True)
    n_chunks = math.ceil(len(records) / a.chunk_size)
    for k in range(n_chunks):
        with open(os.path.join(a.out_dir, "chunk_%04d.faa" % k), "w") as out:
            for orf, (mag, taxon, lineage), seq in records[k::n_chunks]:
                out.write(">" + "\t".join((orf, mag, taxon, lineage)) + "\n" + seq + "\n")


if __name__ == "__main__":
    main()

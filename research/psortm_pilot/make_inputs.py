"""Stage each pilot proteome the way the lane sees it: Prodigal-style ORF ids `<genome>_<n>`
on one contig `<genome>`, that contig's LCA* lineage, then psortm_prep.py chunks.

    make_inputs.py GENOMES_DIR OUT_DIR CHUNK_SIZE
"""
import subprocess
import sys
from pathlib import Path

# genome -> (true envelope, GTDB r232 lineage)
GENOMES = {
    "ecoli": ("diderm (Gram-negative)", "d__Bacteria;p__Pseudomonadota;c__Gammaproteobacteria;o__Enterobacterales;f__Enterobacteriaceae;g__Escherichia;s__Escherichia coli"),
    "paeruginosa": ("diderm (Gram-negative)", "d__Bacteria;p__Pseudomonadota;c__Gammaproteobacteria;o__Pseudomonadales;f__Pseudomonadaceae;g__Pseudomonas;s__Pseudomonas aeruginosa"),
    "btheta": ("diderm (Gram-negative)", "d__Bacteria;p__Bacteroidota;c__Bacteroidia;o__Bacteroidales;f__Bacteroidaceae;g__Bacteroides;s__Bacteroides thetaiotaomicron"),
    "bsubtilis": ("monoderm (Gram-positive)", "d__Bacteria;p__Bacillota;c__Bacilli;o__Bacillales;f__Bacillaceae;g__Bacillus;s__Bacillus subtilis"),
    "scoelicolor": ("monoderm (Gram-positive)", "d__Bacteria;p__Actinomycetota;c__Actinomycetes;o__Streptomycetales;f__Streptomycetaceae;g__Streptomyces;s__Streptomyces coelicolor"),
    "vparvula": ("diderm Firmicute (LPS outer membrane)", "d__Bacteria;p__Bacillota_C;c__Negativicutes;o__Veillonellales;f__Veillonellaceae;g__Veillonella;s__Veillonella parvula"),
    "dradiodurans": ("diderm, thick wall (Gram-positive stain with outer membrane)", "d__Bacteria;p__Deinococcota;c__Deinococci;o__Deinococcales;f__Deinococcaceae;g__Deinococcus;s__Deinococcus radiodurans"),
    "mtuberculosis": ("mycomembrane (Gram-positive with outer membrane)", "d__Bacteria;p__Actinomycetota;c__Actinomycetes;o__Mycobacteriales;f__Mycobacteriaceae;g__Mycobacterium;s__Mycobacterium tuberculosis"),
    "cglutamicum": ("mycomembrane (Gram-positive with outer membrane)", "d__Bacteria;p__Actinomycetota;c__Actinomycetes;o__Mycobacteriales;f__Mycobacteriaceae;g__Corynebacterium;s__Corynebacterium glutamicum"),
    "mpneumoniae": ("no wall, no outer membrane (Mollicutes)", "d__Bacteria;p__Bacillota;c__Bacilli;o__Mycoplasmatales;f__Mycoplasmoidaceae;g__Mycoplasmoides;s__Mycoplasmoides pneumoniae"),
    "macetivorans": ("archaeon", "d__Archaea;p__Halobacteriota;c__Methanosarcinia;o__Methanosarcinales;f__Methanosarcinaceae;g__Methanosarcina;s__Methanosarcina acetivorans"),
    "hvolcanii": ("archaeon", "d__Archaea;p__Halobacteriota;c__Halobacteria;o__Halobacteriales;f__Haloferacaceae;g__Haloferax;s__Haloferax volcanii"),
}

PREP = Path(__file__).resolve().parents[2] / "src/metasmith_libraries/resources/lib/psortm/psortm_prep.py"


def main():
    src, out, chunk = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    for g, (_, lineage) in GENOMES.items():
        d = out / g
        d.mkdir(parents=True, exist_ok=True)
        n = 0
        with open(src / f"{g}.faa") as fin, open(d / "orfs.faa", "w") as fout:
            for line in fin:
                if line.startswith(">"):
                    n += 1
                    fout.write(f">{g}_{n} # pilot\n")
                else:
                    fout.write(line)
        (d / "lcastar.tsv").write_text(f"contig\tlineage\n{g}\t{lineage}\n")
        subprocess.run([sys.executable, str(PREP), "--orfs", str(d / "orfs.faa"),
                        "--contig-taxonomy", str(d / "lcastar.tsv"), "--chunk-size", chunk,
                        "--out-dir", str(d / "chunks")], check=True)


if __name__ == "__main__":
    main()

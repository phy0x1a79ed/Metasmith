"""Per-study medians of ORF annotation and reaction coverage, DIAMOND against BiGG alone and with KofamScan added."""
import csv
from pathlib import Path
from statistics import median

HERE = Path(__file__).parent
STUDIES = ["bissett_base", "karlsson2013", "korem2015", "li2019", "sunagawa2015"]
LABELS = {
    "bissett_base": "Bissett 2016",
    "karlsson2013": "Karlsson 2013",
    "korem2015": "Korem 2015",
    "li2019": "Li 2019",
    "sunagawa2015": "Sunagawa 2015",
}


def read(name):
    with open(HERE / "inputs" / name) as f:
        return {r["bin"]: r for r in csv.DictReader(f, delimiter="\t")}


def main():
    study = {b: r["study"] for b, r in read("bin_study.tsv").items()}
    union = read("evidence_orf_union.tsv")
    mnx = read("evidence_orf_mnx.tsv")

    rows = []
    for b, u in union.items():
        m = mnx[b]
        orfs = int(u["orfs"])
        rows.append({
            "study": study[b],
            "orfs": orfs,
            "annotated_diamond": 100 * int(u["diamond"]) / orfs,
            "annotated_with_kofam": 100 * int(u["diamond_or_ko_raw"]) / orfs,
            "reaction_diamond": 100 * int(m["d_mnx_orfs"]) / orfs,
            "reaction_with_kofam": 100 * int(m["union_mnx_orfs"]) / orfs,
            "kofam_only_reaction_orfs": int(m["k_only_mnx_orfs"]),
            "reactions_diamond": int(m["d_mnxr"]),
            "reactions_with_kofam": int(m["union_mnxr"]),
        })

    cols = list(rows[0])[1:]
    groups = [(LABELS[s], [r for r in rows if r["study"] == s]) for s in STUDIES] + [("All", rows)]
    with open(HERE / "kofam_lift.tsv", "w") as f:
        f.write("\t".join(["study", "mags"] + cols) + "\n")
        for label, rs in groups:
            vals = [median(r[c] for r in rs) for c in cols]
            f.write("\t".join([label, str(len(rs))] + [f"{v:.1f}" for v in vals]) + "\n")
    print((HERE / "kofam_lift.tsv").read_text())


if __name__ == "__main__":
    main()

import csv
import statistics
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).parent
INPUTS = HERE / "inputs"
KOFAM = HERE.parent / "kofam_lift" / "kofam_lift.tsv"
OUT = HERE / "csv"

EXCLUDED_RUNS = {"ERR3858126"}

LADDER = [
    ("metaGEM", "metaGEM's published GEM"),
    ("R0", "none; the archived reproduction lane"),
    ("R1", "none; a second run of the reproduction lane (noise floor)"),
    ("B", "CarveMe 1.6.6's BiGG gene reference, on CarveMe 1.2.2"),
    ("U", "CarveMe 1.6.6's BiGG universe, on CarveMe 1.2.2"),
    ("V", "CarveMe 1.6.6's code and SBML writer, on CPLEX"),
    ("G", "two-step gap fill with no gene scores, on CPLEX"),
    ("D", "DIAMOND 2.1.13 in place of 0.9.30"),
    ("S", "SCIP 9.2.4 in place of CPLEX"),
    ("M", "stock CarveMe 1.6.6 image; the archived modern lane"),
]


def num(v):
    f = float(v)
    return int(f) if f.is_integer() else f


def rows(path):
    return list(csv.DictReader(path.open(), delimiter="\t"))


def table_s1():
    runs = rows(INPUTS / "pratama_runs.tsv")
    minion = {r["sample_alias"].split("_")[0]: r["run_accession"] for r in runs if r["instrument_model"] == "MinION"}
    partner = {r["run_accession"]: minion[r["sample_alias"][:3]] for r in runs
               if r["dataset"] == "reads_2022" and r["library_layout"] == "PAIRED"
               and r["sample_alias"].endswith("02um_2022") and r["sample_alias"][:3] in minion}
    short = [r for r in runs if r["library_layout"] == "PAIRED" and r["run_accession"] not in EXCLUDED_RUNS]
    long_ = [r for r in runs if r["instrument_model"] == "MinION"]
    assert len(short) == 65 and len(partner) == 17 and len(long_) == 6
    head = ["Run accession", "Sample accession", "Sample", "Sampling year", "Instrument", "Layout",
            "Read count", "Base count", "Hybrid assembly with MinION run"]
    body = [[r["run_accession"], r["sample_accession"], r["sample_alias"], r["dataset"].split("_")[1],
             r["instrument_model"], r["library_layout"].lower(), int(r["read_count"]), int(r["base_count"]),
             partner.get(r["run_accession"], "")] for r in short + long_]
    return head, body


def table_s2():
    summ = {(r["against"], r["rung"]): r for r in rows(INPUTS / "ablation_summary.tsv") if r["scope"] == "pooled"}
    # CarveMe 1.2.2 (metaGEM, R0-U) and 1.6.6 (V on) write different SBML, and MEMOTE scores the writer as well as
    # the model. Score the early rungs as rewritten through 1.6.6's writer so every rung shares one writer.
    rewritten = {"metagem", "R0", "R1", "B", "U"}
    scores = defaultdict(lambda: defaultdict(list))
    for name, keep in (("ablation_memote_rewritten.tsv", rewritten.__contains__),
                       ("ablation_memote.tsv", lambda src: src not in rewritten)):
        for r in rows(INPUTS / name):
            if r["note"] or not keep(r["source"]):
                continue
            for k in ("total_score", "consistency"):
                scores[r["source"]][k].append(float(r[k]))
    head = ["Rung", "Change from the rung above", "Bins with a model",
            "Reaction Jaccard vs rung above, median", "Reaction Jaccard vs metaGEM, median",
            "Reaction Jaccard vs metaGEM, IQR", "Gene Jaccard vs metaGEM, median",
            "MEMOTE 0.17 total, median (CarveMe 1.6.6 SBML writer)",
            "MEMOTE 0.17 consistency, median (CarveMe 1.6.6 SBML writer)"]
    body = []
    for rung, change in LADDER:
        src = "metagem" if rung == "metaGEM" else rung
        vs_prev = summ.get(("previous", rung))
        vs_mg = summ.get(("metagem", rung))
        body.append([
            rung, change, len(scores[src]["total_score"]),
            float(vs_prev["reactions_jaccard_median"]) if vs_prev else "",
            float(vs_mg["reactions_jaccard_median"]) if vs_mg else "",
            vs_mg["reactions_jaccard_iqr"] if vs_mg else "",
            float(vs_mg["genes_jaccard_median"]) if vs_mg else "",
            round(statistics.median(scores[src]["total_score"]), 3),
            round(statistics.median(scores[src]["consistency"]), 3),
        ])
    return head, body


def table_s3():
    study = {"Bissett 2016", "Karlsson 2013", "Korem 2015", "Li 2019", "Sunagawa 2015", "All"}
    head = ["Study", "MAGs", "ORFs per MAG", "ORFs annotated, DIAMOND (%)", "ORFs annotated, DIAMOND + KofamScan (%)",
            "ORFs with a reaction, DIAMOND (%)", "ORFs with a reaction, DIAMOND + KofamScan (%)",
            "ORFs with a reaction from KofamScan only", "Reactions, DIAMOND", "Reactions, DIAMOND + KofamScan"]
    body = []
    for r in rows(KOFAM):
        assert r["study"] in study
        vals = list(r.values())
        body.append([vals[0], int(vals[1]), num(vals[2])] + vals[3:7] + [num(v) for v in vals[7:]])
    return head, body


TABLES = [
    ("Table_S1_viromics_reads.csv", table_s1),
    ("Table_S2_gem_ablation.csv", table_s2),
    ("Table_S3_kofam_lift.csv", table_s3),
]


def main():
    OUT.mkdir(exist_ok=True)
    for name, build in TABLES:
        head, body = build()
        with (OUT / name).open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(head)
            w.writerows(body)
        print(OUT / name, len(body))


if __name__ == "__main__":
    main()

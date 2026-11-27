"""The protein_match rows of an InterProScan GFF3 as CSV, and each signature's description beside.

    interproscan_gff.py GFF3 RESULTS_CSV DESCRIPTIONS_CSV [--pfam-hmm PFAM_A_HMM]

A missing GFF3 is a chunk with no matches: both tables are written with their headers only.
"""
import argparse
import csv
import os

HEADERS = ["orf", "start", "stop", "score", "database", "Name", "Dbxref", "Ontology_term"]


# InterProScan reports a Pfam family by its bare accession in every output format. The
# version lives on the ACC line of the very HMM library the scan ran, so the map is exact.
def pfam_versions(hmm):
    versions = {}
    with open(hmm) as fh:
        for line in fh:
            if line.startswith("ACC "):
                acc = line.split()[1]
                versions[acc.split(".", 1)[0]] = acc
    return versions


def parse(gff, versions):
    rows, descriptions = [], {}
    if not os.path.exists(gff):
        return rows, descriptions
    with open(gff) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9 or parts[2] != "protein_match":
                continue
            attrs = {}
            for item in parts[8].split(";"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    attrs[key] = value.strip('"')
            name = attrs.get("Name", "")
            if parts[1] == "Pfam":
                name = versions.get(name, name)
            if name:
                descriptions.setdefault(name, attrs.get("signature_desc", ""))
            dbxref = attrs.get("Dbxref", "")
            rows.append({
                "orf": parts[0],
                "start": parts[3],
                "stop": parts[4],
                "score": "" if parts[5] == "." else parts[5],
                "database": parts[1],
                "Name": name,
                "Dbxref": dbxref.replace("InterPro:", "", 1) if dbxref.startswith("InterPro:") else dbxref,
                "Ontology_term": attrs.get("Ontology_term", "").replace('"', ""),
            })
    return rows, descriptions


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("gff")
    p.add_argument("results")
    p.add_argument("descriptions")
    p.add_argument("--pfam-hmm")
    a = p.parse_args()
    rows, descriptions = parse(a.gff, pfam_versions(a.pfam_hmm) if a.pfam_hmm else {})
    with open(a.results, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADERS)
        w.writeheader()
        w.writerows(rows)
    with open(a.descriptions, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Name", "description"])
        for name in sorted(descriptions):
            w.writerow([name, descriptions[name]])
    print(f"[interproscan] {len(rows)} matches, {len(descriptions)} signatures -> {a.results}")


if __name__ == "__main__":
    main()

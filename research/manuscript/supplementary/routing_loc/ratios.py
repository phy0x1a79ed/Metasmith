"""Split each side's step code into procedure and interface lines, for the routing ratios in figure 2A's text.

nf-core/mag: a module's input:/output: blocks are its interface; every other line of the process is
procedure. Metasmith: a transform's requirement, product and TransformInstance declarations are its
contract; the protocol and its helpers are procedure. Blank lines, comments, imports and stub
sections are dropped on both sides.
"""
import argparse
import csv
import re
from pathlib import Path

HERE = Path(__file__).parent
SCORING = {"amber", "gold_standard"}


def nf_lines(path):
    out, in_comment, in_stub = [], False, False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if in_comment:
            in_comment = "*/" not in line
            continue
        if line.startswith("/*"):
            in_comment = "*/" not in line
            continue
        if not line or line.startswith("//"):
            continue
        if line.startswith("stub:"):
            in_stub = True
        if in_stub:
            continue
        out.append(line)
    return out


def split_module(path):
    interface = procedure = 0
    block = None
    for line in nf_lines(path):
        if re.match(r"^(input|output):$", line):
            block = "io"
            interface += 1
            continue
        if re.match(r"^(when|script|exec|shell):$", line):
            block = None
        if block == "io":
            interface += 1
        else:
            procedure += 1
    return interface, procedure


def split_transform(path):
    contract = procedure = 0
    depth = 0
    in_instance = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(("import ", "from ")):
            continue
        if in_instance or line.startswith("TransformInstance("):
            in_instance = True
            depth += line.count("(") - line.count(")")
            contract += 1
            in_instance = depth > 0
            continue
        if re.search(r"\b(Transform\(\)|AddRequirement|AddProduct|ResolveParentLibrary)\b", line):
            contract += 1
        else:
            procedure += 1
    return contract, procedure


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nfcore", required=True, type=Path, help="nf-core/mag 5.5.0 checkout")
    args = ap.parse_args()

    with open(HERE / "modules.tsv") as f:
        modules = [r["name"] for r in csv.DictReader(f, delimiter="\t") if r["kind"] == "module"]
    nf_io = nf_proc = 0
    for m in modules:
        i, p = split_module(args.nfcore / m)
        nf_io += i
        nf_proc += p

    ms_contract = ms_proc = 0
    for t in sorted((HERE / "inputs/e2/transforms").glob("*.py")):
        if t.stem in SCORING:
            continue
        c, p = split_transform(t)
        ms_contract += c
        ms_proc += p

    with open(HERE / "summary.tsv") as f:
        routing = next(int(r["value"]) for r in csv.DictReader(f, delimiter="\t")
                       if r["section"] == "union" and r["metric"] == "workflow lines: routing")

    rows = [
        ("nfcore", "modules", len(modules)),
        ("nfcore", "procedure lines", nf_proc),
        ("nfcore", "interface lines (input:/output:)", nf_io),
        ("nfcore", "routing lines (workflow code)", routing),
        ("metasmith", "transforms", len([t for t in (HERE / "inputs/e2/transforms").glob("*.py") if t.stem not in SCORING])),
        ("metasmith", "procedure lines", ms_proc),
        ("metasmith", "contract lines", ms_contract),
        ("metasmith", "routing lines", 0),
    ]
    with open(HERE / "ratios.tsv", "w") as f:
        f.write("side\tmetric\tvalue\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")
    for r in rows:
        print(*r, sep="\t")
    print(f"nf-core procedure:interface {nf_proc / nf_io:.1f}:1, procedure:routing {nf_proc / routing:.1f}:1")
    print(f"metasmith procedure:contract {ms_proc / ms_contract:.1f}:1")


if __name__ == "__main__":
    main()

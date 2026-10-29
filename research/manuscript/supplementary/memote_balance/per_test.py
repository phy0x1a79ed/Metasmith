"""Flatten MEMOTE 0.17 per-test results out of E4's ablation tars into one wide table.

    per_test.py <tar> <out.tsv>

<tar> is e4_ablation_memote.tar or e4_ablation_rewrite.tar: an outer tar of memote/block_NN.tar,
each holding <source>/<bin>.json.gz. One row per model. Every test with a scalar metric gets a
column m:<test>; a parametrized test gets the mean of its cases. Tests whose data is a list or
dict also get n:<test>, the length. The unconserved-metabolite and
inconsistent-minimal-stoichiometry tests also get ids:<test>, the JSON of their data.
"""
import csv
import gzip
import io
import json
import sys
import tarfile


IDS = {"test_unconserved_metabolites", "test_inconsistent_min_stoichiometry"}


def flat(tests):
    row = {}
    for name, t in tests.items():
        metric, data = t.get("metric"), t.get("data")
        if isinstance(metric, dict):
            vals = [v for v in metric.values() if isinstance(v, (int, float))]
            metric = sum(vals) / len(vals) if vals else None
        if isinstance(metric, (int, float)):
            row[f"m:{name}"] = metric
        if isinstance(data, (list, dict)):
            row[f"n:{name}"] = len(data)
            if name in IDS:
                row[f"ids:{name}"] = json.dumps(data, sort_keys=True)
        elif isinstance(data, bool):
            row[f"b:{name}"] = int(data)
    return row


def models(outer):
    seen = set()
    with tarfile.open(outer) as top:
        for member in top:
            if not (member.isfile() and member.name.endswith(".tar")):
                continue
            with tarfile.open(fileobj=io.BytesIO(top.extractfile(member).read())) as blk:
                for m in blk:
                    if m.isfile() and m.name.endswith(".json.gz"):
                        src, _, name = m.name.removeprefix("./").partition("/")
                        key = (src, name.removesuffix(".json.gz"))
                        if key in seen:
                            continue
                        seen.add(key)
                        yield key, json.loads(gzip.decompress(blk.extractfile(m).read()))["tests"]


def main(outer, out):
    rows = []
    for (src, b), tests in models(outer):
        rows.append({"source": src, "bin": b, **flat(tests)})
        if len(rows) % 1000 == 0:
            print(len(rows), file=sys.stderr, flush=True)
    cols = ["source", "bin"] + sorted({k for r in rows for k in r} - {"source", "bin"})
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} models, {len(cols)} columns", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])

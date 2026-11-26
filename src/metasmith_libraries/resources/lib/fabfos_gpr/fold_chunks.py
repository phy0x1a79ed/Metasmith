"""Concatenate per-ORF-batch annotator chunks into the merged files a lane and its sibling consumers read.

    fold_chunks.py KIND --merge OUT CHUNK [CHUNK ...] [--merge OUT CHUNK ...] [--db DIR --desc-out PATH]

KIND names how chunks join. `--merge` repeats once per merged product; chunks arrive in the order given.
  cat           byte concatenation
  header        first chunk's header once, repeated header lines dropped
  first-header  first chunk's first line once, every later chunk's first line dropped
  unique-csv, unique-tsv   header once, one row per distinct first field
  eggnog        '#' preamble from the first chunk, '##' footer from the last
  dbcan, vogdb, pathofact-hmm   hmmsearch tables concatenated, plus a term description table at --desc-out
  pbert         parquet embeddings stacked; a sequence_id in two chunks is an error
"""
import argparse
import re
import shutil
import sys


def cat(chunks, out):
    with open(out, "wb") as fout:
        for c in chunks:
            with open(c, "rb") as fin:
                shutil.copyfileobj(fin, fout, 1 << 20)


def header(chunks, out):
    unique(chunks, out, None)


def unique(chunks, out, sep):
    if not chunks:
        open(out, "w").close()
        return
    with open(chunks[0]) as fin:
        head = fin.readline()
    seen = set()
    with open(out, "w") as fout:
        fout.write(head)
        for c in chunks:
            with open(c) as fin:
                for line in fin:
                    if line == head:
                        continue
                    if sep is not None:
                        key = line.split(sep, 1)[0]
                        if key in seen:
                            continue
                        seen.add(key)
                    fout.write(line)


def first_header(chunks, out):
    with open(out, "w") as fout:
        for i, c in enumerate(chunks):
            with open(c) as fin:
                head = fin.readline()
                if i == 0:
                    fout.write(head)
                fout.writelines(fin)


def eggnog(chunks, out):
    with open(out, "w") as fout:
        for i, c in enumerate(chunks):
            with open(c) as fin:
                lines = fin.readlines()
            head_end = 0
            while head_end < len(lines) and lines[head_end].startswith("#"):
                head_end += 1
            tail_start = len(lines)
            while tail_start > head_end and lines[tail_start - 1].startswith("##"):
                tail_start -= 1
            if i == 0:
                fout.writelines(lines[:head_end])
            fout.writelines(lines[head_end:tail_start])
            if i == len(chunks) - 1:
                fout.writelines(lines[tail_start:])


def hmm_concat(chunks, out, field, strip=""):
    hit = set()
    with open(out, "w") as fout:
        for c in chunks:
            for line in open(c):
                fout.write(line)
                if not line.startswith("#"):
                    hit.add(line.split()[field].removesuffix(strip))
    return hit


def pbert(chunks, out):
    import polars as pl
    merged = pl.concat([pl.read_parquet(p) for p in chunks], how="vertical")
    dupes = merged.height - merged["sequence_id"].n_unique()
    if dupes:
        raise SystemExit(
            f"[fold_chunks] {dupes:,} sequence_id appear in more than one chunk. The "
            f"chunks partition the ORFs, so an overlap means the splitter and this "
            f"merge disagree about what a chunk is")
    merged.write_parquet(out)


# A dbCAN model is a family or a subfamily (GH5, GH5_4); CAZy describes the family, and
# DRAM reads the family off the name with this.
FAMILY = re.compile(r"^[A-Z]*[0-9]*")


def write_terms(path, terms, describe):
    with open(path, "w") as fh:
        fh.write("term\tdescription\n")
        for term in sorted(terms):
            fh.write(f"{term}\t{describe(term)}\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind")
    p.add_argument("--merge", nargs="+", action="append", required=True, metavar="OUT CHUNK")
    p.add_argument("--db")
    p.add_argument("--desc-out")
    a = p.parse_args()
    jobs = [(m[0], m[1:]) for m in a.merge]
    k = a.kind
    plain = {"cat": cat, "header": header, "first-header": first_header, "eggnog": eggnog, "pbert": pbert,
             "unique-csv": lambda c, o: unique(c, o, ","), "unique-tsv": lambda c, o: unique(c, o, "\t")}
    if k in plain:
        for out, chunks in jobs:
            plain[k](chunks, out)
    elif k == "dbcan":
        (out, chunks), = jobs
        hit = hmm_concat(chunks, out, 3, ".hmm")
        names = dict(l.rstrip("\n").split("\t", 1) for l in open(f"{a.db}/descriptions.tsv"))
        write_terms(a.desc_out, hit, lambda t: names.get(FAMILY.match(t).group(), ""))
    elif k == "vogdb":
        (out, chunks), = jobs
        hit = hmm_concat(chunks, out, 3)
        names = dict(l.rstrip("\n").split("\t", 1) for l in open(f"{a.db}/descriptions.tsv"))
        write_terms(a.desc_out, hit, lambda t: names.get(t, ""))
    elif k == "pathofact-hmm":
        hit = set()
        for out, chunks in jobs:
            hit |= hmm_concat(chunks, out, 2)
        # cddid_all.tbl: PSSM id, accession, short name, description, length. The HMMs are
        # named by accession (cd01840, pfam00004, COG0001).
        with open(f"{a.db}/cddid_all.tbl", errors="replace") as fin, open(a.desc_out, "w") as fout:
            fout.write("term\tdescription\n")
            for line in fin:
                f = line.rstrip("\n").split("\t")
                if len(f) > 3 and f[1] in hit:
                    fout.write(f"{f[1]}\t{f[2]}: {f[3]}\n")
    else:
        sys.exit(f"unknown kind {k}")


if __name__ == "__main__":
    main()

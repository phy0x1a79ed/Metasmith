#!/usr/bin/env python3
"""Decide, per colony, whether the CRAGE cargo went into the landing pad.

    python3 insertion_call.py <root> <out> [colony ...]

<root> holds ref/ (the parent genome fasta and gff, the insertion plasmid .gb) and
plasmidsaurus/<colony>/<colony>_1_reference.fasta. Writes <out>/insertion_call.tsv,
<out>/features_<colony>.tsv and <out>/insertion_call.md.

This is the yes/no call and the insertion site, and nothing else. It supersedes the junction
arm of compare.py, whose flank logic read a circular contig's origin as position zero: an
assembly's coordinates wrap, so a cargo near the origin had its flank reported at 0 rather than
resolved the long way round. Here each flank is cut from the sequence with explicit modular
arithmetic and then mapped, so the origin is never special.

Stdlib only, plus apptainer images already cached on fir.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Which assemblies to call against: the vendor's by default, or our own once they exist.
ASM_DIR = os.environ.get("ASM_DIR", "plasmidsaurus")

IMG = Path("/scratch/phyberos/cache/apptainer")
BLAST = IMG / "docker..quay.io_biocontainers_blast..2.16.0--hc155240_2.sif"
MINIMAP = IMG / "docker..community.wave.seqera.io_library_minimap2_samtools..33bb43c18d22e29c.sif"

# Each flank is long enough to place uniquely in a 4.7 Mb genome and short enough to stay inside
# one alignment block.
FLANK = 3000
# A feature is called present at this much of its length aligned.
PRESENT = 0.90
# Two flanks landing within this distance in the parent are one insertion point with nothing lost.
ADJACENT = 200
# The delivery backbone. Its presence means the construct is in the cell as a plasmid rather than
# integrated, which is the main thing a yes/no call can get wrong.
BACKBONE = {"R6K_y_ori", "oriT", "lacZ___fragment_", "REDF_ECOLI__fragment_"}
# The two sites CRAGE recombines between; the cargo is what lies between them.
SITES = {"loxP", "lox5171"}


def run(args: list, **kw) -> str:
    return subprocess.run([str(a) for a in args], check=True, capture_output=True,
                          text=True, **kw).stdout


def apptainer(image: Path, root: Path, *args) -> str:
    return run(["apptainer", "exec", "-B", root, image, *args])


def read_fasta(path: Path) -> dict:
    seqs, name = {}, None
    for line in open(path):
        if line.startswith(">"):
            name = line[1:].split()[0]
            seqs[name] = []
        else:
            seqs[name].append(line.strip())
    return {k: "".join(v) for k, v in seqs.items()}


def revcomp(s: str) -> str:
    return s[::-1].translate(str.maketrans("ACGTacgtNn", "TGCAtgcaNn"))


def safe(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", label)


def genbank(path: Path) -> tuple:
    text = path.read_text()
    origin = text.split("\nORIGIN", 1)[1]
    seq = re.sub(r"[^acgtnACGTN]", "", origin.split("//")[0]).upper()
    table = text.split("\nFEATURES", 1)[1].split("\nORIGIN", 1)[0]
    feats, seen = [], set()
    for m in re.finditer(r"\n {5}(\S+)\s+(complement\()?(\d+)\.\.(\d+)\)?((?:\n {21}.*)*)", table):
        kind, comp, start, end, quals = m.groups()
        lab = re.search(r'/label="([^"]*)"', quals)
        lab = safe(lab.group(1) if lab else kind)
        key = (lab, int(start), int(end))
        if key in seen or int(end) - int(start) + 1 < 20:
            continue
        seen.add(key)
        feats.append((lab, int(start), int(end), bool(comp)))
    return seq, feats


def read_gff(path: Path) -> list:
    genes = []
    for line in open(path):
        if line.startswith("#"):
            if line.startswith("##FASTA"):
                break
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 9 or f[2] not in ("CDS", "rRNA", "tRNA", "ncRNA"):
            continue
        a = dict(x.split("=", 1) for x in f[8].split(";") if "=" in x)
        name = a.get("gene") or a.get("Name") or a.get("locus_tag", "")
        product = a.get("product", "").replace("%2C", ",").replace("%3B", ";")
        genes.append((f[0], int(f[3]) - 1, int(f[4]), name, product))
    return genes


def gene_at(genes: list, contig: str, pos: int) -> str:
    inside = [g for g in genes if g[0] == contig and g[1] <= pos < g[2]]
    if inside:
        return f"in {inside[0][3]} ({inside[0][4]})"
    same = [g for g in genes if g[0] == contig]
    if not same:
        return "no annotation"
    left = max((g for g in same if g[2] <= pos), key=lambda g: g[2], default=None)
    right = min((g for g in same if g[1] >= pos), key=lambda g: g[1], default=None)
    bits = []
    if left:
        bits.append(f"{pos - left[2]} bp after {left[3]}")
    if right:
        bits.append(f"{right[1] - pos} bp before {right[3]}")
    return "between genes: " + ", ".join(bits)


# A 31 bp promoter cannot clear a megablast word size or a 1e-10 e-value in a 4.7 Mb subject, so
# the short annotations come back absent from the default search whether or not they are there.
# They get blastn-short, and anything still unplaced is reported as too short to call rather than
# as missing: saying a promoter is gone when the search simply cannot see it is the worse error.
SHORT = 50


def blast(query: Path, subject: Path, root: Path, short: bool = False) -> list:
    fmt = "6 qseqid sseqid pident length qlen sstart send bitscore"
    task = ["-task", "blastn-short", "-evalue", "0.01"] if short else ["-evalue", "1e-10"]
    out = apptainer(BLAST, root, "blastn", "-query", query, "-subject", subject,
                    "-outfmt", fmt, *task, "-max_target_seqs", "50")
    rows = []
    for line in out.splitlines():
        q, s, pid, ln, qlen, ss, se, bits = line.split("\t")
        rows.append(dict(q=q, s=s, pid=float(pid), ln=int(ln), qlen=int(qlen),
                         lo=min(int(ss), int(se)) - 1, hi=max(int(ss), int(se)),
                         strand="+" if int(ss) < int(se) else "-", bits=float(bits)))
    return rows


def merge(spans: list) -> list:
    out = []
    for lo, hi in sorted(spans):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def best_per_feature(rows: list) -> dict:
    best = {}
    for r in rows:
        prev = best.get(r["q"])
        if prev is None or r["bits"] > prev["bits"]:
            best[r["q"]] = r
    for r in best.values():
        r["cov"] = r["ln"] / r["qlen"]
    return best


def cargo_span(rows: list, contig_len: int, plasmid_len: int) -> tuple:
    """The one stretch of colony sequence the plasmid aligns to, and whether it wraps the origin.

    The features do not align as one block: short ones fall below the cutoff and leave gaps, so
    merging only the overlaps collapses the cargo to its single longest feature. Hits are instead
    clustered while consecutive ones sit within a plasmid length of each other, and the cluster
    carrying the most aligned sequence wins.
    """
    if not rows:
        return None
    spans = merge([(r["lo"], r["hi"]) for r in rows])
    clusters = [[spans[0]]]
    for lo, hi in spans[1:]:
        if lo - clusters[-1][-1][1] <= plasmid_len:
            clusters[-1].append([lo, hi])
        else:
            clusters.append([[lo, hi]])
    # A cargo sitting across the assembly's origin arrives as one cluster at each end of the
    # contig. Joining them through the origin is what keeps the junctions real.
    if len(clusters) > 1:
        first, last = clusters[0], clusters[-1]
        if first[0][0] + (contig_len - last[-1][1]) <= plasmid_len:
            joined = [[lo + contig_len, hi + contig_len] for lo, hi in first]
            clusters = clusters[1:-1] + [last + joined]
    aligned = lambda c: sum(hi - lo for lo, hi in c)
    best = max(clusters, key=aligned)
    return (best[0][0], best[-1][1], best[-1][1] > contig_len)


def cut(seq: str, start: int, length: int) -> str:
    """Length bases from start, wrapping the circle."""
    n = len(seq)
    start %= n
    if start + length <= n:
        return seq[start:start + length]
    return seq[start:] + seq[:(start + length) - n]


def map_flanks(flanks: dict, ref: Path, root: Path, out: Path, tag: str) -> dict:
    fa = out / f"flanks_{tag}.fna"
    fa.write_text("".join(f">{k}\n{v}\n" for k, v in flanks.items()))
    paf = apptainer(MINIMAP, root, "minimap2", "-cx", "asm5", "--secondary=no", ref, fa)
    hits = {}
    for line in paf.splitlines():
        f = line.split("\t")
        name, qlen, qs, qe, strand, tname = f[0], int(f[1]), int(f[2]), int(f[3]), f[4], f[5]
        ts, te, match = int(f[7]), int(f[8]), int(f[9])
        prev = hits.get(name)
        if prev and prev["match"] >= match:
            continue
        # The inner edge of a flank is the base nearest the cargo. For the left flank that is its
        # last base, for the right flank its first; which end that maps to depends on the strand.
        inner = (te if strand == "+" else ts) if name.endswith("left") else \
                (ts if strand == "+" else te)
        hits[name] = dict(ref=tname, inner=inner, strand=strand, match=match,
                          frac=match / qlen, ts=ts, te=te)
    return hits


def main() -> None:
    root, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    colonies = sys.argv[3:] or [f"XQTPYV_{i}_Colony_{i}" for i in (1, 2, 3)]
    out.mkdir(parents=True, exist_ok=True)

    plasmid_gb = next((root / "ref").glob("*.gb"))
    ref_fa = next((root / "ref").glob("*_genomic.fna"))
    ref_genes = read_gff(root / "ref" / "genomic.gff")
    pseq, feats = genbank(plasmid_gb)

    features_fa = out / "plasmid_features.fna"
    short_fa = out / "plasmid_features_short.fna"
    with open(features_fa, "w") as f, open(short_fa, "w") as g:
        for lab, s, e, comp in feats:
            sub = pseq[s - 1:e]
            rec = f">{lab}\n{revcomp(sub) if comp else sub}\n"
            (g if len(sub) < SHORT else f).write(rec)
    names = [lab for lab, *_ in feats]
    short_names = {lab for lab, s, e, _ in feats if e - s + 1 < SHORT}

    def search(subject: Path) -> dict:
        found = best_per_feature(blast(features_fa, subject, root))
        found.update(best_per_feature(blast(short_fa, subject, root, short=True)))
        return found

    # EPI300 carries araC and trfA of its own, and the plasmid's AraC matches them, so a feature
    # the parent also has cannot anchor the cargo: it would pull the span onto the parent's copy.
    in_parent = {n for n, h in search(ref_fa).items() if h["cov"] >= PRESENT}

    calls, md = [], ["# Is the cargo in the landing pad?", ""]
    for colony in colonies:
        asm_fa = root / ASM_DIR / colony / f"{colony}_1_reference.fasta"
        if not asm_fa.exists():
            md += [f"## {colony}", "", "No assembly for this colony.", ""]
            continue
        asm = read_fasta(asm_fa)
        best = search(asm_fa)
        # A flye assembly can be several linear contigs. The cargo sits on one of them, so the
        # span and its flanks must come from that contig, not from whichever one is listed first.
        weight = {}
        for n, h in best.items():
            if h["cov"] >= PRESENT and n not in in_parent:
                weight[h["s"]] = weight.get(h["s"], 0) + h["ln"]
        contig = max(weight, key=weight.get) if weight else next(iter(asm))
        seq = asm[contig]

        with open(out / f"features_{colony}.tsv", "w") as f:
            f.write("feature\tpresent\tpercent_identity\tfraction_covered\tcolony_start\tcolony_end\tstrand\n")
            for n in names:
                h = best.get(n)
                if h and h["cov"] >= PRESENT:
                    f.write(f"{n}\tyes\t{h['pid']:.2f}\t{h['cov']:.3f}\t{h['lo'] + 1}\t{h['hi']}\t{h['strand']}\n")
                else:
                    cov = h["cov"] if h else 0.0
                    pid = f"{h['pid']:.2f}" if h else ""
                    verdict = "too short to call" if n in short_names else "no"
                    f.write(f"{n}\t{verdict}\t{pid}\t{cov:.3f}\t\t\t\n")

        present = {n for n in names if (h := best.get(n)) and h["cov"] >= PRESENT}
        backbone = sorted(BACKBONE & present)
        sites = sorted(SITES & present)
        cargo = [n for n in present if n not in BACKBONE and n not in SITES]
        unresolved = sorted(short_names - present - BACKBONE - SITES)
        # Two labels occur twice in the plasmid annotation ("0.99", "MTF_ATTAAT"), and a hit is
        # keyed by label, so counting the raw list would report those as missing.
        callable_cargo = list(dict.fromkeys(
            n for n in names if n not in BACKBONE and n not in SITES and n not in short_names))

        anchors = [best[n] for n in present if n not in in_parent and n not in short_names
                   and best[n]["s"] == contig]
        span = cargo_span(anchors, len(seq), len(pseq))
        junctions, lost = {}, None
        if span:
            lo, hi, wrapped = span
            flanks = {f"{colony}|left": cut(seq, lo - FLANK, FLANK),
                      f"{colony}|right": cut(seq, hi, FLANK)}
            junctions = map_flanks(flanks, ref_fa, root, out, colony)
            left, right = junctions.get(f"{colony}|left"), junctions.get(f"{colony}|right")
            if left and right and left["ref"] == right["ref"]:
                gap = abs(right["inner"] - left["inner"])
                lost = min(gap, len(read_fasta(ref_fa)[left["ref"]]) - gap)

        verdict = "cargo not found"
        if present:
            if backbone:
                verdict = "whole plasmid present, not an integration"
            elif len(sites) == 2 and lost is not None and lost <= ADJACENT:
                verdict = "insertion into the landing pad, nothing lost"
            elif len(sites) == 2:
                verdict = "cargo integrated between both sites, with loss at the site"
            elif len(sites) == 1:
                verdict = "cargo integrated, only one recombinase site left"
            else:
                verdict = "cargo integrated, neither recombinase site found"

        calls.append(dict(colony=colony, verdict=verdict, contig=contig, contig_len=len(seq),
                          span=span and [span[0] + 1, span[1]], wrapped=bool(span and span[2]),
                          cargo_features=len([n for n in cargo if n not in short_names]),
                          total_cargo=len(callable_cargo), unresolved=unresolved,
                          sites=sites, backbone=backbone, lost=lost,
                          junctions={k.split("|")[1]: v for k, v in junctions.items()}))

        md += [f"## {colony}", "", f"**{verdict}**", ""]
        if span:
            md.append(f"Cargo occupies colony {span[0] + 1:,}-{span[1]:,} "
                      f"({span[1] - span[0]:,} bp){' , across the assembly origin' if span[2] else ''}.")
        md.append(f"Recombinase sites found: {', '.join(sites) or 'none'}. "
                  f"Delivery backbone: {', '.join(backbone) or 'absent'}. "
                  f"Cargo features present: {len([n for n in cargo if n not in short_names])} "
                  f"of {len(callable_cargo)}."
                  + (f" Too short to call either way: {', '.join(unresolved)}." if unresolved else ""))
        for side in ("left", "right"):
            j = junctions.get(f"{colony}|{side}")
            if j:
                md.append(f"- {side.capitalize()} junction: parent {j['ref']} {j['inner']:,} "
                          f"({j['frac']:.0%} of the flank placed, {j['strand']} strand), "
                          f"{gene_at(ref_genes, j['ref'], j['inner'])}.")
        if lost is not None:
            md.append(f"- Parent sequence between the two junctions: {lost:,} bp"
                      + (" (nothing lost)" if lost <= ADJACENT else " — this much is missing from the colony"))
        md.append("")

    (out / "insertion_call.tsv").write_text(
        "colony\tverdict\tcargo_span\tsites_found\tbackbone\tcargo_features\tparent_bp_between_junctions\n"
        + "".join(f"{c['colony']}\t{c['verdict']}\t"
                  f"{'-'.join(map(str, c['span'])) if c['span'] else ''}\t"
                  f"{','.join(c['sites'])}\t{','.join(c['backbone']) or 'absent'}\t"
                  f"{c['cargo_features']}/{c['total_cargo']}\t{'' if c['lost'] is None else c['lost']}\n"
                  for c in calls))
    (out / "insertion_call.md").write_text("\n".join(md) + "\n")
    (out / "insertion_call.json").write_text(json.dumps(calls, indent=2))
    for c in calls:
        print(f"{c['colony']}: {c['verdict']}; sites={c['sites']}; backbone={c['backbone'] or 'absent'}; "
              f"cargo={c['cargo_features']}/{c['total_cargo']}; unresolved={len(c['unresolved'])}; "
              f"between_junctions={c['lost']}")


if __name__ == "__main__":
    main()

"""Locate the pw34 CRAGE cargo in Kalen's EPI300 colonies and list how each colony differs from EPI300.

    python3 compare.py features <plasmid.gb> <features.fa> <plasmid.fa>
    python3 compare.py report <root> <out>

Stdlib only, so it runs on fir's system python3 beside run.sh.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

COLONIES = [1, 2, 3]
MIN_GAP = 200
FULL_COVER = 0.95


def read_fasta(path):
    seqs, name = {}, None
    for line in open(path):
        if line.startswith(">"):
            name = line[1:].split()[0]
            seqs[name] = []
        else:
            seqs[name].append(line.strip())
    return {k: "".join(v) for k, v in seqs.items()}


def revcomp(s):
    return s[::-1].translate(str.maketrans("ACGTacgtNn", "TGCAtgcaNn"))


def genbank_features(path):
    text = open(path).read()
    origin = text.split("\nORIGIN", 1)[1]
    seq = re.sub(r"[^acgtnACGTN]", "", origin.split("//")[0]).upper()
    table = text.split("\nFEATURES", 1)[1].split("\nORIGIN", 1)[0]
    feats = []
    for m in re.finditer(r"\n {5}(\S+)\s+(complement\()?(\d+)\.\.(\d+)\)?((?:\n {21}.*)*)", table):
        kind, comp, start, end, quals = m.groups()
        label = re.search(r'/label="([^"]*)"', quals)
        label = label.group(1) if label else kind
        feats.append((label, int(start), int(end), bool(comp), kind))
    return seq, feats


def cmd_features(gb, features_fa, plasmid_fa):
    seq, feats = genbank_features(gb)
    with open(plasmid_fa, "w") as f:
        f.write(f">pw34\n{seq}\n")
    seen = set()
    with open(features_fa, "w") as f:
        for label, start, end, comp, kind in feats:
            key = (label, start, end)
            if key in seen or end - start + 1 < 20:
                continue
            seen.add(key)
            s = seq[start - 1:end]
            name = re.sub(r"[^A-Za-z0-9_.\-]", "_", label)
            f.write(f">{name}|{start}-{end}|{kind}\n{revcomp(s) if comp else s}\n")


def read_blast(path):
    rows = []
    for line in open(path):
        q, s, pid, length, qlen, qs, qe, ss, se, ev, bits = line.split("\t")
        rows.append(dict(q=q, s=s, pid=float(pid), len=int(length), qlen=int(qlen), qs=int(qs), qe=int(qe),
                         ss=int(ss), se=int(se), bits=float(bits)))
    return rows


def read_paf(path, primary_only=True):
    rows = []
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        tags = dict((t[:2], t[5:]) for t in f[12:])
        if primary_only and tags.get("tp") != "P":
            continue
        rows.append(dict(q=f[0], qlen=int(f[1]), qs=int(f[2]), qe=int(f[3]), strand=f[4], t=f[5], tlen=int(f[6]),
                         ts=int(f[7]), te=int(f[8]), match=int(f[9]), alen=int(f[10]), mapq=int(f[11]),
                         nm=int(tags.get("NM", 0))))
    return rows


def uncovered(intervals, length, min_len=MIN_GAP):
    gaps, pos = [], 0
    for s, e in sorted(intervals):
        if s > pos and s - pos >= min_len:
            gaps.append((pos, s))
        pos = max(pos, e)
    if length - pos >= min_len:
        gaps.append((pos, length))
    return gaps


def depth_runs(intervals, min_depth=2, min_len=1000):
    events = sorted([(s, 1) for s, e in intervals] + [(e, -1) for s, e in intervals])
    runs, depth, start = [], 0, None
    for pos, d in events:
        depth += d
        if depth >= min_depth and start is None:
            start = pos
        elif depth < min_depth and start is not None:
            if pos - start >= min_len:
                runs.append((start, pos))
            start = None
    return runs


def read_gff(path):
    genes = []
    for line in open(path):
        if line.startswith("#"):
            if line.startswith("##FASTA"):
                break
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 9 or f[2] not in ("CDS", "rRNA", "tRNA", "ncRNA"):
            continue
        attrs = dict(a.split("=", 1) for a in f[8].split(";") if "=" in a)
        name = attrs.get("gene") or attrs.get("Name") or attrs.get("locus_tag", "")
        product = attrs.get("product", "").replace("%2C", ",").replace("%3B", ";")
        if attrs.get("pseudo") == "true":
            product += " (pseudogene)"
        genes.append((f[0], int(f[3]) - 1, int(f[4]), f[6], name, product))
    return genes


def genes_in(genes, contig, s, e):
    return [g for g in genes if g[0] == contig and g[1] < e and g[2] > s]


def gene_at(genes, contig, pos):
    hits = genes_in(genes, contig, pos, pos + 1)
    if hits:
        g = hits[0]
        return f"in {g[4]} ({g[5]})"
    same = [g for g in genes if g[0] == contig]
    if not same:
        return ""
    left = max((g for g in same if g[2] <= pos), key=lambda g: g[2], default=None)
    right = min((g for g in same if g[1] >= pos), key=lambda g: g[1], default=None)
    parts = []
    if left:
        parts.append(f"{pos - left[2]} bp after {left[4]} ({left[5]})")
    if right:
        parts.append(f"{right[1] - pos} bp before {right[4]} ({right[5]})")
    return "intergenic: " + "; ".join(parts)


def describe_genes(gs, limit=12):
    names = [f"{g[4]}" + (f" [{g[5]}]" if g[5] else "") for g in gs]
    more = f" … and {len(names) - limit} more" if len(names) > limit else ""
    return "; ".join(names[:limit]) + more


def colony_paths(root, c):
    base = root / "plasmidsaurus" / f"XQTPYV_{c}_Colony_{c}"
    return (base / f"XQTPYV_{c}_Colony_{c}_1_reference.fasta",
            base / "annotation" / f"XQTPYV_{c}_Colony_{c}_1_reference.gff3")


def feature_table(rows):
    best = {}
    for r in rows:
        cov = r["len"] / r["qlen"]
        if r["q"] not in best or r["bits"] > best[r["q"]]["bits"]:
            best[r["q"]] = dict(r, cov=cov)
    return best


def cargo_block(rows, plasmid_len):
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: -r["bits"])
    anchor = rows[0]
    near = [r for r in rows if r["s"] == anchor["s"] and abs(min(r["ss"], r["se"]) - min(anchor["ss"], anchor["se"])) < 2 * plasmid_len]
    lo = min(min(r["ss"], r["se"]) for r in near)
    hi = max(max(r["ss"], r["se"]) for r in near)
    pcov = [(r["qs"] - 1, r["qe"]) for r in near]
    covered = sum(e - s for s, e in merge(pcov))
    return dict(contig=anchor["s"], start=lo - 1, end=hi, plasmid_covered=covered, hits=near)


def merge(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def flank_mapping(paf, contig, pos, side):
    cands = [r for r in paf if r["q"] == contig]
    if side == "left":
        cands = [r for r in cands if r["qe"] <= pos + 50]
        r = max(cands, key=lambda r: r["qe"], default=None)
        if not r:
            return None
        q_edge = r["qe"]
        t_edge = r["te"] if r["strand"] == "+" else r["ts"]
    else:
        cands = [r for r in cands if r["qs"] >= pos - 50]
        r = min(cands, key=lambda r: r["qs"], default=None)
        if not r:
            return None
        q_edge = r["qs"]
        t_edge = r["ts"] if r["strand"] == "+" else r["te"]
    return dict(colony_pos=q_edge, ref_contig=r["t"], ref_pos=t_edge, strand=r["strand"], gap=abs(q_edge - pos))


def read_vars(path):
    out = []
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        if f[0] != "V":
            continue
        ctg, s, e, depth, mapq, ref, alt, q, qs, qe, qstrand = f[1:12]
        if int(depth) != 1:
            continue
        kind = "SNP" if len(ref) == 1 and len(alt) == 1 and ref != "-" and alt != "-" else "indel"
        out.append(dict(ctg=ctg, s=int(s), e=int(e), ref=ref, alt=alt, q=q, qs=int(qs), kind=kind))
    return out


def cmd_report(root, out):
    root, out = Path(root), Path(out)
    ref_fa = next((root / "ref").glob("*_genomic.fna"))
    ref = read_fasta(ref_fa)
    ref_genes = read_gff(root / "ref" / "genomic.gff")
    plasmid_len = len(read_fasta(out / "pw34.fa")["pw34"])
    feat_names = list(read_fasta(out / "pw34_features.fa"))
    epi_feats = feature_table(read_blast(out / "epi300_features.blast"))

    feats_tsv = ["colony\tfeature\tpw34_coords\tkind\tpercent_identity\tfraction_covered\tcolony_start\tcolony_end\tstrand\tin_EPI300_reference"]
    sv_tsv = ["colony\tevent\tcolony_contig\tcolony_start\tcolony_end\tEPI300_start\tEPI300_end\tlength\tgenes"]
    var_tsv = ["colony\tkind\tEPI300_pos\tEPI300_base\tcolony_base\tcolony_pos\tcontext"]
    md = ["# Kalen's CRAGE colonies against E. coli EPI300 (GCF_052692645.1)", ""]

    for c in COLONIES:
        asm_fa, gff = colony_paths(root, c)
        asm = read_fasta(asm_fa)
        genes = read_gff(gff)
        feats = feature_table(read_blast(out / f"c{c}_features.blast"))
        block = cargo_block(read_blast(out / f"c{c}_pw34.blast"), plasmid_len)
        paf = read_paf(out / f"c{c}_vs_epi300.paf")
        rpaf = read_paf(out / f"epi300_vs_c{c}.paf")
        md += [f"## Colony {c}", "", f"Assembly: {', '.join(f'{k} {len(v):,} bp' for k, v in asm.items())}.", ""]

        md.append("### pw34 features")
        md.append("")
        md.append("| feature | pw34 coords | identity | covered | colony position | also in EPI300? |")
        md.append("|---|---|---|---|---|---|")
        for name in feat_names:
            label, coords, kind = name.split("|")
            h = feats.get(name)
            e = epi_feats.get(name)
            in_ref = f"yes ({e['pid']:.1f}%, {e['len'] / e['qlen']:.0%})" if e and e["len"] / e["qlen"] > 0.5 else "no"
            if h:
                strand = "+" if h["ss"] < h["se"] else "-"
                feats_tsv.append(f"{c}\t{label}\t{coords}\t{kind}\t{h['pid']:.2f}\t{h['cov']:.3f}\t{min(h['ss'], h['se'])}\t{max(h['ss'], h['se'])}\t{strand}\t{in_ref}")
                md.append(f"| {label} | {coords} | {h['pid']:.1f}% | {h['cov']:.0%} | {min(h['ss'], h['se']):,}–{max(h['ss'], h['se']):,} ({strand}) | {in_ref} |")
            else:
                feats_tsv.append(f"{c}\t{label}\t{coords}\t{kind}\t\t0\t\t\t\t{in_ref}")
                md.append(f"| {label} | {coords} | — | absent | — | {in_ref} |")
        md.append("")

        cargo = None
        if block:
            cargo = (block["start"], block["end"])
            left = flank_mapping(paf, block["contig"], block["start"], "left")
            right = flank_mapping(paf, block["contig"], block["end"], "right")
            md.append(f"pw34 sequence spans colony {block['start'] + 1:,}–{block['end']:,} "
                      f"({block['end'] - block['start']:,} bp), covering {block['plasmid_covered']:,} of {plasmid_len:,} bp of the plasmid "
                      f"in {len(block['hits'])} BLAST segment(s).")
            for side, fl in (("Left", left), ("Right", right)):
                if fl:
                    md.append(f"- {side} flank: colony {fl['colony_pos']:,} joins EPI300 {fl['ref_pos']:,} "
                              f"({fl['strand']} strand, {fl['gap']:,} bp from the pw34 edge), "
                              f"{gene_at(ref_genes, fl['ref_contig'], fl['ref_pos'])}.")
            md.append("")
        else:
            md += ["No pw34 sequence found in this colony.", ""]

        md.append("### Large differences from EPI300 (≥ 200 bp)")
        md.append("")
        for s, e in uncovered([(r["qs"], r["qe"]) for r in paf], len(next(iter(asm.values())))):
            contig = next(iter(asm))
            tag = "insertion (in colony, not in EPI300)"
            if cargo and s < cargo[1] and e > cargo[0]:
                tag += ", overlaps pw34 cargo"
            gs = genes_in(genes, contig, s, e)
            sv_tsv.append(f"{c}\tinsertion\t{contig}\t{s + 1}\t{e}\t\t\t{e - s}\t{describe_genes(gs, 1000)}")
            md.append(f"- **{tag}** colony {s + 1:,}–{e:,} ({e - s:,} bp): {describe_genes(gs) or 'no annotated genes'}")
        ref_contig = next(iter(ref))
        for s, e in uncovered([(r["qs"], r["qe"]) for r in rpaf], len(ref[ref_contig])):
            gs = genes_in(ref_genes, ref_contig, s, e)
            sv_tsv.append(f"{c}\tdeletion\t\t\t\t{s + 1}\t{e}\t{e - s}\t{describe_genes(gs, 1000)}")
            md.append(f"- **deletion (in EPI300, missing from colony)** EPI300 {s + 1:,}–{e:,} ({e - s:,} bp): {describe_genes(gs) or 'no annotated genes'}")
        for s, e in depth_runs([(r["ts"], r["te"]) for r in paf]):
            gs = genes_in(ref_genes, ref_contig, s, e)
            sv_tsv.append(f"{c}\tduplication\t\t\t\t{s + 1}\t{e}\t{e - s}\t{describe_genes(gs, 1000)}")
            md.append(f"- **duplication (EPI300 region present twice in colony)** EPI300 {s + 1:,}–{e:,} ({e - s:,} bp): {describe_genes(gs) or 'no annotated genes'}")
        md.append("")

        vs = read_vars(out / f"c{c}_vs_epi300.var")
        n_snp = sum(v["kind"] == "SNP" for v in vs)
        md.append(f"### Small differences: {n_snp} SNPs, {len(vs) - n_snp} small indels")
        md.append("")
        for v in vs:
            ctx = gene_at(ref_genes, v["ctg"], v["s"])
            var_tsv.append(f"{c}\t{v['kind']}\t{v['s'] + 1}\t{v['ref']}\t{v['alt']}\t{v['qs'] + 1}\t{ctx}")
            md.append(f"- {v['kind']} EPI300 {v['s'] + 1:,} {v['ref']}→{v['alt']}: {ctx}")
        md.append("")

    md.append("## Colonies against each other")
    md.append("")
    for a in COLONIES:
        for b in COLONIES:
            if a >= b:
                continue
            paf = read_paf(out / f"c{b}_vs_c{a}.paf")
            aligned = sum(r["qe"] - r["qs"] for r in paf)
            nm = sum(r["nm"] for r in paf)
            qlen = paf[0]["qlen"] if paf else 0
            md.append(f"- Colony {b} vs colony {a}: {aligned:,} of {qlen:,} bp aligned, {nm:,} mismatched or gapped bases.")

    (out / "features.tsv").write_text("\n".join(feats_tsv) + "\n")
    (out / "structural.tsv").write_text("\n".join(sv_tsv) + "\n")
    (out / "small_variants.tsv").write_text("\n".join(var_tsv) + "\n")
    (out / "report.md").write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    {"features": cmd_features, "report": cmd_report}[sys.argv[1]](*sys.argv[2:])

"""E2, E3 and E4's solved plans beside E5's, step for step, with a ribbon per functional module.

Every drawing is a STEPS-mode DAG in the flexibility figure's monochrome ink. Rows are ordered so each
module's steps are consecutive where the dependencies allow it; each module's rows are tinted in its
colour, and a ribbon carries a module from the plan it came from to the rows it occupies in E5.

A step is labelled by its transform with the experiment's suffix dropped. E3 runs its contig batching and
its four viral callers once per assembly lane; those runs are drawn as one step each, as nf-core's one
CheckM2 process stands for metasmith's four. CheckV's batch and merge are drawn as one step, and so is
everything from curation to the island filter.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from html import unescape
from pathlib import Path

from PIL import ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))
GRAPHS = HERE / "graphs"
SCALE = 0.8
INK = ("#2b2b2b", "#dfe3ea")

from metasmith.models.dag_draw import Label  # noqa: E402
from metasmith.models.dag_renderer import SYNTHETIC, DagMode, DagRenderer, NodeKind  # noqa: E402

# One shade per group; the gaps between bands, the key and the step names tell a group's subgroups apart
ASM, BIN, VIR, GEM = "#636EFA", "#00CC96", "#EF553B", "#AB63FA"
MODULES = [  # (key, label, light, dark) in E5's row order
    ("short", "Short", ASM, ASM),
    ("hybrid", "Hybrid", ASM, ASM),
    ("long", "Long", ASM, ASM),
    ("bin", "Binning", BIN, BIN),
    ("vir", "Viromics", VIR, VIR),
    ("gem", "GEMs", GEM, GEM),
]
INSET = 4  # each band and ribbon end sits this far inside its rows, leaving twice this between sections
RANK = {m[0]: i for i, m in enumerate(MODULES)}
MODULE = {}
for keys, mod in [  # a read lane is its QC and its assembler; read mapping and gene calling feed the binners
    ("fastp fastqc_trimmed bbduk interleave_zipped_short_reads megahit spades", "short"),
    ("spades_hybrid opera_ms", "hybrid"),
    ("porechop_abi chopper filtlong flye", "long"),
    ("bowtie2_binning_bam minimap2_binning_bam assembly_stats prodigal metabat2 semibin2 comebin das_tool checkm2", "bin"),
    ("batch_contigs deepvirfinder vibrant virsorter2 genomad merge_candidate_calls viral_merge_calls "
     "contig_length_table batch_viral_contigs checkv votu", "vir"),
    ("carveme_init_db carveme_annotate_bigg carveme_carve_gapfill memote mag_orfs carveme_from_orfs memote_score", "gem"),
]:
    for k in keys.split():
        MODULE[k] = mod
RENAME = {"splitContigsForAmr": "batch_contigs", "split_hybrid_contigs": "batch_contigs",
          "split_viral_contigs": "batch_viral_contigs", "viral_split": "batch_viral_contigs",
          **dict.fromkeys(["checkv_batch", "checkv_merge"], "checkv"),
          # curation, MMseqs2 clustering, representatives and the island filter; E3's names, then E5's
          **dict.fromkeys(["curate_trim_batch", "curate_merge", "mmseqs_votu", "genomad_island_annotate",
                           "island_filter", "votu_curate_batch", "votu_curate_merge", "votu_cluster",
                           "votu_representatives", "votu_island_annotate", "votu_island_filter"], "votu")}
# Read QC reports, and E3's two recovery steps, scored against Pratama's published vOTUs; E5 has no
# counterpart to those, as E2's AMBER steps have none
CUT = {"fastqc_raw", "interleave_zipped_short_reads", "fastp_report", "seqkit_reads", "pratama_votu_recovery", "final_votu_recovery"}


def union(graphs, ids, **kw):
    """One renderer over several graphs, each node renamed by `ids(graph_index, node)`."""
    r = DagRenderer(**kw)
    for i, g in enumerate(graphs):
        for a, b in g._edges:
            for n in (a, b):
                r.add_node(g._nodes[n], ids(i, n), g.labels.get(n))
            r.add_edge(ids(i, a), ids(i, b))
    return r



def shared_step_ids(graphs, pooled=()):
    """Per graph, node -> id. A step is its transform, the types it makes, and the types it reads that every
    graph has, so two arms' steps meet where only arm-only inputs tell them apart. A transform in `pooled` is
    its name alone, so all its steps are one node, as nf-core runs one process over every bin set. A product
    is its producer's id and its type; an input is its type."""
    def typed(g):
        return {n: g.labels[n].name for n, k in g._nodes.items() if k is not NodeKind.TRANSFORM}
    common = set.intersection(*(set(typed(g).values()) for g in graphs))
    out = []
    for g in graphs:
        types, preds, succs = typed(g), defaultdict(set), defaultdict(set)
        for a, b in g._edges:
            succs[a].add(b)
            preds[b].add(a)
        ids = {n: n for n in SYNTHETIC if n in g._nodes}
        for n, k in g._nodes.items():
            if k is NodeKind.TRANSFORM and g.labels[n].name in pooled:
                ids[n] = g.labels[n].name
            elif k is NodeKind.TRANSFORM and n not in ids:
                ids[n] = "\x00".join([g.labels[n].name, *sorted({types[p] for p in preds[n]} & common),
                                      "->", *sorted(types[s] for s in succs[n])])
        unpooled = [i for n, i in ids.items() if g.labels[n].name not in pooled]
        assert len(set(unpooled)) == len(unpooled), "two steps of one graph share an id"
        for n, t in types.items():
            made_by = preds[n] - set(SYNTHETIC)
            ids[n] = f"{ids[min(made_by)]}\x00{t}" if made_by else t
        out.append(ids)
    return out



def monochrome(r, theme):
    """The flexibility figure's steps: filled in the ink, outlined at the data's weight, labelled unbolded."""
    dark = theme == "dark"
    styles = r._theme.styles
    step = replace(styles[NodeKind.TRANSFORM], fill=INK[dark], stroke=INK[dark], stroke_width=1.3, weight="normal")
    r._theme = replace(r._theme, styles={**styles, NodeKind.TRANSFORM: step})
    return r


def display(name):
    bare = re.sub(r"_(pratama|metagem)$", "", name)
    return RENAME.get(bare, bare)


# Title case, each tool spelled as its authors spell it
PRETTY = {
    "fastp": "fastp", "fastqc_trimmed": "FastQC Trimmed", "porechop_abi": "Porechop ABI", "chopper": "Chopper",
    "bbduk": "BBDuk", "filtlong": "Filtlong", "interleave_zipped_short_reads": "Interleave Zipped Short Reads",
    "megahit": "MEGAHIT", "spades": "SPAdes", "spades_hybrid": "SPAdes Hybrid", "flye": "Flye",
    "opera_ms": "OPERA-MS", "assembly_stats": "Assembly Stats", "prodigal": "Prodigal",
    "minimap2_binning_bam": "minimap2", "bowtie2_binning_bam": "Bowtie 2",
    "metabat2": "MetaBAT 2", "semibin2": "SemiBin2", "comebin": "COMEBin", "das_tool": "DAS Tool",
    "checkm2": "CheckM2", "batch_contigs": "Batch Contigs", "deepvirfinder": "DeepVirFinder",
    "vibrant": "VIBRANT", "virsorter2": "VirSorter2", "genomad": "geNomad",
    "merge_candidate_calls": "Merge Candidate Calls", "viral_merge_calls": "Merge Candidate Calls",
    "batch_viral_contigs": "Batch Viral Contigs", "checkv": "CheckV", "votu": "vOTUs",
    "contig_length_table": "Contig Length Table", "carveme_init_db": "CarveMe Init DB",
    "carveme_annotate_bigg": "CarveMe Annotate BiGG", "carveme_carve_gapfill": "CarveMe Carve Gapfill",
    "memote": "MEMOTE", "mag_orfs": "MAG ORFs", "carveme_from_orfs": "CarveMe from ORFs",
    "memote_score": "MEMOTE Score",
}
MODULE.update({PRETTY[k]: m for k, m in list(MODULE.items()) if k in PRETTY})


def relabel(r):
    for n, k in r._nodes.items():
        if k is NodeKind.TRANSFORM and n in r._labels:
            r._labels[n] = Label(display(r._labels[n].name))
    return r


def from_json(path):
    g = json.loads(Path(path).read_text())
    r = DagRenderer(mode=DagMode.PLAIN)
    for n, v in g["nodes"].items():
        r.add_node(NodeKind[{"GIVEN": "DATA"}.get(v["kind"], v["kind"])], n, Label(v["name"], v["namespace"] or ""))
    # a given's lineage is drawn as data-to-data edges; a steps-only drawing never shows them
    transforms = {n for n, v in g["nodes"].items() if v["kind"] == "TRANSFORM"}
    for a, b in g["edges"]:
        if a in transforms or b in transforms:
            r.add_edge(a, b)
    return r


def prune(r, cut):
    for n, k in list(r._nodes.items()):
        if k is NodeKind.TRANSFORM and r.labels[n].name in cut:
            r.remove_node(n)
    while True:
        made = {b for a, b in r._edges if r._nodes[a] is NodeKind.TRANSFORM and a != "given"}
        dead = [n for n, k in r._nodes.items()
                if k is not NodeKind.TRANSFORM and r.out_degree(n) == 0 and n not in made]
        if not dead:
            return r
        for n in dead:
            r.remove_node(n)


def pool_repeats(r):
    """One node per transform name: a step run once per lane is drawn once."""
    names = Counter(r.labels[n].name for n, k in r._nodes.items() if k is NodeKind.TRANSFORM)
    ids = shared_step_ids([r], pooled={n for n, c in names.items() if c > 1})
    return union([r], lambda i, n: ids[i][n])


def module_order(r):
    """A topological order of the steps that takes the earliest module first, and the renderer's own row
    order within a module."""
    nodes, edges = r._graph()
    default = {n: i for i, n in enumerate(r.layout().order)}
    preds, succs = defaultdict(set), defaultdict(set)
    for a, b in edges:
        succs[a].add(b)
        preds[b].add(a)
    rank = {n: RANK[MODULE[r.labels[n].name]] for n in nodes}
    ready = {n for n in nodes if not preds[n]}
    order = []
    while ready:
        n = min(ready, key=lambda x: (rank[x], default[x]))
        ready.remove(n)
        order.append(n)
        for c in succs[n]:
            preds[c].discard(n)
            if not preds[c]:
                ready.add(c)
    assert len(order) == len(nodes)
    return order


def steps(r, theme):
    s = DagRenderer(mode=DagMode.STEPS, theme=theme, background=False)
    s._nodes, s._labels, s._edges, s._seen_edges = dict(r._nodes), dict(r._labels), list(r._edges), set(r._edges)
    order = module_order(s)
    s._labels = {n: Label(PRETTY.get(l.name, l.name)) if s._nodes[n] is NodeKind.TRANSFORM else l for n, l in s._labels.items()}
    s.layout = lambda order_=None, _o=order: DagRenderer.layout(s, _o)
    return monochrome(s, theme)


def e2(theme):
    return steps(from_json(GRAPHS / "e2.graph.json"), theme)


def e3(theme):
    return steps(pool_repeats(prune(relabel(from_json(GRAPHS / "e3_pratama.graph.json")), CUT)), theme)


def e4(theme):
    return steps(relabel(from_json(GRAPHS / "e4_gems_repro.graph.json")), theme)


def split_carve(r):
    """E5's one CarveMe task, drawn as E4 runs it: the DIAMOND search, then carve and gap-fill from its hits.

    Requested of bench-E5 on 2026-10-04; until it lands, this is the figure's rendering only.
    """
    for n, k in list(r._nodes.items()):
        if k is NodeKind.TRANSFORM and r.labels[n].name == "carveme_from_orfs":
            hits, carve = f"{n}#hits", f"{n}#carve"
            outs = [(a, b) for a, b in r._edges if a == n]
            r._edges = [e for e in r._edges if e not in outs]
            r._seen_edges = set(r._edges)
            r._labels[n] = Label("carveme_annotate_bigg")
            r.add_node(NodeKind.DATA, hits, Label("bigg_diamond_hits"))
            r.add_node(NodeKind.TRANSFORM, carve, Label("carveme_carve_gapfill"))
            for e in [(n, hits), (hits, carve)] + [(carve, b) for _, b in outs]:
                r.add_edge(*e)
    return r


def e5(theme):
    graphs = [split_carve(prune(relabel(from_json(p)), CUT)) for p in sorted(GRAPHS.glob("e5_*.graph.json"))]
    # each shape runs each transform once, reading its own assembly, so a transform is one step across shapes
    ids = shared_step_ids(graphs, pooled={g.labels[n].name for g in graphs
                                             for n, k in g._nodes.items() if k is NodeKind.TRANSFORM})
    return steps(union(graphs, lambda i, n: ids[i][n]), theme)


def rows(svg):
    """(step name, row centre y) per step, and the drawing's size."""
    w, h = (float(x) for x in re.search(r'<svg[^>]*width="([\d.]+)" height="([\d.]+)"', svg).groups())
    out = []
    for name, pts in re.findall(r"<g><title>([^<]+)</title>\s*<polygon points=\"([^\"]+)\"", svg):
        ys = [float(p.split(",")[1]) for p in pts.split()]
        out.append((name, (min(ys) + max(ys)) / 2))
    return out, w, h


ARIAL = ImageFont.truetype("LiberationSans-Regular.ttf", 13)  # Arial's metrics
TITLE = ImageFont.truetype("LiberationSans-Bold.ttf", 26)


def text_right(svg):
    """The right edge of the drawing's widest step name; the renderer's own width budgets for 32 characters."""
    return max(float(x) + ARIAL.getlength(unescape(t))
               for x, t in re.findall(r'<text x="([\d.]+)"[^>]*>([^<]+)</text>', svg))


def inner(svg):
    return re.sub(r"^.*?<svg[^>]*>", "", svg, flags=re.S).rsplit("</svg>", 1)[0]


ROW = 31.2  # the renderer's row pitch


def bands(rs):
    """module -> [(y0, y1)] runs of consecutive rows, in the drawing's coordinates."""
    out = defaultdict(list)
    for name, y in sorted(rs, key=lambda t: t[1]):
        m = MODULE[name]
        if out[m] and abs(out[m][-1][1] - (y - ROW / 2)) < 1:
            out[m][-1] = (out[m][-1][0], y + ROW / 2)
        else:
            out[m].append((y - ROW / 2, y + ROW / 2))
    return out


TITLES = {"tools": ("nf-core/MAG", "Viromics", "metaGEM"), "domains": ("Metagenomics", "Viromics", "GEMs")}


def compose(theme, titles):
    """A over B over C on the left, packed tight; D on the right, its module key beside it. Each panel is
    named on a bar outside it, the left panels on their left, D outermost on the right."""
    dark = theme == "dark"
    ink, muted, surface = ("#DFE3EA", "#97A0B0", "#1B1E24") if dark else ("#1B1E24", "#5F6878", "#FFFFFF")
    colour = {m[0]: m[3 if dark else 2] for m in MODULES}
    label = {m[0]: m[1] for m in MODULES}
    tint, flow = (0.26, 0.32) if dark else (0.18, 0.26)

    panels = [("A", titles[0], e2(theme)), ("B", titles[1], e3(theme)),
              ("C", titles[2], e4(theme)), ("D", "Metasmith", e5(theme))]
    drawn = {}
    for letter, title, r in panels:
        svg = r.to_svg()
        rs, w, h = rows(svg)
        drawn[letter] = dict(letter=letter, title=title, svg=svg, rows=rs, w=text_right(svg), h=h, steps=len(rs),
                             top=min(y for _, y in rs) - ROW / 2, bottom=max(y for _, y in rs) + ROW / 2)
    A, B, C, D = (drawn[k] for k in "ABCD")
    # a panel shorter than its name gets room above and below, and its bar is stretched to cover the name
    slack = lambda d: max(0, TITLE.getlength(d["title"]) + 16 - (d["bottom"] - d["top"]))  # noqa: E731
    span = lambda d: d["bottom"] - d["top"] + CAP + slack(d)  # noqa: E731

    CAP, PAD, VGAP, FLOW_W, TOP, KEY_W, LEFT = 0, 10, 14, 150, 4, 96, 44
    l_w = LEFT + max(A["w"], B["w"], C["w"]) + 2 * PAD
    left_h = span(A) + span(B) + span(C) + 2 * VGAP
    H = TOP + max(left_h, span(D)) + 6
    y = TOP + (H - 6 - TOP - left_h) / 2
    for d in (A, B, C):
        d["col"] = (LEFT, l_w)
        d["x"], d["y"] = LEFT + PAD, y + CAP + slack(d) / 2 - d["top"]
        y += span(d) + VGAP
    D["col"] = (l_w + FLOW_W, l_w + FLOW_W + D["w"] + 2 * PAD)
    D["x"], D["y"] = D["col"][0] + PAD, TOP + (H - 6 - TOP - span(D)) / 2 + CAP - D["top"]
    key_x = D["col"][1] + 6
    W = key_x + KEY_W

    back, front = [], []
    for d in drawn.values():
        d["bands"] = {m: [(d["y"] + y0, d["y"] + y1) for y0, y1 in runs] for m, runs in bands(d["rows"]).items()}
        x0, x1 = d["col"]
        for m, runs in d["bands"].items():
            for y0, y1 in runs:
                back.append(f'<rect x="{x0:.1f}" y="{y0 + INSET:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0 - 2 * INSET:.1f}" '
                            f'rx="4" fill="{colour[m]}" fill-opacity="{tint}"/>')

    hull = lambda runs: (runs[0][0] + INSET, runs[-1][1] - INSET)  # noqa: E731

    def ribbon(m, xa, s0, s1, xb, u0, u1):
        cx = (xa + xb) / 2
        back.append(f'<path d="M {xa:.1f},{s0:.1f} C {cx:.1f},{s0:.1f} {cx:.1f},{u0:.1f} {xb:.1f},{u0:.1f} '
                    f'L {xb:.1f},{u1:.1f} C {cx:.1f},{u1:.1f} {cx:.1f},{s1:.1f} {xa:.1f},{s1:.1f} Z" '
                    f'fill="{colour[m]}" fill-opacity="{flow}"/>')

    # each side splits an E5 module's rows among its own sources, in stacking order, as a sankey's do
    for sources, xa, xb in (([A, B, C], l_w, D["col"][0]),):
        feeds = defaultdict(list)
        for d in sources:
            for m, runs in d["bands"].items():
                if m in D["bands"]:
                    feeds[m].append(hull(runs))
        for m, srcs in feeds.items():
            t0, t1 = hull(D["bands"][m])
            total = sum(s1 - s0 for s0, s1 in srcs)
            cursor = t0
            for s0, s1 in sorted(srcs):
                u0, u1 = cursor, cursor + (t1 - t0) * (s1 - s0) / total
                cursor = u1
                ribbon(m, xa, s0, s1, xb, u0, u1)

    font = 'font-family="Arial"'
    SIZE = 13  # the step names' size; a panel's name is twice it
    edge = "#8D97A8" if dark else "#666666"  # the DAGs' edge colour

    def bar(x, y0, y1, fill, text, fg, gap, size=SIZE, weight="normal"):
        """A 4-wide bar over [y0, y1] with its label read downward, `gap` from the bar's left edge."""
        front.append(f'<rect x="{x:.1f}" y="{y0 + 1:.1f}" width="4" height="{y1 - y0 - 2:.1f}" rx="2" fill="{fill}"/>')
        front.append(f'<text transform="translate({x + gap:.1f} {(y0 + y1) / 2:.1f}) rotate(90)" {font} '
                     f'font-size="{size}" font-weight="{weight}" fill="{fg}" text-anchor="middle">{text}</text>')

    def title(x, d, gap):
        y0, y1 = d["y"] + d["top"] + INSET, d["y"] + d["bottom"] - INSET
        over = max(0, (TITLE.getlength(d["title"]) + 12 - (y1 - y0)) / 2)
        bar(x, y0 - over, y1 + over, edge, d["title"], ink, gap, 2 * SIZE, "bold")

    for d in drawn.values():
        front.append(f'<g transform="translate({d["x"]:.1f} {d["y"]:.1f})">{inner(d["svg"])}</g>')
    # rotated text's glyphs lie on the +x side of its baseline, so a label left of its bar sits a glyph
    # height further from it than one on the right
    for d in (A, B, C):
        title(LEFT - 10, d, -25)

    # the key: each module named beside its rows in E5, reading downward
    for m, runs in D["bands"].items():
        y0, y1 = hull(runs)
        bar(key_x, y0, y1, colour[m], label[m], muted, 12)

    # the three read lanes bracketed together as assembly, outside their own key entries
    y0, y1 = hull(D["bands"]["short"])[0], hull(D["bands"]["long"])[1]
    bar(key_x + 30, y0, y1, edge, "Assembly", muted, 12)
    title(key_x + 60, D, 13)

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * SCALE:.0f}" height="{H * SCALE:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}"><rect width="100%" height="100%" fill="{surface}"/>'
           + "".join(back) + "".join(front) + "</svg>")
    return svg, {k: d["steps"] for k, d in drawn.items()}


if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    for variant, titles in TITLES.items():
        for theme in ("light", "dark"):
            svg, n = compose(theme, titles)
            (out / f"composition_{variant}_{theme}.svg").write_text(svg)
    print(n)

"""Draw the lineage and routing panels with metasmith's own DAG renderer as a section for the methods-panels page."""
import html
import re
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))

from metasmith.models.dag_renderer import DagRenderer, Label, NodeKind  # noqa: E402

# Figure 1C's hues, one per kind of step, so a reader matches steps across panels.
HUE = {"assemble": "#EF553B", "map": "#636EFA", "bin": "#00CC96", "classify": "#AB63FA",
       "compress": "#FFA15A"}
INK = {"light": "#2B2B2B", "dark": "#DFE3EA"}


def renderer(theme):
    """The house renderer, restyled to the assembly-flexibility figure: no step rules, solid data."""
    r = DagRenderer(theme=theme, background=False)
    st = r._theme.styles
    st = {**st,
          NodeKind.TRANSFORM: replace(st[NodeKind.TRANSFORM], heading=False, weight="normal", stroke_width=1.3),
          NodeKind.DATA: replace(st[NodeKind.DATA], fill=INK[theme], stroke=INK[theme])}
    r._theme = replace(r._theme, styles=st)
    return r


def draw(steps, theme, given=(), target=(), lineage=()):
    """steps: (id, kind, label, inputs, outputs). given/target add the hollow synthetic ends."""
    r = renderer(theme)
    hues = {}
    for tid, kind, label, ins, outs in steps:
        r.add_node(NodeKind.TRANSFORM, tid, Label(name=label))
        if kind:
            hues[label] = HUE[kind]
        for i in ins:
            r.add_edge(i, tid)
        for o in outs:
            r.add_edge(tid, o)
    if given:
        r.add_node(NodeKind.TRANSFORM, "given", Label(name=""))
        for g in given:
            r.add_edge("given", g)
    if target:
        r.add_node(NodeKind.TRANSFORM, "target", Label(name=""))
        for t in target:
            r.add_edge(t, "target")
    for parent, child in lineage:
        r.add_edge(parent, child)
    return tint(r.to_svg(), hues)


def tint(svg, hues):
    def one(m):
        hue = hues.get(html.unescape(m.group(1)))
        if not hue:
            return m.group(0)
        return re.sub(r'(<polygon[^>]*?)fill="[^"]*"( stroke=")[^"]*"', rf'\1fill="{hue}"\2{hue}"', m.group(0), count=1)
    svg = re.sub(r"<g><title>([^<]*)</title>.*?</g>", one, svg, flags=re.S)
    return svg.split("?>", 1)[-1].strip()


def both(**kw):
    return {t: draw(theme=t, **kw) for t in ("light", "dark")}


ROUTING = [
    ("asmA", "assemble", "assemble (group)", ["reads 1", "reads 2"], ["co-assembly 1+2"]),
    ("asmB", "assemble", "assemble", ["reads 3"], ["assembly 3"]),
    ("m1", "map", "map (join)", ["reads 1", "co-assembly 1+2"], ["BAM 1"]),
    ("m2", "map", "map (join) ", ["reads 2", "co-assembly 1+2"], ["BAM 2"]),
    ("m3", "map", "map (join)  ", ["reads 3", "assembly 3"], ["BAM 3"]),
    ("binA", "bin", "bin (group by assembly)", ["co-assembly 1+2", "BAM 1", "BAM 2"], ["bins 1+2"]),
    ("binB", "bin", "bin", ["assembly 3", "BAM 3"], ["bins 3"]),
    ("clsA", "classify", "classify (cross)", ["bins 1+2", "reference DB"], ["taxonomy 1+2"]),
    ("clsB", "classify", "classify (cross) ", ["bins 3", "reference DB"], ["taxonomy 3"]),
]

PANELS = [
    ("A", "No constraint", {
        "Given": both(steps=[], given=["reads"]),
        "Target": both(steps=[], target=["compressed file"]),
        "Plan": both(steps=[("gz", "compress", "compress", ["reads"], ["compressed file"])]),
    }),
    ("B", "Lineage constraint", {
        "Given": both(steps=[], given=["reads"]),
        "Target": both(steps=[], target=["compressed file"], lineage=[("assembly", "compressed file")]),
        "Plan": both(steps=[("asm", "assemble", "assemble", ["reads"], ["assembly"]),
                            ("gz", "compress", "compress", ["assembly"], ["compressed file"])]),
    }),
    ("C", "Rows: join, group, cross", {
        "Given": both(steps=[], given=["reads 1", "reads 2", "reads 3", "reference DB"]),
        "Target": both(steps=[], target=["taxonomy"]),
        "Plan": both(steps=ROUTING),
    }),
]


STYLE = """<style>
  /* Routing figure: panels side by side on a shared Given / Target / Plan grid. */
  .rp-entry { background:var(--surface); border:1px solid var(--rule); border-radius:10px; padding:16px 18px 18px; min-width:0; }
  .rp-head { display:flex; align-items:baseline; gap:10px 14px; flex-wrap:wrap; border-bottom:1px solid var(--rule); padding-bottom:12px; margin-bottom:16px; }
  .rp-head h2 { font-size:15px; font-weight:600; margin:0; }
  .rp-head .sub { color:var(--muted); font-size:12.5px; }
  .rp-head p { flex-basis:100%; margin:0; color:var(--muted); font-size:12.5px; }
  .rp-scroll { overflow-x:auto; }
  .rp-fig { display:grid; grid-template-columns:1.6rem repeat(3, max-content); column-gap:36px; row-gap:10px; }
  .rp-rowlbl { grid-column:1; writing-mode:vertical-rl; transform:rotate(180deg); justify-self:center; align-self:center; font-size:11.5px; color:var(--faint); }
  .rp-panel { margin:0; display:grid; grid-row:1 / span 4; grid-template-rows:subgrid; }
  .rp-panel figcaption { font-weight:500; font-size:13.5px; display:flex; gap:8px; align-items:baseline; white-space:nowrap; }
  .rp-panel .letter { font-weight:600; }
  .rp-cell svg { display:block; }
  .rp-given { align-self:start; } .rp-target { align-self:end; } .rp-plan { align-self:start; }
  .rp-dark { display:none; }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) .rp-light { display:none; }
    :root:not([data-theme="light"]) .rp-dark { display:block; }
  }
  :root[data-theme="dark"] .rp-light { display:none; }
  :root[data-theme="dark"] .rp-dark { display:block; }
</style>"""


def section():
    rows = ["Given", "Target", "Plan"]
    cols = []
    for i, (letter, title, cells) in enumerate(PANELS):
        parts = [f'<figure class="rp-panel" style="grid-column:{i + 2}">'
                 f'<figcaption><span class="letter">{letter}</span><span>{html.escape(title)}</span></figcaption>']
        for j, row in enumerate(rows):
            for t in ("light", "dark"):
                parts.append(f'<div class="rp-cell rp-{row.lower()} rp-{t}" style="grid-row:{j + 2}">{cells[row][t]}</div>')
        parts.append("</figure>")
        cols.append("".join(parts))
    labels = "".join(f'<span class="rp-rowlbl" style="grid-row:{j + 2}">{r}</span>' for j, r in enumerate(rows))
    return (STYLE + '\n<section class="rp-entry" id="panel-routing" aria-labelledby="rp-title">'
            '<div class="rp-head"><h2 id="rp-title">Lineage and routing</h2><span class="sub">A no constraint · B lineage constraint · C rows</span>'
            "<p>Drawn with metasmith's DAG renderer. A and B ask for the same file; B's lineage constraint names the assembly it must descend from. "
            "C runs three samples, two co-assembled: mapping joins each sample to its own assembly, binning groups every BAM on one assembly into one task, "
            "and the reference DB, which shares no lineage with any sample, crosses to every bin set. Triangle hues match the solver panel.</p></div>"
            f'<div class="rp-scroll"><div class="rp-fig">{labels}{"".join(cols)}</div></div></section>')


if __name__ == "__main__":
    (HERE / "routing_section.html").write_text(section())
    print("wrote", HERE / "routing_section.html")

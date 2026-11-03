"""Draw the overview figure's DAG-renderer pieces (specification, plan, execution grid) and splice the figure into the methods-panels page."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "routing_panels"))

from build import draw  # noqa: E402

INK = {"light": {"cell": "#2B2B2B", "text": "#111111", "muted": "#7A7A7A", "fill": "#F1F2F5"},
       "dark": {"cell": "#DFE3EA", "text": "#DFE3EA", "muted": "#8D97A8", "fill": "#262A31"}}

# The plan's shape: t1 makes several b from one a; t2 runs once per b (group by b), takes a as well, and makes several c.
PLAN = [("t1", None, "t1", ["a"], ["b"]),
        ("t2", None, "t2", ["a", "b"], ["c"])]
# The specification's library holds more than the plan uses: bin is offered and left out.
LIBRARY = [[("asm", None, "assemble", ["reads"], ["assembly"])],
           [("map", None, "map", ["reads", "assembly"], ["BAM"])],
           [("bin", None, "bin", ["assembly"], ["MAG", "unbinned"])]]
COLUMNS = 4
# Per data row, the instance columns each cell spans. One a; two b from it; two c from each b, drawn as one cell per b
# with a line down its middle, since t2 groups by b.
CELLS = {"a": [[0, 1, 2, 3]], "b": [[0, 1], [2, 3]], "c": [[0, 1], [2, 3]]}
DIVIDED = {"c"}


def piece(svg):
    m = re.match(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"[^>]*>(.*)</svg>\s*$', svg, flags=re.S)
    return {"w": float(m.group(1)), "h": float(m.group(2)), "body": m.group(3)}


def hollow(svg):
    """Data nodes drawn open, filled with the background the transforms already use."""
    bg = re.search(r'<polygon[^>]*fill="([^"]+)"', svg).group(1)
    return re.sub(r'(<circle[^>]*?)fill="[^"]*"', rf'\1fill="{bg}"', svg)


def bare(svg, pad=6.0):
    """No node labels, and the frame cropped to the graph; returns the piece and its y shift."""
    svg = re.sub(r"<text[^>]*>[^<]*</text>", "", svg)
    xs, ys = [], []
    for x, y in re.findall(r"[ML] ([\d.]+),([\d.]+)", svg) + re.findall(r"A [\d.]+,[\d.]+ \d \d \d ([\d.]+),([\d.]+)", svg):
        xs.append(float(x)); ys.append(float(y))
    for cx, cy, r in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"', svg):
        xs += [float(cx) - float(r), float(cx) + float(r)]; ys += [float(cy) - float(r), float(cy) + float(r)]
    for pts in re.findall(r'<polygon points="([^"]+)"', svg):
        for x, y in (p.split(",") for p in pts.split()):
            xs.append(float(x)); ys.append(float(y))
    p = piece(svg)
    dx, dy = pad - min(xs), pad - min(ys)
    return {"w": max(xs) - min(xs) + 2 * pad, "h": max(ys) - min(ys) + 2 * pad,
            "body": f'<g transform="translate({dx:.1f} {dy:.1f})">{p["body"]}</g>'}, dy


def data_rows(svg):
    return {t: float(cy) for t, cy in re.findall(r'<g><title>([^<]+)</title>\s*<circle cx="[\d.]+" cy="([\d.]+)"', svg)}


def plan(theme):
    return hollow(draw(PLAN, theme, given=["a"], target=["c"]))


def plan_and_grid(theme):
    """The plan without labels, and the execution grid beside it with each row level with its data node."""
    svg = plan(theme)
    ys, ink = data_rows(svg), INK[theme]
    p, dy = bare(svg)
    cw, ch, gap = 30.0, 16.0, 4.0
    out = []
    for name, spans in CELLS.items():
        y = ys[name] + dy - ch / 2
        for cols in spans:
            x = cols[0] * (cw + gap)
            w = len(cols) * cw + (len(cols) - 1) * gap
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{ch:.1f}" rx="3" fill="{ink["fill"]}" '
                       f'stroke="{ink["cell"]}" stroke-width="1.1"/>')
            if name in DIVIDED:
                out.append(f'<line x1="{x + w / 2:.1f}" y1="{y:.1f}" x2="{x + w / 2:.1f}" y2="{y + ch:.1f}" '
                           f'stroke="{ink["cell"]}" stroke-width="1.1"/>')
    gw = COLUMNS * cw + (COLUMNS - 1) * gap
    top, bot = min(ys.values()) + dy - ch / 2, max(ys.values()) + dy + ch / 2
    label = lambda x, y, t, extra="": (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" font-size="13" fill="{ink["text"]}" '
                                       f'text-anchor="middle"{extra}>{t}</text>')
    out.append(label(gw / 2, top - 7, "instances"))
    out.append(f'<line x1="{gw + 8:.1f}" y1="{top:.1f}" x2="{gw + 8:.1f}" y2="{bot:.1f}" stroke="{ink["text"]}" stroke-width="1.1"/>')
    out.append(label(gw + 20, (top + bot) / 2, "types", f' transform="rotate(90 {gw + 20:.1f} {(top + bot) / 2:.1f})" dominant-baseline="central"'))
    for i, cols in enumerate(CELLS["c"]):
        x = cols[0] * (cw + gap) + (len(cols) * cw + (len(cols) - 1) * gap) / 2
        out.append(label(x, ys["c"] + dy + ch / 2 + 15, f"job {i + 1}"))
    return p, {"w": gw + 30, "h": p["h"], "body": "".join(out)}


def spec_piece(svg, row=None):
    """A specification piece: open nodes, no labels. Its anchor is the y of the named data row, else of its transform."""
    rows = data_rows(svg)
    p, dy = bare(hollow(svg))
    if row:
        return {**p, "anchor": rows[row] + dy}
    tri = [float(y) for y in re.findall(r"[\d.]+,([\d.]+)", re.search(r'<polygon points="([^"]+)"', svg).group(1))]
    return {**p, "anchor": sum(tri) / len(tri) + dy}


def specification(theme):
    return {"given": spec_piece(draw([], theme, given=["reads"]), "reads"),
            "library": [spec_piece(draw(steps, theme)) for steps in LIBRARY],
            "targets": spec_piece(draw([], theme, target=["BAM"]), "BAM")}


def data():
    out = {}
    for t in ("light", "dark"):
        plan_piece, grid_piece = plan_and_grid(t)
        out[t] = {"plan": plan_piece, "grid": grid_piece, "spec": specification(t)}
    return out


def splice(page: Path, section: Path, script: Path):
    html = page.read_text()
    blob = json.dumps(data(), separators=(",", ":")).replace("</", "<\\/")
    block = (section.read_text().replace("__OV_DATA__", blob))
    html = re.sub(r"<!-- ov:start -->.*?<!-- ov:end -->\n?", "", html, flags=re.S)
    html = html.replace('  <section class="panel" id="panel-2"', f"<!-- ov:start -->\n{block}<!-- ov:end -->\n" + '  <section class="panel" id="panel-2"', 1)
    js = script.read_text()
    html = re.sub(r"  // ov:js:start.*?// ov:js:end\n", "", html, flags=re.S)
    html = html.replace("  const built = {};\n", "  const built = {};\n" + js, 1)
    html = re.sub(r"(    document\.getElementById\(\"p2-fig\"\)\.innerHTML = p2;\n)(?!    drawOverview)", r"\1    drawOverview(pal);\n", html, count=1)
    page.write_text(html)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("page", type=Path, help="methods_panels.html to splice the overview into, in place")
    args = ap.parse_args()
    splice(args.page, HERE / "section.html", HERE / "overview.js")
    print("spliced into", args.page)

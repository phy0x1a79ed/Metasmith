"""Draw the overview figure's DAG-renderer pieces (lineage pair, rows) and splice the figure into the methods-panels page."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "routing_panels"))

from build import HUE, draw  # noqa: E402

HUE.update({"bin": "#00CC96", "genes": "#FFA15A"})
INK = {"light": {"cell": "#2B2B2B", "text": "#111111", "muted": "#7A7A7A", "fill": "#F1F2F5"},
       "dark": {"cell": "#DFE3EA", "text": "#DFE3EA", "muted": "#8D97A8", "fill": "#262A31"}}

PLAIN = [("asm", "assemble", "assemble", ["reads"], ["assembly"]),
         ("orf", "genes", "call genes", ["assembly"], ["ORFs"])]
VIA_MAG = [("asm", "assemble", "assemble", ["reads"], ["assembly"]),
           ("bin", "bin", "bin", ["assembly"], ["MAG"]),
           ("orf", "genes", "call genes", ["MAG"], ["ORFs"])]
ROWS = [("asm", "assemble", "assemble", ["reads"], ["assembly"]),
        ("map", "map", "map", ["reads", "assembly"], ["BAM"])]
SAMPLES = ["S1", "S2", "S3"]
# Per data row, the sample columns each cell spans: assembly co-assembles S1 and S2.
CELLS = {"reads": [[0], [1], [2]], "assembly": [[0, 1], [2]], "BAM": [[0], [1], [2]]}


def piece(svg):
    m = re.match(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"[^>]*>(.*)</svg>\s*$', svg, flags=re.S)
    return {"w": float(m.group(1)), "h": float(m.group(2)), "body": m.group(3)}


def data_rows(svg):
    return {t: float(cy) for t, cy in re.findall(r'<g><title>([^<]+)</title>\s*<circle cx="[\d.]+" cy="([\d.]+)"', svg)}


def lineage(theme):
    return {"plain": piece(draw(PLAIN, theme, given=["reads"], target=["ORFs"])),
            "mag": piece(draw(VIA_MAG, theme, given=["reads"], target=["ORFs"]))}


def rows(theme):
    svg = draw(ROWS, theme, given=["reads"], target=["BAM"])
    p, ys, ink = piece(svg), data_rows(svg), INK[theme]
    cw, ch, gap, x0 = 30.0, 16.0, 4.0, p["w"] + 14
    out = [p["body"]]
    head_y = min(ys.values()) - 26
    for i, s in enumerate(SAMPLES):
        out.append(f'<text x="{x0 + i * (cw + gap) + cw / 2:.1f}" y="{head_y:.1f}" font-family="Arial" font-size="13" '
                   f'fill="{ink["text"]}" text-anchor="middle">{s}</text>')
    for name, spans in CELLS.items():
        y = ys[name] - ch / 2
        for cols in spans:
            x = x0 + cols[0] * (cw + gap)
            w = len(cols) * cw + (len(cols) - 1) * gap
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{ch:.1f}" rx="3" fill="{ink["fill"]}" '
                       f'stroke="{ink["cell"]}" stroke-width="1.1"/>')
    return {"w": x0 + 3 * cw + 2 * gap + 4, "h": p["h"], "body": "".join(out)}


def data():
    return {t: {"lineage": lineage(t), "rows": rows(t)} for t in ("light", "dark")}


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

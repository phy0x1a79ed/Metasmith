#!/usr/bin/env python3
"""Fill both page templates from the solved plan and the rendered DAG.

    python research/kalen_crage/page.py

Reads results/plan.json and results/kalen_crage_dag.svg. Writes two pages from one plan:
kalen_crage_plan.html for Tony, which carries the choices that are his, and
kalen_crage_for_kalen.html for the depositor, which carries neither those nor any result.
Run it after build.sh.
"""

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
MOCK_LIBRARY = "crage"

# The DAG's own white plate is drawn by the page, which also has to work in a dark theme, so the
# graphviz background rect goes rather than sitting a hard white rectangle inside a styled one.
BACKGROUND_RECT = re.compile(r'<rect width="\d+" height="\d+" fill="#FFFFFF"/>\s*')


def rows(steps: list[dict]) -> str:
    out = []
    for s in steps:
        proposed = s["library"] == MOCK_LIBRARY
        tag = '<span class="tag prop">proposed</span>' if proposed \
            else f'<span class="tag real">{html.escape(s["library"])}</span>'
        makes = ", ".join(t.split("::", 1)[1] for t in s["makes"]) or "&mdash;"
        out.append(f'<tr><td class="n">{s["order"]}</td>'
                   f'<td class="s">{html.escape(s["name"])}</td>'
                   f"<td>{tag}</td><td class=\"m\">{makes}</td></tr>")
    return "\n".join(out)


def main() -> None:
    plan = json.loads((RESULTS / "plan.json").read_text())
    svg = (RESULTS / "kalen_crage_dag.svg").read_text()
    svg = svg[svg.index("<svg"):]
    svg = BACKGROUND_RECT.sub("", svg, count=1)
    steps = plan["steps"]
    proposed = [s for s in steps if s["library"] == MOCK_LIBRARY]

    fields = {
        "__SVG__": svg,
        "__ROWS__": rows(steps),
        "__NCOL__": str(len(plan["colonies"])),
        "__NSTEP__": str(len(steps)),
        "__NREAL__": str(len(steps) - len(proposed)),
        "__NPROP__": str(len(proposed)),
        "__PARENT__": html.escape(plan["parent"][0]),
        "__ACC__": html.escape(plan["parent"][1]),
    }
    for template, name in (("page.template.html", "kalen_crage_plan.html"),
                           ("page_kalen.template.html", "kalen_crage_for_kalen.html")):
        page = (HERE / template).read_text()
        for key, value in fields.items():
            page = page.replace(key, value)
        left = sorted(set(re.findall(r"__[A-Z]+__", page)))
        assert not left, f"{template}: unfilled placeholders: {left}"
        out = RESULTS / name
        out.write_text(page)
        print(f"{out} ({out.stat().st_size / 1024:.0f} KB)")
    print(f"{len(steps)} steps, {len(proposed)} proposed")


if __name__ == "__main__":
    main()

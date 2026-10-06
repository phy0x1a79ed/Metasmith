"""Export the manuscript's figure SVGs (light theme) from their pages with headless Chrome."""
import argparse
import base64
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "methods_panels"))
import build as methods_build  # noqa: E402

LIGHT = '<script>document.documentElement.dataset.theme = "light";</script>'

# Each hook leaves `name=<base64 svg>` lines in #export once the page has drawn.
METHODS_HOOK = """<pre id="export"></pre><script>
setTimeout(() => {
  const svg = document.querySelector("#p2-fig svg");
  const s = new XMLSerializer().serializeToString(svg);
  document.getElementById("export").textContent = "methods=" + btoa(unescape(encodeURIComponent(s)));
}, 3000);
</script>"""

REPRO_HOOK = """<pre id="export"></pre><script>
setTimeout(async () => {
  const out = [];
  for (const [id, name] of [["fig", "reproduction"], ["figS", "reproduction_supp"]]) {
    const gd = document.getElementById(id), { width, height } = gd._fullLayout;
    const url = await Plotly.toImage(gd, { format: "svg", width, height });
    out.push(name + "=" + btoa(unescape(encodeURIComponent(decodeURIComponent(url.slice(url.indexOf(",") + 1))))));
  }
  document.getElementById("export").textContent = out.join("\\n");
}, 4000);
</script>"""


def dump(page: str, tmp: Path) -> dict[str, str]:
    src = tmp / "page.html"
    src.write_text(page)
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    dom = subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run", "--disable-crash-reporter",
                          f"--user-data-dir={tmp}/profile", "--window-size=1100,1400", "--virtual-time-budget=20000",
                          "--dump-dom", src.as_uri()], check=True, capture_output=True, text=True).stdout
    body = html.unescape(re.search(r'<pre id="export">(.*?)</pre>', dom, re.S).group(1))
    found = dict(line.split("=", 1) for line in body.split() if "=" in line)
    if not found:
        raise SystemExit("page drew nothing to export")
    return {k: base64.b64decode(v).decode() for k, v in found.items()}


def with_hook(page: str, hook: str) -> str:
    return page.replace("</body>", LIGHT + hook + "</body>") if "</body>" in page else page + LIGHT + hook


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        svgs = dump(with_hook(methods_build.build(), METHODS_HOOK), tmp)
        svgs |= dump(with_hook((HERE / "reproduction" / "reproduction.html").read_text(), REPRO_HOOK), tmp)
    for name, svg in svgs.items():
        path = args.out / f"{name}.svg"
        path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + svg if not svg.startswith("<?xml") else svg)
        print(f"{path} ({len(svg)} chars)")


if __name__ == "__main__":
    main()

"""Build methods_panels.html from the template and the Excalidraw scenes, optionally screenshotting it."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENES = ["interface", "types", "solver"]
KEEP = ["id", "type", "x", "y", "width", "height", "angle", "strokeColor", "backgroundColor", "fillStyle",
        "strokeWidth", "strokeStyle", "roundness", "opacity", "points", "elbowed", "startArrowhead",
        "endArrowhead", "startBinding", "endBinding", "text", "fontSize", "fontFamily", "textAlign",
        "verticalAlign", "containerId", "lineHeight", "groupIds", "isDeleted"]
THEME_HOOK = 'try { setTheme(localStorage.getItem("methods-panels-theme")); }'


def build() -> str:
    scenes = {}
    for name in SCENES:
        elements = json.loads((HERE / "excal" / f"{name}.json").read_text())["elements"]
        scenes[name] = [{k: e.get(k) for k in KEEP} for e in elements if not e.get("isDeleted")]
    data = json.dumps({"scenes": scenes}, separators=(",", ":")).replace("</", "<\\/")
    return (HERE / "methods_panels.template.html").read_text().replace("__DATA__", data)


def screenshot(html: str, theme: str, out: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    page = f"<!doctype html><html><head><meta charset=utf8></head><body>{html.replace(THEME_HOOK, f'try {{ setTheme({theme!r}); }}')}</body></html>"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        src.write_text(page)
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}/profile",
                        "--window-size=1100,1400", "--virtual-time-budget=8000", f"--screenshot={out}", src.as_uri()],
                       check=True, capture_output=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=HERE / "methods_panels.html")
    ap.add_argument("--preview", nargs="*", choices=["light", "dark"], help="screenshot these themes beside --out")
    args = ap.parse_args()
    html = build()
    args.out.write_text(html)
    print(f"built: {args.out} ({len(html.encode())} bytes)")
    for theme in args.preview or []:
        png = args.out.with_name(f"preview_{theme}.png")
        screenshot(html, theme, png)
        print(f"preview: {png}")


if __name__ == "__main__":
    main()

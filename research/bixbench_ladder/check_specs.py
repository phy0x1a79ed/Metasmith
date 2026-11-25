"""Run each spec's script on its synthetic fixture, inside the image and offline.

    ./check_specs.sh [tool ...]

A fixture is specs/fixtures/<tool>/ holding one file or directory per input slot, named
<slot>.<ext> or <slot>, and an optional params.json that overrides parameter defaults.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from generate import INTERPRETERS, lint, load

SPECS = Path(__file__).resolve().parent / "specs"


def slot_path(base: Path, slot: str, ext: str | None) -> Path:
    return base / (f"{slot}.{ext}" if ext else slot)


def check(types: dict, tool: dict) -> str | None:
    fixture = SPECS / "fixtures" / tool["name"]
    if not fixture.is_dir():
        return "no fixture"
    env = dict(os.environ)
    for slot, t in tool["inputs"].items():
        path = slot_path(fixture, slot, types[t].get("ext"))
        if not path.exists():
            return f"fixture lacks {path.name}"
        env[f"IN_{slot}"] = str(path)
    overrides = json.loads((fixture / "params.json").read_text()) if (fixture / "params.json").exists() else {}
    for name, p in (tool.get("params") or {}).items():
        env[f"PARAM_{name}"] = str(overrides.get(name, p["default"]))
    with tempfile.TemporaryDirectory() as work:
        outputs = {slot: slot_path(Path(work) / "out", slot, types[t].get("ext")) for slot, t in tool["outputs"].items()}
        (Path(work) / "out").mkdir()
        for slot, path in outputs.items():
            env[f"OUT_{slot}"] = str(path)
        (Path(work) / "step_script").write_text(tool["script"])
        run = subprocess.run([*INTERPRETERS[tool["interpreter"]], "step_script"], cwd=work, env=env,
                             capture_output=True, text=True, timeout=900)
        if run.returncode != 0:
            return f"exit {run.returncode}: {(run.stderr or run.stdout)[-1500:]}"
        for slot, path in outputs.items():
            if not path.exists() or (path.is_file() and path.stat().st_size == 0):
                return f"output {slot} is missing or empty"
            if "-v" in sys.argv:
                shown = "\n".join(sorted(p.name for p in path.iterdir())[:10]) if path.is_dir() else path.read_text(errors="replace")[:600]
                print(f"--- {tool['name']}.{slot}\n{shown}")
    return None


def main() -> None:
    types, tools = load(SPECS)
    wanted = {a for a in sys.argv[1:] if not a.startswith("-")}
    errors = [e for e in lint(types, tools) if not wanted or e.split(":")[0] in wanted]
    if errors:
        sys.exit("\n".join(errors))
    failed = 0
    for tool in tools:
        if wanted and tool["name"] not in wanted:
            continue
        problem = check(types, tool)
        failed += problem is not None
        print(f"{'FAIL' if problem else 'ok  '} {tool['name']}{': ' + problem if problem else ''}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

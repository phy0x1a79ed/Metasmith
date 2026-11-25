from __future__ import annotations

import json
import subprocess
import tempfile


def ask(model: str, system: str, prompt: str, timeout: int = 300) -> dict:
    # A neutral directory keeps the host's AGENTS.md and memory out of the call's context.
    with tempfile.TemporaryDirectory(dir="/var/tmp") as cwd:
        out = subprocess.run(
            ["claude", "--print", "--output-format", "json", "--model", model, "--tools", "",
             "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
             "--no-session-persistence", "--system-prompt", system, prompt],
            cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout, check=True,
        ).stdout
    r = json.loads(out)
    return {"text": r.get("result") or "", "usage": r.get("usage"), "cost_usd": r.get("total_cost_usd")}

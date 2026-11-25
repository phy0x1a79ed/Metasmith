"""Stdio MCP server that is the benchmark agent's only way to act: it runs commands in one container.

The agent process stays on the host with no built-in tools, so the container needs no
credentials and no network. Every call is appended to SANDBOX_LOG, which is also the
record of which tools (the planner among them) a run used.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

CONTAINER = os.environ["SANDBOX_CONTAINER"]
LOG = os.environ["SANDBOX_LOG"]
MAX_STEPS = int(os.environ["SANDBOX_MAX_STEPS"])
MAX_OUTPUT = 20_000
DEFAULT_TIMEOUT_S = 300
MAX_TIMEOUT_S = 1200

TOOLS = [
    {
        "name": "bash",
        "description": (
            "Run a bash command in the analysis machine, starting in /workspace. "
            "Returns stdout and stderr together, then the exit code. State is kept "
            "in files only: each call is a fresh shell."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_s": {
                    "type": "integer",
                    "description": f"Default {DEFAULT_TIMEOUT_S}, maximum {MAX_TIMEOUT_S}.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": "Write text to a file in the analysis machine. Relative paths resolve from /workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
]


def _exec(argv: list[str], stdin: str | None, timeout_s: int) -> tuple[int, str]:
    # `timeout` runs inside the container so the command dies with its children;
    # the outer timeout only covers a hung docker client.
    full = ["docker", "exec", "-i", "-w", "/workspace", CONTAINER,
            "timeout", "-k", "5", str(timeout_s), *argv]
    try:
        p = subprocess.run(full, input=stdin, capture_output=True, text=True,
                           errors="replace", timeout=timeout_s + 30)
    except subprocess.TimeoutExpired:
        return 124, "the command did not return"
    return p.returncode, p.stdout + p.stderr


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT:
        return text
    half = MAX_OUTPUT // 2
    return f"{text[:half]}\n[... {len(text) - MAX_OUTPUT} characters omitted ...]\n{text[-half:]}"


def _call(name: str, args: dict) -> str:
    if name == "bash":
        timeout_s = min(int(args.get("timeout_s") or DEFAULT_TIMEOUT_S), MAX_TIMEOUT_S)
        code, out = _exec(["bash", "-c", args["command"]], None, timeout_s)
        note = f" (timed out after {timeout_s} s)" if code == 124 else ""
        return f"{_clip(out)}\n[exit code {code}{note}]"
    if name == "write_file":
        script = 'mkdir -p "$(dirname "$1")" && cat > "$1"'
        code, out = _exec(["bash", "-c", script, "_", args["path"]], args["content"], 60)
        return f"wrote {args['path']}" if code == 0 else f"{out}\n[exit code {code}]"
    raise ValueError(f"unknown tool {name}")


def main() -> None:
    steps = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        req = json.loads(line)
        method, rid = req.get("method"), req.get("id")
        if rid is None:
            continue
        if method == "initialize":
            result = {
                "protocolVersion": req["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "sandbox", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            steps += 1
            name, args = req["params"]["name"], req["params"].get("arguments") or {}
            start = time.time()
            if steps > MAX_STEPS:
                text, is_error = "Step limit reached. Give your final answer now.", True
            else:
                try:
                    text, is_error = _call(name, args), False
                except Exception as e:  # a bad call is the agent's to recover from
                    text, is_error = f"{type(e).__name__}: {e}", True
            with open(LOG, "a") as fp:
                fp.write(json.dumps({
                    "step": steps, "tool": name, "args": args, "t": start,
                    "seconds": round(time.time() - start, 2), "output": text,
                }) + "\n")
            result = {"content": [{"type": "text", "text": text}], "isError": is_error}
        elif method == "ping":
            result = {}
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "error": {
                "code": -32601, "message": f"method not found: {method}"}}) + "\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

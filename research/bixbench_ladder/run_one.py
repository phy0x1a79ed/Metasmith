"""Run one agent trajectory on one BixBench question and store everything it produced.

The agent is headless Claude Code on the host with no built-in tools. Its only tools
are served by sandbox_mcp.py and act inside an offline container that holds the
capsule data. A rung differs from another only in the text passed by --system-extra.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent

SYSTEM_PROMPT = """\
You are a bioinformatics data analyst. Answer one question about the dataset in /workspace by analysing the data.

Your tools act inside an offline Linux machine. It has Python 3 and R 4.3.3 with common bioinformatics packages and command-line tools. It has no internet access. Each bash call is a fresh shell, so keep state in files.

You have at most {max_steps} tool calls. Base the answer on your own analysis of the data.

End with your final answer inside <answer></answer> tags. Give one short value or phrase in the format the question asks for. Always give an answer.
"""


def unpack_capsule(zip_path: Path, dest: Path) -> None:
    """Mirror the reference harness: lift the Data folder's contents up, drop the original analysis."""
    shutil.unpack_archive(zip_path, dest)
    data = next((p for p in dest.rglob("*") if p.is_dir() and "Data" in p.name), None)
    if data is None:
        raise FileNotFoundError(f"no Data folder in {zip_path.name}")
    for item in data.iterdir():
        shutil.move(str(item), str(dest / item.name))
    shutil.rmtree(data)
    for p in [p for p in dest.rglob("*") if p.is_dir() and "Notebook" in p.name]:
        shutil.rmtree(p, ignore_errors=True)
    for p in dest.rglob("*.ipynb"):
        p.unlink()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question-id", required=True)
    ap.add_argument("--rung", required=True)
    ap.add_argument("--repeat", type=int, required=True)
    ap.add_argument("--data", type=Path, required=True, help="the BixBench dataset folder")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--system-extra", type=Path)
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--max-usd", type=float, default=5.0)
    ap.add_argument("--timeout-s", type=int, default=3600)
    a = ap.parse_args()

    rows = [json.loads(l) for l in (a.data / "BixBench.jsonl").open()]
    q = next(r for r in rows if r["question_id"] == a.question_id)

    run = (a.out / a.rung / a.question_id / f"r{a.repeat}").resolve()
    if (run / "result.json").exists():
        print(f"done already: {run}")
        return 0
    if run.exists():
        shutil.rmtree(run)
    work = run / "work"
    run.mkdir(parents=True)
    unpack_capsule(a.data / q["data_folder"], work)

    system = SYSTEM_PROMPT.format(max_steps=a.max_steps)
    if a.system_extra:
        system += "\n" + a.system_extra.read_text()
    (run / "system_prompt.txt").write_text(system)

    container = f"bxl-{uuid.uuid4().hex[:12]}"
    # Claude Code loads AGENTS.md and project memory from its working directory's
    # parents, so the agent process starts in a neutral directory outside any repo.
    cwd = Path("/var/tmp") / container
    cwd.mkdir()
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", container, "--network", "none",
         "--cpus", "4", "--memory", "16g", "--user", f"{os.getuid()}:{os.getgid()}",
         "-e", "HOME=/tmp", "-v", f"{work}:/workspace", "-w", "/workspace",
         a.image, "sleep", "infinity"],
        check=True, stdout=subprocess.DEVNULL)
    mcp = {"mcpServers": {"sandbox": {
        "command": sys.executable, "args": [str(HERE / "sandbox_mcp.py")],
        "env": {"SANDBOX_CONTAINER": container, "SANDBOX_LOG": str(run / "tool_calls.jsonl"),
                "SANDBOX_MAX_STEPS": str(a.max_steps)},
    }}}
    (run / "mcp.json").write_text(json.dumps(mcp))
    argv = ["claude", "--print", "--verbose", "--output-format", "stream-json",
            "--model", a.model, "--tools", "", "--strict-mcp-config",
            "--mcp-config", str(run / "mcp.json"), "--setting-sources", "",
            "--disable-slash-commands", "--no-session-persistence",
            "--permission-mode", "bypassPermissions", "--max-budget-usd", str(a.max_usd),
            "--system-prompt", system, q["question"]]
    start = time.time()
    try:
        with (run / "stream.jsonl").open("w") as fp:
            try:
                exit_code = subprocess.run(argv, cwd=cwd, stdout=fp, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, timeout=a.timeout_s).returncode
            except subprocess.TimeoutExpired:
                exit_code = 124
    finally:
        subprocess.run(["docker", "kill", container], capture_output=True)
        shutil.rmtree(cwd, ignore_errors=True)
    seconds = time.time() - start

    final, init = {}, {}
    for line in (run / "stream.jsonl").open():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev
        elif ev.get("type") == "system" and ev.get("subtype") == "init":
            init = ev
    text = final.get("result") or ""
    answers = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, re.DOTALL)
    calls = run / "tool_calls.jsonl"
    result = {
        "question_id": a.question_id, "short_id": q["short_id"], "rung": a.rung, "repeat": a.repeat,
        "answer": answers[-1] if answers else None, "final_text": text,
        "exit_code": exit_code, "is_error": final.get("is_error"), "subtype": final.get("subtype"),
        "seconds": round(seconds, 1), "num_turns": final.get("num_turns"),
        "tool_calls": sum(1 for _ in calls.open()) if calls.exists() else 0,
        "usage": final.get("usage"), "cost_usd": final.get("total_cost_usd"),
        "model_usage": final.get("modelUsage"), "model": init.get("model"),
        "tools_offered": init.get("tools"), "max_steps": a.max_steps,
    }
    (run / "result.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("question_id", "rung", "repeat", "answer", "seconds", "tool_calls", "cost_usd", "subtype")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

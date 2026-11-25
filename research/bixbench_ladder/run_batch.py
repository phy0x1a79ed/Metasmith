"""Run a set of capsules on the chosen rungs and repeats, interleaved, a few runs at a time.

    python3 run_batch.py --set pilot --data DATA --out OUT --image IMAGE

A finished run is skipped, so the same command resumes a batch. PROTOCOL.md defines a fault.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import split

HERE = Path(__file__).resolve().parent
AGENT_LIMITS = {"error_max_turns", "error_max_budget_usd"}
stop = threading.Event()
streak = 0
lock = threading.Lock()


def is_fault(result: dict) -> bool:
    if result["exit_code"] == 124 or result.get("subtype") in AGENT_LIMITS:
        return False
    return result.get("subtype") != "success" or bool(result.get("is_error"))


def one(job: tuple[str, str, int], a) -> str:
    global streak
    rung, qid, repeat = job
    run = a.out / rung / qid / f"r{repeat}"
    for attempt in range(1 + a.retries):
        if stop.is_set():
            return f"skipped {rung} {qid} r{repeat}"
        if not (run / "result.json").exists():
            subprocess.run([sys.executable, str(HERE / "run_one.py"), "--rung", rung, "--question-id", qid,
                            "--repeat", str(repeat), "--data", str(a.data), "--out", str(a.out),
                            "--image", a.image, "--model", a.model],
                           capture_output=True, text=True)
        result = json.loads((run / "result.json").read_text()) if (run / "result.json").exists() else None
        if result and not is_fault(result):
            with lock:
                streak = 0
            return f"ok {rung} {qid} r{repeat} {result['seconds']:.0f}s answer={result['answer']!r}"
        faults = a.out / "faults"
        faults.mkdir(exist_ok=True)
        (faults / f"{rung}_{qid}_r{repeat}_{attempt}.json").write_text(json.dumps(result))
        (run / "result.json").unlink(missing_ok=True)
        with lock:
            streak += 1
            if streak >= a.max_fault_streak:
                stop.set()
        time.sleep(60)
    return f"FAULT {rung} {qid} r{repeat}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True, choices=["pilot", "confirmatory", "all"])
    ap.add_argument("--rungs", nargs="+", default=["harness", "search", "planner"])
    ap.add_argument("--repeats", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--max-fault-streak", type=int, default=6)
    a = ap.parse_args()

    capsules = {"pilot": split.PILOT, "confirmatory": split.CONFIRMATORY, "all": list(split.FAMILY)}[a.set]
    questions = [r["question_id"] for r in map(json.loads, (a.data / "BixBench.jsonl").open())
                 if r["short_id"] in capsules]
    jobs = [(rung, q, k) for q in questions for rung in a.rungs for k in a.repeats]
    # A shuffled order spreads a provider-side change or an outage over all rungs.
    random.Random(split.SEED).shuffle(jobs)
    print(f"{len(jobs)} runs: {len(questions)} questions, rungs {a.rungs}, repeats {a.repeats}", flush=True)
    with ThreadPoolExecutor(a.jobs) as pool:
        for line in pool.map(lambda j: one(j, a), jobs):
            print(time.strftime("%H:%M:%S"), line, flush=True)
    if stop.is_set():
        sys.exit("stopped: too many faults in a row; see faults/")


if __name__ == "__main__":
    main()

"""Tabulate graded runs and test the three contrasts as PROTOCOL.md fixes them.

    python3 analyse.py --out OUT [--set pilot|confirmatory|all] [--grade correct|lenient]
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import split

RUNGS = ["harness", "search", "planner"]
CONTRASTS = [("search", "harness"), ("planner", "search"), ("planner", "harness")]
PLANNER_CALL = re.compile(r"\bbx\s+(plan|run)\b")


def load(out: Path, grade: str) -> list[dict]:
    rows = []
    for path in sorted(out.glob("*/*/r*/result.json")):
        r = json.loads(path.read_text())
        g = json.loads((path.parent / "grade.json").read_text())
        calls = path.parent / "tool_calls.jsonl"
        commands = [json.dumps(json.loads(l)["args"]) for l in calls.open()] if calls.exists() else []
        usage = r.get("usage") or {}
        selection = r.get("selection") or {}
        rows.append({
            "rung": r["rung"], "capsule": r["short_id"], "question": r["question_id"], "repeat": r["repeat"],
            "family": split.FAMILY[r["short_id"]], "mode": g["eval_mode"], "correct": bool(g[grade]),
            "answered": r["answer"] is not None, "seconds": r["seconds"], "tool_calls": r["tool_calls"],
            "cost": (r.get("cost_usd") or 0) + (selection.get("cost_usd") or 0),
            "tokens": sum(v for k, v in usage.items() if k.endswith("_tokens") and isinstance(v, int)),
            "cards": len(selection.get("selected") or []),
            "planned": sum(bool(PLANNER_CALL.search(c)) for c in commands),
        })
    return rows


def accuracy(rows: list[dict]) -> float:
    return mean(r["correct"] for r in rows) if rows else float("nan")


def table(title: str, rows: list[dict], key: str) -> None:
    print(f"\n{title}")
    values = sorted({r[key] for r in rows}, key=str)
    print(f"{'':16}" + "".join(f"{rung:>16}" for rung in RUNGS))
    for v in values:
        cells = []
        for rung in RUNGS:
            sub = [r for r in rows if r["rung"] == rung and r[key] == v]
            cells.append(f"{accuracy(sub):.3f} (n={len(sub)})" if sub else "-")
        print(f"{str(v):16}" + "".join(f"{c:>16}" for c in cells))


def contrasts(rows: list[dict], resamples: int) -> None:
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["capsule"]][r["rung"]].append(r["correct"])
    capsules = sorted(by)

    def diff(sample: list[str], a: str, b: str) -> float:
        return (mean(x for c in sample for x in by[c][a]) - mean(x for c in sample for x in by[c][b]))

    rng = random.Random(split.SEED)
    draws = [[rng.choice(capsules) for _ in capsules] for _ in range(resamples)]
    found = []
    for a, b in CONTRASTS:
        d = sorted(diff(s, a, b) for s in draws)
        p = min(1.0, 2 * min(mean(x <= 0 for x in d), mean(x >= 0 for x in d)))
        found.append([f"{a} - {b}", diff(capsules, a, b), d[int(0.025 * resamples)], d[int(0.975 * resamples) - 1], p])
    # Holm: the k-th smallest p-value is multiplied by (m - k), and adjusted values never decrease.
    running = 0.0
    for k, row in enumerate(sorted(found, key=lambda f: f[4])):
        running = max(running, min(1.0, (len(found) - k) * row[4]))
        row.append(running)
    print(f"\nContrasts on {len(capsules)} capsules, {resamples} capsule resamples")
    for name, observed, low, high, p, holm in found:
        print(f"{name:20} {observed:+.3f}  95% [{low:+.3f}, {high:+.3f}]  p={p:.4f}  Holm p={holm:.4f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--set", default="all", choices=["pilot", "confirmatory", "all"])
    ap.add_argument("--grade", default="correct", choices=["correct", "lenient"])
    ap.add_argument("--resamples", type=int, default=10000)
    a = ap.parse_args()
    keep = {"pilot": split.PILOT, "confirmatory": split.CONFIRMATORY, "all": list(split.FAMILY)}[a.set]
    rows = [r for r in load(a.out, a.grade) if r["capsule"] in keep]

    print(f"{'rung':10}{'runs':>6}{'accuracy':>10}{'no answer':>11}{'med s':>8}{'mean s':>8}{'med calls':>11}"
          f"{'mean USD':>10}{'mean tokens':>13}{'cards':>7}{'uptake':>8}")
    for rung in RUNGS:
        sub = [r for r in rows if r["rung"] == rung]
        if not sub:
            continue
        print(f"{rung:10}{len(sub):>6}{accuracy(sub):>10.3f}{mean(not r['answered'] for r in sub):>11.3f}"
              f"{median(r['seconds'] for r in sub):>8.0f}{mean(r['seconds'] for r in sub):>8.0f}"
              f"{median(r['tool_calls'] for r in sub):>11.0f}{mean(r['cost'] for r in sub):>10.3f}"
              f"{mean(r['tokens'] for r in sub):>13.0f}{mean(r['cards'] for r in sub):>7.1f}"
              f"{mean(r['planned'] > 0 for r in sub):>8.3f}")
    table("Accuracy by family", rows, "family")
    table("Accuracy by grading mode", rows, "mode")
    planner = [dict(r, used="planner used" if r["planned"] else "planner unused") for r in rows if r["rung"] == "planner"]
    for used in ("planner used", "planner unused"):
        sub = [r for r in planner if r["used"] == used]
        print(f"{used}: accuracy {accuracy(sub):.3f} (n={len(sub)})")

    grades = defaultdict(set)
    for r in rows:
        grades[r["rung"], r["question"]].add(r["correct"])
    for rung in RUNGS:
        same = [len(v) == 1 for (g, _), v in grades.items() if g == rung]
        if same:
            print(f"repeat agreement {rung}: {mean(same):.3f}")
    if all(any(r["rung"] == rung for r in rows) for rung in RUNGS):
        contrasts(rows, a.resamples)


if __name__ == "__main__":
    main()

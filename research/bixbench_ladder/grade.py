"""Grade stored runs with BixBench's open-answer rules and write grade.json beside each result.json.

The rules follow bixbench/graders.py at the pinned commit, with one repair: a range
answer that is out of range or not a number is incorrect, where the reference crashes.
`correct` is the reference rule. `lenient` also lets the judge accept a string answer
that failed the exact match.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from llm import ask

# Copied verbatim from bixbench/prompts.py.
OPEN_ENDED_GRADING_PROMPT = """You are given a question, target answer and a predicted answer. Your task is to compare the target answer with the predicted and assess if the predicted answer is correct, incorrect or it refused to answer.
Question: {question}
Target Answer: {target}
Predicted Answer: {predicted}

Important: You must only output one from `correct`, `incorrect` or `refused` between <grade> tags.
Example Output: <grade> correct </grade>
"""

NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def judge(model: str, question: str, target: str, predicted: str) -> bool:
    prompt = OPEN_ENDED_GRADING_PROMPT.format(question=question, target=target, predicted=predicted)
    out = ask(model, "You are a careful grader.", prompt)["text"]
    m = re.search(r"<grade>\s*(.*?)\s*</grade>", out, re.DOTALL)
    return bool(m) and m[1].strip().lower() == "correct"


def in_range(target: str, predicted: str) -> bool:
    lower, upper = ast.literal_eval(target)
    m = NUMBER.search(predicted.replace(",", ""))
    return bool(m) and lower <= float(m[0]) <= upper


def grade(q: dict, predicted: str | None, judge_model: str) -> dict:
    if not predicted:
        return {"correct": False, "lenient": False, "judged": False}
    mode, target = q["eval_mode"], str(q["ideal"])
    judged = False
    if mode == "range_verifier":
        correct = lenient = in_range(target, predicted)
    elif mode == "str_verifier":
        clean = lambda s: re.sub(r"[^a-zA-Z0-9]", "", s).lower()
        correct = lenient = clean(predicted) == clean(target)
        if not correct:
            lenient, judged = judge(judge_model, q["question"], target, predicted), True
    elif mode == "llm_verifier":
        correct = lenient = judge(judge_model, q["question"], target, predicted)
        judged = True
    else:
        raise ValueError(mode)
    return {"correct": correct, "lenient": lenient, "judged": judged}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--judge-model", default="claude-sonnet-5-5")
    a = ap.parse_args()
    questions = {r["question_id"]: r for r in map(json.loads, (a.data / "BixBench.jsonl").open())}

    def one(path: Path) -> str:
        r = json.loads(path.read_text())
        q = questions[r["question_id"]]
        g = grade(q, r["answer"], a.judge_model)
        g.update(eval_mode=q["eval_mode"], judge_model=a.judge_model)
        (path.parent / "grade.json").write_text(json.dumps(g, indent=1))
        return f"{r['rung']} {r['question_id']} r{r['repeat']} {q['eval_mode']} correct={g['correct']} lenient={g['lenient']}"

    todo = [p for p in sorted(a.out.rglob("result.json")) if not (p.parent / "grade.json").exists()]
    with ThreadPoolExecutor(4) as pool:
        for line in pool.map(one, todo):
            print(line)


if __name__ == "__main__":
    main()

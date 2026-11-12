"""Journal test 2, mocked: the binning checker is the plan's own CheckM step. check_l3.py LOG RUN"""
import json, os, sys

log, run = sys.argv[1:3]
rows = [json.loads(l) for l in open(log)]
sent = [r["env"] for r in rows if r["dir"] == "in"]
offers = [e for e in sent if e["selector"] == "offer"]
contract = lambda e, i=0: e["args"]["set"]["steps"][i]["props"].get("contract")
binning = next(e for e in offers if contract(e) == "binning")
checkm = [e for e in offers if contract(e) == "checkm"]
assert len(checkm) == 2, "expected the checker offer and the plan's own checkm offer, saw %d" % len(checkm)
checker, plan = checkm
assert [s["op"] for s in checker["args"]["set"]["steps"]] == ["task", "place"]
assert checker["args"]["set"]["steps"][1]["spec"]["path"].endswith(".baitan-check")
a, b = checker["args"]["set"]["steps"][0], plan["args"]["set"]["steps"][0]
assert a["props"] == b["props"] and a["inputs"] == b["inputs"] and len(a["inputs"]) == 2, "checker and plan step must share a declared set"

sets = binning["args"]["set"]
assert [x["name"] for x in sets["axes"]] == ["time", "completeness", "contamination"]

ran = [r["env"]["args"] for r in rows if r["dir"] == "run" and r["env"]["selector"] == "ran"]
hits = [r["env"]["args"] for r in rows if r["dir"] == "run" and r["env"]["selector"] == "hit"]
runs = [x["props"]["contract"] for x in ran]
assert runs.count("checkm") == 1 and runs.count("binning") == 1, runs
assert [h["contract"] for h in hits] == ["checkm"], hits

promise = next(r["env"]["args"]["promise"] for r in rows if r["dir"] == "out" and r["env"].get("replyTo") == binning["id"])
reviews = [e["args"] for e in sent if e["selector"] == "review"]
assert len(reviews) == 1 and reviews[0]["promise"] == promise, reviews
assert reviews[0]["scores"] == {"completeness": 80.0, "contamination": 3.0}, reviews[0]
assert open(os.path.join(run, "out", "checkm.tsv")).read().startswith("Bin\tCompleteness")
print("layer 3 ok: one checkm run, shared by checker and plan step; one review of the binning promise:", reviews[0]["scores"])

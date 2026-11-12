"""Two workflows share one step and one declared reference: check_l2.py LOG RUN"""
import json, os, sys

log, run = sys.argv[1:3]
rows = [json.loads(l) for l in open(log)]
offers = [r["env"]["args"]["set"] for r in rows if r["dir"] == "in" and r["env"]["selector"] == "offer"]
shared = [s for s in offers if s["steps"][0]["props"].get("contract") == "shared"]
assert len(shared) == 2, "expected one shared offer per workflow, saw %d" % len(shared)
a, b = (s["steps"][0] for s in shared)
assert a["props"] == b["props"] and a["inputs"] == b["inputs"] and a["spec"] == b["spec"], "shared step declared differently"
assert "hash" not in a["props"], "declared step must not carry the task hash"
assert len(a["inputs"]) == 2

ran = [r["env"]["args"] for r in rows if r["dir"] == "run" and r["env"]["selector"] == "ran"]
hits = [r["env"]["args"] for r in rows if r["dir"] == "run" and r["env"]["selector"] == "hit"]
assert [r["props"]["contract"] for r in ran].count("shared") == 1, "shared step must run once: %s" % ran
assert len(hits) == 1 and hits[0]["contract"] == "shared", hits
assert hits[0]["key"] == [r["key"] for r in ran if r["props"]["contract"] == "shared"][0], "the repeat offer must carry the first offer's key"

extra = [s for s in offers if s["steps"][0]["props"].get("contract") == "extra"]
assert len(extra) == 1 and extra[0]["steps"][0]["inputs"] == [hits[0]["stored"]], "extra must read the stored shared id"
assert open(os.path.join(run, "b", "out", "extra.txt")).read() == "sample\ndb-v1\n"
assert open(os.path.join(run, "a", "out", "shared.txt")).read() == open(os.path.join(run, "b", "out", "shared.txt")).read()
print("layer 2 ok: same declared set and offer key across workflows, shared step ran once, repeat settled from the stored id")

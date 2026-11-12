"""Assertions over the stub market's log and the pipeline's work dirs: check.py ok|kill LOG RUN_DIR"""
import json, os, sys

mode, log, run = sys.argv[1:4]
rows = [json.loads(l) for l in open(log)]
sent = [r for r in rows if r["dir"] == "in"]
offers = [r for r in sent if r["env"]["selector"] == "offer"]
settled = [i for i, r in enumerate(rows) if r["dir"] == "out" and r["env"]["selector"] == "event" and "settled" in r["env"]["args"]["phase"]]
cancels = [r for r in sent if r["env"]["selector"] == "cancel"]
produce = [r for r in offers if r["env"]["args"]["set"]["steps"][0]["props"].get("contract") == "nextflow-task"
           and len(r["env"]["args"]["set"]["steps"]) == 1]
assert len(produce) == 3, "expected 3 producer offers, saw %d" % len(produce)

if mode == "kill":
    assert len(cancels) >= 2, "expected cancels for the running producers, saw %d" % len(cancels)
    print("kill ok:", len(cancels), "cancels")
    sys.exit(0)

first_settle = settled[0]
posted_before = [i for i, r in enumerate(rows) if r["dir"] == "in" and r["env"]["selector"] == "offer"][:3]
assert all(i < first_settle for i in posted_before), "producer offers were not all outstanding before the first settle"

consumer = [r for r in offers if len(r["env"]["args"]["set"]["steps"]) == 2][0]["env"]["args"]["set"]
assert [s["op"] for s in consumer["steps"]] == ["task", "place"]
assert len(consumer["steps"][0]["inputs"]) == 3

work = [os.path.join(run, "work", a, b) for a in os.listdir(os.path.join(run, "work")) if len(a) == 2
        for b in os.listdir(os.path.join(run, "work", a))]
stubs = 0
for w in work:
    manifest = os.path.join(w, ".baitan-manifest.json")
    for f in os.listdir(w):
        if f.startswith("p") and f.endswith(".txt"):
            body = open(os.path.join(w, f)).read()
            assert "payload" not in body, "real bytes in producer work dir " + w
            assert set(json.loads(body)) == {"id", "path", "provider"}
            assert os.path.exists(manifest)
            stubs += 1
assert stubs == 3, "expected 3 producer stubs, saw %d" % stubs

merged = open(os.path.join(run, "out", "merged.txt")).read()
assert all("producer-%d-payload" % i in merged for i in (1, 2, 3)), "published file lacks real content: " + merged

disposed = [r["env"]["args"]["ids"] for r in sent if r["env"]["selector"] == "dispose"]
assert len(disposed) == 1 and len(disposed[0]) == 3, "expected one dispose of the 3 intermediates: %s" % disposed
out_ids = set()
for r in rows:
    a = r["env"]["args"]
    if r["dir"] == "out" and r["env"]["selector"] == "event" and "settled" in a["phase"]:
        out_ids |= set(a["phase"]["settled"]["listing"])
final_id = [i for i in out_ids if i not in disposed[0]]
assert len(final_id) == 1, "the final target must not be disposed"
print("ok: 3 concurrent offers, stubs only, published content real, 3 intermediates disposed")

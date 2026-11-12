"""A stub baitan market for the nf-baitan test: JSON lines on stdio, jobs run locally per JOBS.md.

Usage: stub_market.py LOG ROOT
Every envelope in and out is appended to LOG as {t, dir, env}. Each `task` step runs in ROOT/<promise>/.
"""
import glob, hashlib, json, os, shutil, signal, subprocess, sys, threading, time, uuid

LOG, ROOT = sys.argv[1], sys.argv[2]
PROVIDER = "stub-1"
WINDOW = 1.5  # seconds a promise stays open, so concurrent offers are visible in the log
lock = threading.Lock()
STATE = os.path.join(ROOT, "state.json")
store = {}       # instance id -> directory holding it
inflight = []    # offered task steps, in arrival order: {"pairs", "event"}
done = []        # settled task steps: {"pairs", "slots", "listing", "sizes"}
promises = {}    # promise id -> {"phase": ..., "proc": Popen|None, "cancelled": bool}


def h(obj):
    return hashlib.sha256(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:32]


def offer_key(s):
    return h([s["op"], dict(sorted(s.get("props", {}).items())), s.get("inputs", []), s.get("spec"), s.get("to")])


def slot_id(key, slot):
    return h([key, slot])


def load_state():
    if os.path.exists(STATE):
        saved = json.load(open(STATE))
        store.update(saved["store"])
        done.extend(saved["done"])


def save_state():
    json.dump({"store": store, "done": done}, open(STATE, "w"))


def note(selector, args):
    with lock:
        with open(LOG, "a") as f:
            f.write(json.dumps({"t": time.time(), "dir": "run", "env": {"selector": selector, "args": args}}) + "\n")


def pairs(step):
    return {"%s=%s" % kv for kv in step.get("props", {}).items()} | {"op=" + step["op"]} | {"input=" + i for i in step.get("inputs", [])}


def find_hit(step):
    want = pairs(step)
    return next((d for d in done if want <= set(d["pairs"]) and all(i in store for i in d["listing"])), None)


def emit(env):
    with lock:
        with open(LOG, "a") as f:
            f.write(json.dumps({"t": time.time(), "dir": "out", "env": env}) + "\n")
        sys.stdout.write(json.dumps(env, separators=(",", ":")) + "\n")
        sys.stdout.flush()


def envelope(to, selector, args, reply_to=None):
    e = {"v": 1, "id": str(uuid.uuid4()), "from": "market", "to": to, "selector": selector, "args": args}
    if reply_to:
        e["replyTo"] = reply_to
    return e


def set_phase(caller, promise, phase):
    promises[promise]["phase"] = phase
    emit(envelope(caller, "event", {"promise": promise, "phase": phase}))


def fail(caller, promise, name, message):
    set_phase(caller, promise, {"failed": {"name": name, "message": message}})


def run_set(caller, promise, offer_set):
    try:
        run_steps(caller, promise, offer_set)
    finally:
        for e in promises[promise]["entries"]:
            e["event"].set()


def run_steps(caller, promise, offer_set):
    p = promises[promise]
    entries = iter(p["entries"])
    time.sleep(WINDOW)
    if p["cancelled"]:
        return
    set_phase(caller, promise, {"awarded": {"provider": PROVIDER}})
    set_phase(caller, promise, {"started": {"provider": PROVIDER}})
    work = os.path.join(ROOT, promise)
    os.makedirs(work)
    slots, facts, sizes, listing = {}, [], {}, {}
    alias = {}
    for step in offer_set["steps"]:
        if step["op"] == "task":
            spec = step["spec"]
            out = slot_id(offer_key(step), "out")
            mine = next(entries)
            hit = find_hit(step)
            if not hit:
                want = pairs(step)
                earlier = inflight[:inflight.index(mine)]
                prior = next((e for e in earlier if want <= e["pairs"] and not e["event"].is_set()), None)
                if prior:
                    prior["event"].wait()
                    hit = find_hit(step)
            if hit:
                stored = hit["slots"]["out"]
                alias[out] = stored
                slots[stored] = store[stored]
                listing[stored], sizes[stored] = hit["listing"][stored], hit["sizes"][stored]
                facts.append({"s": {"id": stored}, "p": {"rel": "at"}, "o": {"provider": PROVIDER}})
                note("hit", {"promise": promise, "key": offer_key(step), "stored": stored, "contract": step["props"].get("contract")})
                continue
            for name, ref in spec["stage"].items():
                dest = os.path.join(work, name)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                src = ref["src"] if "src" in ref else os.path.join(store[ref["id"]], ref.get("path", ""))
                (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, dest)
            with open(os.path.join(work, "run.sh"), "w") as f:
                f.write(spec["script"])
            note("ran", {"promise": promise, "key": offer_key(step), "props": step.get("props", {}), "inputs": step.get("inputs", [])})
            p["proc"] = subprocess.Popen(["bash", "run.sh"], cwd=work, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            _, err = p["proc"].communicate()
            if p["cancelled"]:
                return
            if p["proc"].returncode != 0:
                return fail(caller, promise, "BrokenPromise", err.decode()[-200:] or "exit %d" % p["proc"].returncode)
            files = sorted({os.path.relpath(m, work) for pat in spec["outputs"] for m in glob.glob(os.path.join(work, pat), recursive=True)
                            if os.path.isfile(m)} | {os.path.relpath(os.path.join(d, f), work) for pat in spec["outputs"]
                            for m in glob.glob(os.path.join(work, pat), recursive=True) if os.path.isdir(m) for d, _, fs in os.walk(m) for f in fs})
            store[out] = work
            slots[out] = work
            facts.append({"s": {"id": out}, "p": {"rel": "at"}, "o": {"provider": PROVIDER}})
            sizes[out] = sum(os.path.getsize(os.path.join(work, f)) for f in files)
            listing[out] = files
            with lock:
                done.append({"pairs": sorted(pairs(step)), "slots": {"out": out}, "listing": {out: files}, "sizes": {out: sizes[out]}})
                save_state()
            mine["event"].set()
        elif step["op"] == "place":
            for sid in (alias.get(i, i) for i in step["inputs"]):
                if sid not in slots:
                    return fail(caller, promise, "BadArgs", "place input %s is not a slot of this set" % sid)
                for rel in listing[sid]:
                    dest = os.path.join(step["spec"]["path"], rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy(os.path.join(slots[sid], rel), dest)
    set_phase(caller, promise, {"settled": {"provider": PROVIDER, "facts": facts, "sizes": sizes, "listing": listing}})


def handle(env):
    sel, args, caller = env["selector"], env["args"], env["from"]
    reply = lambda s, a: emit(envelope(caller, s, a, env["id"]))
    if sel == "offer":
        promise = str(uuid.uuid4())
        entries = [{"pairs": pairs(s), "event": threading.Event()} for s in args["set"]["steps"] if s["op"] == "task"]
        with lock:
            inflight.extend(entries)
        promises[promise] = {"phase": "open", "proc": None, "cancelled": False, "entries": entries}
        reply("return", {"promise": promise})
        threading.Thread(target=run_set, args=(caller, promise, args["set"]), daemon=True).start()
    elif sel in ("watch", "review"):
        reply("return", None)
    elif sel == "status":
        reply("return", {"promise": args["promise"], "phase": promises[args["promise"]]["phase"]})
    elif sel == "cancel":
        p = promises.get(args["promise"])
        if p is None:
            return reply("raise", {"name": "UnknownPromise", "message": args["promise"]})
        p["cancelled"] = True
        if p["proc"] and p["proc"].poll() is None:
            p["proc"].kill()
        reply("return", None)
        fail(caller, args["promise"], "Cancelled", "cancelled by caller")
    elif sel == "dispose":
        with lock:
            for i in args["ids"]:
                if i in store:
                    shutil.rmtree(store.pop(i), ignore_errors=True)
            done[:] = [d for d in done if all(i in store for i in d["listing"])]
            save_state()
        reply("return", None)
    else:
        reply("doesNotUnderstand", {"selector": sel})


load_state()
for line in sys.stdin:
    env = json.loads(line)
    with lock:
        with open(LOG, "a") as f:
            f.write(json.dumps({"t": time.time(), "dir": "in", "env": env}) + "\n")
    handle(env)

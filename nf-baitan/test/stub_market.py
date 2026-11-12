"""A stub baitan market for the nf-baitan test: JSON lines on stdio, jobs run locally per JOBS.md.

Usage: stub_market.py LOG ROOT
Every envelope in and out is appended to LOG as {t, dir, env}. Each `task` step runs in ROOT/<promise>/.
"""
import glob, hashlib, json, os, shutil, signal, subprocess, sys, threading, time, uuid

LOG, ROOT = sys.argv[1], sys.argv[2]
PROVIDER = "stub-1"
WINDOW = 1.5  # seconds a promise stays open, so concurrent offers are visible in the log
lock = threading.Lock()
store = {}       # instance id -> directory holding it
promises = {}    # promise id -> {"phase": ..., "proc": Popen|None, "cancelled": bool}


def h(obj):
    return hashlib.sha256(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:32]


def offer_key(s):
    return h([s["op"], dict(sorted(s.get("props", {}).items())), s.get("inputs", []), s.get("spec"), s.get("to")])


def slot_id(key, slot):
    return h([key, slot])


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
    p = promises[promise]
    time.sleep(WINDOW)
    if p["cancelled"]:
        return
    set_phase(caller, promise, {"awarded": {"provider": PROVIDER}})
    set_phase(caller, promise, {"started": {"provider": PROVIDER}})
    work = os.path.join(ROOT, promise)
    os.makedirs(work)
    slots, facts, sizes, listing = {}, [], {}, {}
    for step in offer_set["steps"]:
        if step["op"] == "task":
            spec = step["spec"]
            for name, ref in spec["stage"].items():
                dest = os.path.join(work, name)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                src = ref["src"] if "src" in ref else os.path.join(store[ref["id"]], ref.get("path", ""))
                (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, dest)
            with open(os.path.join(work, "run.sh"), "w") as f:
                f.write(spec["script"])
            p["proc"] = subprocess.Popen(["bash", "run.sh"], cwd=work, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            _, err = p["proc"].communicate()
            if p["cancelled"]:
                return
            if p["proc"].returncode != 0:
                return fail(caller, promise, "BrokenPromise", err.decode()[-200:] or "exit %d" % p["proc"].returncode)
            files = sorted({os.path.relpath(m, work) for pat in spec["outputs"] for m in glob.glob(os.path.join(work, pat), recursive=True)
                            if os.path.isfile(m)} | {os.path.relpath(os.path.join(d, f), work) for pat in spec["outputs"]
                            for m in glob.glob(os.path.join(work, pat), recursive=True) if os.path.isdir(m) for d, _, fs in os.walk(m) for f in fs})
            out = slot_id(offer_key(step), "out")
            store[out] = work
            slots[out] = work
            facts.append({"s": {"id": out}, "p": {"rel": "at"}, "o": {"provider": PROVIDER}})
            sizes[out] = sum(os.path.getsize(os.path.join(work, f)) for f in files)
            listing[out] = files
        elif step["op"] == "place":
            for sid in step["inputs"]:
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
        promises[promise] = {"phase": "open", "proc": None, "cancelled": False}
        reply("return", {"promise": promise})
        threading.Thread(target=run_set, args=(caller, promise, args["set"]), daemon=True).start()
    elif sel == "watch":
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
        for i in args["ids"]:
            if i in store:
                shutil.rmtree(store.pop(i), ignore_errors=True)
        reply("return", None)
    else:
        reply("doesNotUnderstand", {"selector": sel})


for line in sys.stdin:
    env = json.loads(line)
    with lock:
        with open(LOG, "a") as f:
            f.write(json.dumps({"t": time.time(), "dir": "in", "env": env}) + "\n")
    handle(env)

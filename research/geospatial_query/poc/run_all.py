"""Full dossier run: every registered adapter x every AOI."""
import os, sys, json, time, importlib, concurrent.futures as cf
sys.path.append(os.getcwd())
import pipeline as P

LANES = ["adapters_health_env", "adapters_census", "adapters_physical",
         "adapters_infrastructure", "adapters_s2signature", "adapters_embeddings"]
ADAPTERS = list(P.ADAPTERS)
loaded = {"core(pipeline.py)": len(P.ADAPTERS)}
for m in LANES:
    try:
        mod = importlib.import_module(m)
        extra = list(getattr(mod, "ADAPTERS", []))
        ADAPTERS += extra
        loaded[m] = len(extra)
    except Exception as e:
        loaded[m] = f"SKIPPED {type(e).__name__}: {str(e)[:80]}"

aois = P.load_aois(os.environ["AOI_PATH"])
seen, dedup = set(), []
for spec in ADAPTERS:                      # (slot, source, family, licence, auth, fn)
    key = (spec[0], spec[1])
    if key in seen:
        continue
    seen.add(key); dedup.append(spec)
ADAPTERS = dedup

print(json.dumps(loaded), flush=True)
print(f"{len(aois)} AOIs x {len(ADAPTERS)} adapters = {len(aois)*len(ADAPTERS)} fetches", flush=True)

tasks = [(a, s) for a in aois for s in ADAPTERS]
t0, out = time.time(), []
with cf.ThreadPoolExecutor(int(os.environ.get("NWORK", 8))) as ex:
    futs = {ex.submit(P.run_one, a, s): (a["aoi_id"], s[1]) for a, s in tasks}
    for n, fu in enumerate(cf.as_completed(futs), 1):
        try:
            out.append(fu.result())
        except Exception as e:
            aid, src = futs[fu]
            out.append({"aoi_id": aid, "source": src, "slot": "?", "family": "?", "licence": "?",
                        "fill_type": "observed", "status": "unavailable",
                        "reason": f"harness: {type(e).__name__}: {str(e)[:120]}",
                        "features": {}, "n_features": 0, "wall_s": None})
        if n % 50 == 0:
            print(f"  {n}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
json.dump(out, open("poc_records.json", "w"))
print(f"DONE {len(out)} records in {time.time()-t0:.0f}s", flush=True)

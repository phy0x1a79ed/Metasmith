"""One source over every AOI, one table out: a row per AOI x feature found, a status row per AOI without."""
import argparse, json, os, re, time, concurrent.futures as cf
import pandas as pd
from . import pipeline as P
from .registry import SOURCES, UNITS, specs

COLUMNS = ["aoi", "source", "observation_type", "time", "feature", "family", "value",
           "value_num", "SI_unit", "licence", "native_res_m", "status", "reason"]


# Shared public APIs throttle and stall when every source runs at once; these failures are retried.
TRANSIENT = re.compile(r"429|Too Many Requests|[Tt]imeout|timed out|HTTP 5\d\d|50[234]")
BACKOFF_S = (15, 60, 180)


def rows(rec, src):
    base = {"aoi": rec["aoi_id"], "source": rec["source"], "family": src["family"],
            "observation_type": src["observation_type"], "time": rec.get("obs_date"),
            "licence": rec["licence"], "native_res_m": rec.get("res_m"),
            "status": rec["status"], "reason": rec["reason"]}
    if rec["status"] != "found":
        return [base]
    return [{**base, "feature": k, "value": v, "SI_unit": UNITS.get(k, "")}
            for k, v in rec["features"].items()]


def fetch(aois, source, nwork):
    todo = [(a, s) for s in specs() if s[1] == source for a in aois]
    if not todo:
        raise SystemExit(f"unknown source: {source}")
    with cf.ThreadPoolExecutor(nwork) as ex:
        recs = list(ex.map(lambda t: P.run_one(*t), todo))
    for wait in BACKOFF_S:
        retry = [i for i, r in enumerate(recs)
                 if r["status"] == "unavailable" and TRANSIENT.search(r["reason"] or "")]
        if not retry:
            break
        time.sleep(wait)
        for i in retry:  # serially, so a throttled API sees one request at a time
            recs[i] = P.run_one(*todo[i])
    out = [row for r in recs for row in rows(r, SOURCES[source])]
    t = pd.DataFrame(out).reindex(columns=COLUMNS)
    t["value_num"] = pd.to_numeric(t["value"], errors="coerce")
    # identifiers are text: parsing 090805 as 90805 would corrupt the join key
    t.loc[t.feature.astype(str).str.contains(r"(?:_id|uid|_code)$"), "value_num"] = float("nan")
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aois", required=True)
    ap.add_argument("--source", required=True, help="JSON file or string: {\"adapter\": name}")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.load(open(a.source)) if os.path.exists(a.source) else json.loads(a.source)
    t = fetch(P.load_aois(a.aois), spec["adapter"], int(os.environ.get("NWORK", 4)))
    t.to_csv(a.out, sep="\t", index=False)
    print(f"{spec['adapter']}: {t.status.value_counts().to_dict()} -> {a.out}")


if __name__ == "__main__":
    main()

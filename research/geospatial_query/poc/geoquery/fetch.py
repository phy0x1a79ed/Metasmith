"""One source over every AOI, one table out: a row per AOI x feature found, a status row per AOI without."""
import argparse, json, os, concurrent.futures as cf
import pandas as pd
from . import pipeline as P
from .registry import SOURCES, UNITS, specs

COLUMNS = ["aoi", "source", "observation_type", "time", "feature", "family", "value",
           "value_num", "SI_unit", "licence", "native_res_m", "status", "reason"]


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
    out = []
    with cf.ThreadPoolExecutor(nwork) as ex:
        for rec in ex.map(lambda t: P.run_one(*t), todo):
            out += rows(rec, SOURCES[source])
    t = pd.DataFrame(out).reindex(columns=COLUMNS)
    t["value_num"] = pd.to_numeric(t["value"], errors="coerce")
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

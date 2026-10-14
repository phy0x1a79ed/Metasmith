"""Q3: one STAC search over a date range, binned into periods client-side, versus one search per period.

A period spec is {start, end, every, months}: every in {"month", "year", "<N>d"}; months restricts to a
recurring season (e.g. [7] = every July). The best item per period is the lowest eo:cloud_cover.
"""
import datetime as dtm
import json

import common as c

SPEC = {"start": "2023-01-01", "end": "2024-12-31", "collection": "sentinel-2-l2a", "limit": 1000}
PERIODS = {
    "monthly": {"every": "month"},
    "every July": {"every": "year", "months": [7]},
    "16-day": {"every": "16d"},
}


def parse_dt(s):
    return dtm.datetime.fromisoformat(s.replace("Z", "+00:00"))


def bin_key(when, period, start):
    if "months" in period and when.month not in period["months"]:
        return None
    ev = period["every"]
    if ev == "month":
        return f"{when.year}-{when.month:02d}"
    if ev == "year":
        return f"{when.year}-{'+'.join(f'{m:02d}' for m in period['months'])}" if "months" in period else str(when.year)
    if ev.endswith("d"):
        n = int(ev[:-1])
        days = (when.date() - dtm.date.fromisoformat(start)).days
        k = days // n
        a = dtm.date.fromisoformat(start) + dtm.timedelta(days=k * n)
        return a.isoformat()
    raise ValueError(ev)


def best_per_period(feats, period, start):
    best = {}
    for f in feats:
        key = bin_key(parse_dt(f["properties"]["datetime"]), period, start)
        if key is None:
            continue
        cc = f["properties"].get("eo:cloud_cover", 101)
        if key not in best or cc < best[key][0]:
            best[key] = (cc, f["id"], f["properties"]["datetime"][:10])
    return dict(sorted(best.items()))


def period_windows(period, start, end):
    """Enumerate the date windows a fan-out would query, one request each."""
    s, e = dtm.date.fromisoformat(start), dtm.date.fromisoformat(end)
    out = []
    ev = period["every"]
    if ev == "month":
        y, m = s.year, s.month
        while dtm.date(y, m, 1) <= e:
            a = dtm.date(y, m, 1)
            b = dtm.date(y + (m == 12), 1 if m == 12 else m + 1, 1) - dtm.timedelta(days=1)
            if "months" not in period or m in period["months"]:
                out.append((f"{y}-{m:02d}", a, min(b, e)))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    elif ev == "year":
        for y in range(s.year, e.year + 1):
            for m in period.get("months", [None]):
                if m is None:
                    out.append((str(y), dtm.date(y, 1, 1), dtm.date(y, 12, 31)))
                else:
                    nm = dtm.date(y + (m == 12), 1 if m == 12 else m + 1, 1)
                    out.append((f"{y}-{m:02d}", dtm.date(y, m, 1), nm - dtm.timedelta(days=1)))
    else:
        n = int(ev[:-1])
        a = s
        while a <= e:
            out.append((a.isoformat(), a, min(a + dtm.timedelta(days=n - 1), e)))
            a += dtm.timedelta(days=n)
    return out


def single_search(base, bbox):
    body = {"collections": [SPEC["collection"]], "bbox": bbox, "datetime": c.dt(SPEC["start"], SPEC["end"]),
            "limit": 200 if base == c.ES else SPEC["limit"],  # Earth Search answers 502 above ~200 items per page
            "fields": {"include": ["id", "properties.datetime", "properties.eo:cloud_cover"]}}
    return c.search_all(base, body)


def fanout_best(base, bbox, windows):
    """One request per period window, server-side sort on cloud cover (PC) or client pick (ES)."""
    res, n = {}, 0
    for key, a, b in windows:
        body = {"collections": [SPEC["collection"]], "bbox": bbox, "datetime": c.dt(a.isoformat(), b.isoformat()),
                "limit": 100, "fields": {"include": ["id", "properties.datetime", "properties.eo:cloud_cover"]}}
        feats, k, st = c.search_all(base, body)
        n += k
        if feats:
            f = min(feats, key=lambda f: f["properties"].get("eo:cloud_cover", 101))
            res[key] = (f["properties"].get("eo:cloud_cover"), f["id"], f["properties"]["datetime"][:10])
    return res, n


def run(verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    summary = {"spec": SPEC, "periods": PERIODS, "catalogs": {}}
    log("SPEC", json.dumps(SPEC), "PERIODS", json.dumps(PERIODS))
    hits = {}
    for cat, base in c.CATALOGS.items():
        cs = {"aois": {}, "single_requests": 0, "fanout_requests_theory": {}, "items": {}}
        # control box: expect zero items
        ctrl, n, st = single_search(base, c.CONTROL_BBOX)
        cs["control_items"] = len(ctrl)
        log(f"\n===== {cat} control (mid-Pacific) items={len(ctrl)} http={st}")
        for a in c.load_aois():
            feats, n, st = single_search(base, a["bbox"])
            cs["single_requests"] += n
            cs["items"][a["id"]] = len(feats)
            uniq = len({f["properties"]["datetime"] for f in feats})
            row = {"items": len(feats), "pages": n, "unique_datetimes": uniq}
            log(f"\n--- {cat} {a['id']}: {len(feats)} items ({uniq} distinct datetimes) in {n} request(s) (http {st})")
            for pname, period in PERIODS.items():
                best = best_per_period(feats, period, SPEC["start"])
                wins = period_windows(period, SPEC["start"], SPEC["end"])
                row[pname] = {"periods_total": len(wins), "periods_with_item": len(best),
                              "median_best_cloud": sorted(v[0] for v in best.values())[len(best) // 2] if best else None}
                cs["fanout_requests_theory"][pname] = cs["fanout_requests_theory"].get(pname, 0) + len(wins)
                if pname != "16-day":  # 16-day table is 46 rows per AOI; shown for the first AOI only
                    log(f"  [{pname}] {len(best)}/{len(wins)} periods have an item")
                    for k, (cc, iid, d) in best.items():
                        log(f"    {k:10s} {d} cloud={cc:6.2f} {iid}")
                elif a["id"] == "farm_sk_quarter":
                    log(f"  [{pname}] {len(best)}/{len(wins)} periods have an item")
                    for k, (cc, iid, d) in best.items():
                        log(f"    {k:10s} {d} cloud={cc:6.2f} {iid}")
                row[pname]["table"] = best
            cs["aois"][a["id"]] = row
        hits[cat] = sum(1 for r in cs["aois"].values() if r["items"] > 0)
        # equivalence proof on one AOI: fan-out best == binned best
        a = c.aoi("farm_sk_quarter")
        feats, n_single, _ = single_search(base, a["bbox"])
        eq = {}
        for pname in ("monthly", "every July"):
            period = PERIODS[pname]
            binned = best_per_period(feats, period, SPEC["start"])
            fan, n_fan = fanout_best(base, a["bbox"], period_windows(period, SPEC["start"], SPEC["end"]))
            same = {k: binned.get(k, (None, None))[0] == fan.get(k, (None, None))[0] for k in set(binned) | set(fan)}
            eq[pname] = {"single_requests": n_single, "fanout_requests": n_fan, "periods": len(same),
                         "same_best_cloud": sum(same.values())}
            log(f"\n{cat} equivalence on farm_sk_quarter [{pname}]: single search {n_single} request(s) vs fan-out {n_fan}; "
                f"best-cloud identical in {sum(same.values())}/{len(same)} periods")
        cs["equivalence"] = eq
        summary["catalogs"][cat] = cs
        log(f"\n{cat}: {cs['single_requests']} requests for 15 AOIs (single search) vs fan-out {cs['fanout_requests_theory']}")
    summary["aoi_hits"] = hits
    json.dump(summary, open(f"{c.OUT}/q3_result.json", "w"), indent=1, default=str)
    return summary


if __name__ == "__main__":
    run()

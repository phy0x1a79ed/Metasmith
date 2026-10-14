"""Shared helpers for lane A probes: rate-limited HTTP, AOI loading, static STAC crawling with an on-disk cache."""
import json, re, threading, time, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import requests
from shapely.geometry import shape, box

ROOT = Path("/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query")
LANE = ROOT / "reports/probes/A"
CACHE = LANE / "cache"
CACHE.mkdir(exist_ok=True)
CONTROL_BBOX = (-150.0, 0.0, -149.9, 0.1)
S = requests.Session()
S.headers["User-Agent"] = "geoquery-probe-lane-A/1.0"
_lock = threading.Lock()
_last = {}
MIN_GAP = 0.5  # 2 req/s per host


def aois():
    g = json.load(open(ROOT / "examples/test_aois.geojson"))
    return {f["properties"]["aoi_id"]: shape(f["geometry"]) for f in g["features"]}


def throttle(url):
    host = url.split("/")[2]
    with _lock:
        t = max(time.time(), _last.get(host, 0) + MIN_GAP)
        _last[host] = t
    time.sleep(max(0, t - time.time()))


def req(method, url, retries=3, **kw):
    kw.setdefault("timeout", 60)
    last = None
    for k in range(retries + 1):
        throttle(url)
        try:
            r = S.request(method, url, **kw)
        except requests.RequestException as e:
            last = e
            time.sleep(2 * 2 ** k)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            last = r
            time.sleep(3 * 2 ** k)
            continue
        return r
    if isinstance(last, requests.Response):
        return last
    raise last


def get_json(url, **kw):
    """Cached JSON GET; returns (status, obj or None)."""
    f = CACHE / (hashlib.md5(url.encode()).hexdigest() + ".json")
    if f.exists():
        return 200, json.load(open(f))
    r = req("GET", url, **kw)
    if r.status_code != 200:
        return r.status_code, None
    try:
        o = r.json()
    except ValueError:
        return r.status_code, None
    json.dump(o, open(f, "w"))
    return 200, o


def s3_list(bucket_url, prefix, delimiter="/", max_pages=100):
    """Anonymous S3 ListObjectsV2; returns (prefixes, keys)."""
    pre, keys, tok, n = [], [], None, 0
    while n < max_pages:
        p = {"list-type": 2, "prefix": prefix}
        if delimiter:
            p["delimiter"] = delimiter
        if tok:
            p["continuation-token"] = tok
        r = req("GET", bucket_url, params=p)
        if r.status_code != 200:
            break
        pre += re.findall(r"<Prefix>(.*?)</Prefix>", r.text)
        keys += re.findall(r"<Key>(.*?)</Key>", r.text)
        m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", r.text)
        n += 1
        if not m:
            break
        tok = m.group(1)
    return pre, keys


def crawl(root_url, only_child=None, workers=2, max_items=100000):
    """Walk a static STAC tree. Returns list of item dicts. Each catalog/item fetched once and cached on disk."""
    seen, items = set(), []
    stack = [root_url]
    lock = threading.Lock()

    def visit(u):
        st, o = get_json(u)
        if o is None:
            return []
        if o.get("type") == "Feature":
            with lock:
                items.append(o)
            return []
        nxt = []
        for l in o.get("links", []):
            if l["rel"] in ("child", "item"):
                h = urljoin(u, l["href"])
                if only_child and l["rel"] == "child" and not only_child(h, u):
                    continue
                nxt.append(h)
        return nxt

    with ThreadPoolExecutor(workers) as ex:
        while stack and len(items) < max_items:
            batch = [u for u in stack if u not in seen]
            stack = []
            seen.update(batch)
            for res in ex.map(visit, batch):
                stack += res
    return items


def item_hits(items, aoi_geoms):
    """AOI id -> list of item ids whose bbox/geometry intersects the AOI."""
    out = {k: [] for k in aoi_geoms}
    for it in items:
        g = shape(it["geometry"]) if it.get("geometry") else box(*it["bbox"])
        for k, a in aoi_geoms.items():
            if g.intersects(a):
                out[k].append(it["id"])
    return out

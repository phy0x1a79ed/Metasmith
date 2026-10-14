"""Shared helpers for the lane F STAC probes: AOIs, a polite HTTP client, paginated search, counts."""
import json
import os
import time
from urllib.parse import urlparse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

PC = "https://planetarycomputer.microsoft.com/api/stac/v1"
ES = "https://earth-search.aws.element84.com/v1"
CATALOGS = {"PC": PC, "ES": ES}
CONTROL_BBOX = [-150.0, 0.0, -149.9, 0.1]
MIN_INTERVAL = 0.5


def load_aois():
    gj = json.load(open(os.path.join(ROOT, "examples", "test_aois.geojson")))
    out = []
    for f in gj["features"]:
        xs, ys = [], []
        ring = f["geometry"]["coordinates"][0]
        for x, y in ring:
            xs.append(x)
            ys.append(y)
        out.append({"id": f["properties"]["aoi_id"], "tier": f["properties"].get("tier"),
                    "bbox": [min(xs), min(ys), max(xs), max(ys)], "geometry": f["geometry"],
                    "area_km2": f["properties"].get("area_km2")})
    return out


def aoi(aoi_id):
    return next(a for a in load_aois() if a["id"] == aoi_id)


class Http:
    """requests wrapper: <=2 req/s per host, retry on 429/5xx up to 3 times, counts requests per host."""

    def __init__(self):
        self.s = requests.Session()
        self.last = {}
        self.n = {}
        self.retries = 0
        self.status429 = 0

    def request(self, method, url, **kw):
        host = urlparse(url).netloc
        kw.setdefault("timeout", 90)
        for attempt in range(4):
            wait = MIN_INTERVAL - (time.time() - self.last.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            self.last[host] = time.time()
            self.n[host] = self.n.get(host, 0) + 1
            try:
                r = self.s.request(method, url, **kw)
            except requests.RequestException:
                if attempt == 3:
                    raise
                self.retries += 1
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 429 or r.status_code >= 500:
                if r.status_code == 429:
                    self.status429 += 1
                self.retries += 1
                if attempt == 3:
                    return r
                time.sleep(float(r.headers.get("Retry-After", 3 * (attempt + 1))))
                continue
            return r

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def total(self):
        return sum(self.n.values())


HTTP = Http()


def dt(start, end):
    return f"{start}T00:00:00Z/{end}T23:59:59Z"


def search_page(base, body):
    r = HTTP.post(base + "/search", json=body)
    return r


def search_all(base, body, max_pages=20):
    """Follow rel=next POST links. Returns (features, n_requests, last_status)."""
    feats, n, status = [], 0, None
    cur = dict(body)
    for _ in range(max_pages):
        r = search_page(base, cur)
        n += 1
        status = r.status_code
        if r.status_code != 200:
            break
        j = r.json()
        feats.extend(j.get("features", []))
        nxt = next((l for l in j.get("links", []) if l.get("rel") == "next"), None)
        if not nxt or not j.get("features"):
            break
        nb = nxt.get("body") or {}
        cur = {**cur, **nb} if nxt.get("merge") else nb
    return feats, n, status


def count(base, body):
    """Number of items matched. Uses numberMatched when the server reports it, else pages through ids."""
    b = {**body, "limit": 1}
    r = search_page(base, b)
    if r.status_code != 200:
        return None, r.status_code, 1
    j = r.json()
    m = j.get("numberMatched")
    if m is None:
        m = (j.get("context") or {}).get("matched")
    if m is not None:
        return m, 200, 1
    b = {**body, "limit": 1000, "fields": {"include": ["id"]}}
    feats, n, st = search_all(base, b)
    return len(feats), st, n + 1


def sign_pc(item_or_href):
    import planetary_computer as pc
    return pc.sign(item_or_href)

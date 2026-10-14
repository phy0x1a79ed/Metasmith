"""Build the 50-photo geolocation test set: Commons geosearch + Panoramax + worldwide. Re-runnable (seeded)."""
import csv, io, json, os, random, re, sys, time
import requests
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ORIG = os.path.join(HERE, "orig"); IMG = os.path.join(HERE, "images")
os.makedirs(ORIG, exist_ok=True); os.makedirs(IMG, exist_ok=True)
UA = {"User-Agent": "geoprobe/0.1 (research probe)"}
random.seed(20261013)
COMMONS = "https://commons.wikimedia.org/w/api.php"
PANX = "https://api.panoramax.xyz/api/search"

def get(url, **kw):
    for i in range(4):
        r = requests.get(url, headers=UA, timeout=60, **kw)
        if r.status_code == 429:
            time.sleep(5 * (i + 1)); continue
        return r
    return r

def jget(url, **kw):
    for i in range(5):
        r = get(url, **kw)
        try:
            return r.json()
        except Exception:
            print("non-json", r.status_code, url[:60]); time.sleep(8 * (i + 1))
    return {}

def licence_ok(s):
    s = (s or "").lower()
    return s.startswith("cc") or "public domain" in s or s.startswith("pd") or "etalab" in s or "ouverte" in s or "odbl" in s

def commons_candidates(lat, lon, n, tag, used):
    out = []
    r = jget(COMMONS, params=dict(action="query", list="geosearch", gscoord=f"{lat}|{lon}", gsradius=10000,
                                 gslimit=500, gsnamespace=6, format="json"))
    if "query" not in r:
        print("geosearch error", r); time.sleep(10); return out
    gs = r["query"]["geosearch"]
    time.sleep(0.6)
    random.shuffle(gs)
    gs = [g for g in gs if g["title"].lower().endswith((".jpg", ".jpeg"))]
    for i in range(0, min(len(gs), 120), 40):
        chunk = gs[i:i + 40]
        info = jget(COMMONS, params=dict(action="query", titles="|".join(g["title"] for g in chunk), prop="imageinfo",
                                        iiprop="url|size|mime|extmetadata", format="json"))
        if "query" not in info:
            print("imageinfo error", str(info)[:200]); time.sleep(10); continue
        pages = {p["title"]: p for p in info["query"]["pages"].values()}
        time.sleep(0.6)
        for g in chunk:
            p = pages.get(g["title"]); 
            if not p or "imageinfo" not in p: continue
            ii = p["imageinfo"][0]; em = ii.get("extmetadata", {})
            lic = em.get("LicenseShortName", {}).get("value", "")
            if ii["mime"] != "image/jpeg" or ii["width"] < 1000 or ii["size"] > 25_000_000: continue
            if not licence_ok(lic): continue
            if any(abs(g["lat"] - u[0]) < 0.003 and abs(g["lon"] - u[1]) < 0.003 for u in used): continue
            used.append((g["lat"], g["lon"]))
            out.append(dict(source="commons", true_lat=g["lat"], true_lon=g["lon"], licence=lic,
                            source_url="https://commons.wikimedia.org/wiki/" + g["title"].replace(" ", "_"),
                            title=g["title"], download_url=ii["url"], aoi_id=tag, pixels=f'{ii["width"]}x{ii["height"]}'))
            if len(out) >= n: return out
    return out

def panoramax_candidates(bbox, n, tag, used):
    out = []
    r = jget(PANX, params=dict(bbox=",".join(map(str, bbox)), limit=200))
    feats = r.get("features", [])
    random.shuffle(feats)
    per_coll = {}
    for f in feats:
        c = f["collection"]
        if per_coll.get(c, 0) >= 1: continue
        lic = next((l["href"].rsplit("/", 1)[-1].replace(".html", "") for l in f["links"] if l["rel"] == "license"), "")
        if not licence_ok(lic): continue
        x, y = f["geometry"]["coordinates"]
        if any(abs(y - u[0]) < 0.003 and abs(x - u[1]) < 0.003 for u in used): continue
        ex = f["properties"].get("exif", {})
        w = int(ex.get("Exif.Photo.PixelXDimension", 0) or 0); h = int(ex.get("Exif.Photo.PixelYDimension", 0) or 0)
        pano = ex.get("Xmp.GPano.ProjectionType") or ex.get("Exif.Image.Model", "").lower().find("max") >= 0
        if pano or (w and h and w / h > 1.9): continue
        per_coll[c] = 1; used.append((y, x))
        out.append(dict(source="panoramax", true_lat=y, true_lon=x, licence=lic,
                        source_url=f["links"][[l["rel"] for l in f["links"]].index("self")]["href"],
                        title=f["id"], download_url=f["assets"]["hd"]["href"], aoi_id=tag, pixels=f"{w}x{h}"))
        if len(out) >= n: break
    return out

def main():
    aois = json.load(open(os.path.join(ROOT, "examples", "test_aois.geojson")))["features"]
    seen = {}; 
    for f in aois:
        p = f["properties"]; seen.setdefault((p["centroid_lat"], p["centroid_lon"]), p["aoi_id"])
    rows, used = [], []
    # ~28 Commons near the 12 distinct AOI centroids (15 AOIs; 3 pairs share a centroid)
    cents = list(seen.items())
    quota = [3, 2, 2, 2, 3, 2, 2, 2, 3, 2, 3, 2]
    for ((lat, lon), tag), q in zip(cents, quota):
        c = commons_candidates(lat, lon, q, tag, used); print(tag, len(c)); rows += c
    # Panoramax near AOI cities
    for tag, bb in [("city_toronto_core", (-79.45, 43.62, -79.32, 43.70)), ("city_montreal_core", (-73.65, 45.45, -73.50, 45.55)),
                    ("city_windsor_on", (-83.12, 42.28, -82.95, 42.34)), ("city_us_detroit_mi", (-83.15, 42.30, -83.00, 42.40)),
                    ("farm_on_essex", (-83.0, 42.0, -82.6, 42.3))]:
        c = panoramax_candidates(bb, 2, tag, used); print("panx", tag, len(c)); rows += c
    # worldwide: Commons
    world = [("Tokyo", 35.68, 139.76), ("Nairobi", -1.29, 36.82), ("Sao Paulo", -23.55, -46.63), ("Sydney", -33.87, 151.21),
             ("Reykjavik", 64.14, -21.9), ("Cairo", 30.04, 31.24), ("Mumbai", 19.08, 72.88), ("Lima", -12.05, -77.04),
             ("Cape Town", -33.92, 18.42), ("Ulaanbaatar", 47.92, 106.92), ("Mexico City", 19.43, -99.13), ("Tbilisi", 41.72, 44.79),
             ("Istanbul", 41.01, 28.98), ("Wellington", -41.29, 174.78), ("Anchorage", 61.22, -149.9), ("Bangkok", 13.75, 100.5),
             ("Lagos", 6.52, 3.38), ("Buenos Aires", -34.6, -58.38), ("Hanoi", 21.03, 105.85), ("Windhoek", -22.56, 17.08)]
    for name, lat, lon in world:
        rows += commons_candidates(lat, lon, 1, "world:" + name, used)
    # worldwide: Panoramax
    for name, bb in [("Paris", (2.25, 48.82, 2.42, 48.90)), ("Berlin", (13.3, 52.48, 13.5, 52.56)), ("Bordeaux", (-0.65, 44.8, -0.5, 44.88)),
                     ("Nantes", (-1.6, 47.2, -1.5, 47.25)), ("Lyon", (4.8, 45.72, 4.9, 45.78)), ("Brussels", (4.3, 50.82, 4.42, 50.88))]:
        rows += panoramax_candidates(bb, 2, "world:" + name, used)
    print("candidates", len(rows))
    # trim to 50 favouring spread: keep all panoramax, then commons AOI, then world
    random.shuffle(rows)
    final = []
    for r in rows:
        final.append(r)
    # download
    outrows = []
    for r in final:
        if len(outrows) >= 50: break
        i = len(outrows) + 1
        pid = f"p{i:02d}"
        fn = os.path.join(ORIG, f"{pid}.jpg")
        try:
            d = get(r["download_url"], stream=False)
            if d.status_code != 200: print("skip", r["title"], d.status_code); continue
            open(fn, "wb").write(d.content)
            im = Image.open(fn); im = ImageOps.exif_transpose(im).convert("RGB")
            if im.width / im.height > 1.9:  # equirectangular 360 or panorama strip
                print("skip pano", r["title"]); continue
            w = 640; h = round(im.height * w / im.width)
            im2 = im.resize((w, h), Image.LANCZOS)
            clean = Image.new("RGB", im2.size); clean.putdata(list(im2.getdata()))
            clean.save(os.path.join(IMG, f"{pid}.jpg"), quality=90)
        except Exception as e:
            print("fail", r["title"], e); continue
        r.update(id=pid, orig_file=f"orig/{pid}.jpg", image_file=f"images/{pid}.jpg")
        outrows.append(r); time.sleep(0.5)
    cols = ["id", "source", "true_lat", "true_lon", "licence", "source_url", "title", "aoi_id", "pixels", "download_url", "orig_file", "image_file"]
    with open(os.path.join(HERE, "testset.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, cols, extrasaction="ignore"); w.writeheader()
        for r in sorted(outrows, key=lambda r: r["id"]): w.writerow(r)
    print("wrote", len(outrows))

if __name__ == "__main__":
    main()

"""Step zero: does the original download carry EXIF GPS, and does it match the stated coordinates."""
import csv, os, json, exifread
from math import radians, sin, cos, asin, sqrt
HERE = os.path.dirname(os.path.abspath(__file__))
def hav(a, b, c, d):
    a, b, c, d = map(radians, (a, b, c, d)); h = sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(h))
def dms(v, ref):
    d, m, s = [float(x.num) / float(x.den) for x in v.values]; x = d + m / 60 + s / 3600
    return -x if str(ref) in ("S", "W") else x
out = []
for r in csv.DictReader(open(os.path.join(HERE, "testset.csv"))):
    with open(os.path.join(HERE, r["orig_file"]), "rb") as fh:
        t = exifread.process_file(fh, details=False)
    rec = dict(id=r["id"], source=r["source"], has_gps=False, err_km="", exif_keys=len(t),
               has_direction="GPS GPSImgDirection" in t, has_camera="Image Model" in t, has_datetime="EXIF DateTimeOriginal" in t)
    try:
        la = dms(t["GPS GPSLatitude"], t["GPS GPSLatitudeRef"]); lo = dms(t["GPS GPSLongitude"], t["GPS GPSLongitudeRef"])
        rec.update(has_gps=True, exif_lat=la, exif_lon=lo, err_km=round(hav(la, lo, float(r["true_lat"]), float(r["true_lon"])), 4))
    except KeyError:
        pass
    out.append(rec)
json.dump(out, open(os.path.join(HERE, "exif_check.json"), "w"), indent=1)
g = [o for o in out if o["has_gps"]]
print("n", len(out), "with GPS", len(g))
for s in ("commons", "panoramax"):
    a = [o for o in out if o["source"] == s]; b = [o for o in a if o["has_gps"]]
    print(s, len(a), "GPS", len(b), "within100m", sum(o["err_km"] <= 0.1 for o in b), "within1km", sum(o["err_km"] <= 1 for o in b))
print("direction", sum(o["has_direction"] for o in out), "camera model", sum(o["has_camera"] for o in out), "datetime", sum(o["has_datetime"] for o in out))
print("max err", max((o["err_km"] for o in g), default=None))

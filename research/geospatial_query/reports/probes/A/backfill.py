"""Q1 backfill: re-query the 45 POC scene ids on Planetary Computer and write scene_qc_backfill.csv."""
import warnings; warnings.filterwarnings("ignore")
import csv, json, re, sys, time, math
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np, pandas as pd, requests, rasterio
import planetary_computer as pc
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

ROOT = Path("/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query")
OUT = ROOT / "reports/probes/A"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLL = {"sentinel2_l2a": "sentinel-2-l2a", "landsat_c2l2_st": "landsat-c2-l2", "sentinel1_rtc": "sentinel-1-rtc"}
S = requests.Session()
MAXPIX = 3000


def get(url, **kw):
    for k in range(4):
        r = S.get(url, timeout=60, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 * 2 ** k); continue
        return r
    return r


def aois():
    g = json.load(open(ROOT / "examples/test_aois.geojson"))
    return {f["properties"]["aoi_id"]: shape(f["geometry"]) for f in g["features"]}


def read_aoi(href, geom4326, nodata_fill=None):
    """Read AOI window of a PC raster, masked by the polygon. Returns (array, inside-mask)."""
    with rasterio.open(pc.sign(href)) as src:
        tr = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
        g = shp_transform(tr, geom4326)
        win = from_bounds(*g.bounds, transform=src.transform).intersection(Window(0, 0, src.width, src.height))
        win = Window(math.floor(win.col_off), math.floor(win.row_off), math.ceil(win.width) + 1, math.ceil(win.height) + 1)
        win = win.intersection(Window(0, 0, src.width, src.height))
        h, w = int(win.height), int(win.width)
        sc = min(1.0, MAXPIX / max(h, w))
        oh, ow = max(1, int(h * sc)), max(1, int(w * sc))
        arr = src.read(1, window=win, out_shape=(oh, ow))
        wt = src.window_transform(win)
        from affine import Affine
        t = wt * Affine.scale(w / ow, h / oh)
        inside = geometry_mask([g], out_shape=arr.shape, transform=t, invert=True)
    return arr, inside


def s2_row(it, geom):
    p, a = it["properties"], it["assets"]
    r = {}
    r["off_nadir_deg"], r["off_nadir_source"], r["view_azimuth_deg"] = "", "", ""
    x = get(pc.sign(a["granule-metadata"]["href"]))
    if x.status_code == 200:
        root = ET.fromstring(x.content)
        z = [float(e.text) for m in root.iter() if m.tag.endswith("Mean_Viewing_Incidence_Angle")
             for e in m if e.tag.endswith("ZENITH_ANGLE")]
        az = [float(e.text) for m in root.iter() if m.tag.endswith("Mean_Viewing_Incidence_Angle")
              for e in m if e.tag.endswith("AZIMUTH_ANGLE")]
        if z:
            r["off_nadir_deg"] = round(float(np.mean(z)), 3)
            r["off_nadir_source"] = f"granule-metadata:MTD_TL.xml Mean_Viewing_Incidence_Angle_List/ZENITH_ANGLE mean of {len(z)} bands (min {min(z):.2f} max {max(z):.2f})"
            r["view_azimuth_deg"] = round(float(np.mean(az)), 3)
    else:
        r["off_nadir_source"] = f"granule-metadata HTTP {x.status_code}"
    sz = p.get("s2:mean_solar_zenith")
    r["sun_elevation_deg"] = round(90 - sz, 3) if sz is not None else ""
    r["sun_azimuth_deg"] = p.get("s2:mean_solar_azimuth", "")
    r["cloud_cover_scene_pct"] = p.get("eo:cloud_cover", "")
    arr, inside = read_aoi(a["SCL"]["href"], geom)
    v = inside & (arr != 0)
    n = int(v.sum())
    r["aoi_valid_px"] = n
    if n:
        cls = arr[v]
        cs = np.isin(cls, [3, 8, 9, 10]).mean() * 100
        r["cloud_cover_aoi_pct"] = round(float(cs), 2)
        r["aoi_cloud_detail"] = ";".join(f"scl{c}={np.mean(cls == c) * 100:.1f}" for c in (3, 8, 9, 10))
    r["processing_level"] = f"{p.get('s2:product_type')} (L2A) baseline {p.get('s2:processing_baseline')}"
    r["orbit_state"] = p.get("sat:orbit_state", "")
    r["relative_orbit"] = p.get("sat:relative_orbit", "")
    r["absolute_orbit"] = ""
    r["extra"] = f"mgrs={p.get('s2:mgrs_tile')};shadow_scene={p.get('s2:cloud_shadow_percentage')};cirrus_scene={p.get('s2:thin_cirrus_percentage')};nodata_scene={p.get('s2:nodata_pixel_percentage')};degraded={p.get('s2:degraded_msi_data_percentage')}"
    return r


def ls_row(it, geom):
    p, a = it["properties"], it["assets"]
    r = {"off_nadir_deg": p.get("view:off_nadir", ""), "off_nadir_source": "item property view:off_nadir",
         "view_azimuth_deg": "", "sun_elevation_deg": p.get("view:sun_elevation", ""),
         "sun_azimuth_deg": p.get("view:sun_azimuth", ""), "cloud_cover_scene_pct": p.get("eo:cloud_cover", "")}
    arr, inside = read_aoi(a["qa_pixel"]["href"], geom)
    v = inside & ((arr & 1) == 0)
    n = int(v.sum())
    r["aoi_valid_px"] = n
    if n:
        q = arr[v].astype(np.uint32)
        bit = lambda b: ((q >> b) & 1).astype(bool)
        anyc = bit(1) | bit(2) | bit(3) | bit(4)
        r["cloud_cover_aoi_pct"] = round(float(anyc.mean() * 100), 2)
        r["aoi_cloud_detail"] = f"cloud={bit(3).mean() * 100:.1f};dilated={bit(1).mean() * 100:.1f};cirrus={bit(2).mean() * 100:.1f};shadow={bit(4).mean() * 100:.1f};snow={bit(5).mean() * 100:.1f}"
    r["processing_level"] = f"{p.get('landsat:correction')} {p.get('landsat:collection_category')} C{p.get('landsat:collection_number')}"
    r["orbit_state"] = ""
    r["relative_orbit"] = ""
    r["absolute_orbit"] = ""
    r["extra"] = f"wrs={p.get('landsat:wrs_path')}/{p.get('landsat:wrs_row')};cloud_land={p.get('landsat:cloud_cover_land')};scene_id={p.get('landsat:scene_id')}"
    return r


def s1_row(it, geom):
    p = it["properties"]
    r = {"off_nadir_deg": "per-pixel", "off_nadir_source": "", "view_azimuth_deg": "", "sun_elevation_deg": "n/a",
         "sun_azimuth_deg": "n/a", "cloud_cover_scene_pct": "n/a", "cloud_cover_aoi_pct": "n/a"}
    # the GRD STAC item can be absent (3 of 15 here); the GRD blob folder is still there, same name and hash
    h = it["assets"]["vv"]["href"].rsplit("/measurement/", 1)[0]
    base = h.replace("sentinel1euwestrtc.blob", "sentinel1euwest.blob").replace("/sentinel1-grd-rtc/", "/s1-grd/")
    if True:
        x = get(pc.sign(base + "/annotation/iw-vv.xml"))
        if x.status_code == 200:
            t = x.text
            mid = float(re.search(r"<incidenceAngleMidSwath>(.*?)<", t).group(1))
            head = float(re.search(r"<platformHeading>(.*?)<", t).group(1))
            pts = re.findall(r"<latitude>(.*?)</latitude>\s*<longitude>(.*?)</longitude>.*?<incidenceAngle>(.*?)</incidenceAngle>", t, re.S)
            arr = np.array(pts, dtype=float)
            c = geom.centroid
            f = LinearNDInterpolator(arr[:, [1, 0]], arr[:, 2])(c.x, c.y)
            if np.isnan(f):
                f = NearestNDInterpolator(arr[:, [1, 0]], arr[:, 2])(c.x, c.y)
            r["off_nadir_deg"] = round(float(f), 3)
            r["off_nadir_source"] = (f"sidecar GRD annotation/iw-vv.xml geolocationGrid incidenceAngle interpolated at AOI centroid "
                                     f"({len(arr)} grid pts, range {arr[:, 2].min():.1f}-{arr[:, 2].max():.1f}); incidenceAngleMidSwath={mid:.3f}; "
                                     f"RTC item has no angle asset (only vv, vh)")
            r["incidence_mid_swath_deg"] = round(mid, 3)
            r["view_azimuth_deg"] = round(head, 3)  # platformHeading, not look azimuth
        else:
            r["off_nadir_source"] = f"GRD annotation HTTP {x.status_code}; per-pixel, RTC assets vv/vh only"
    r["aoi_valid_px"] = ""
    r["processing_level"] = f"{p.get('sar:product_type')} L{p.get('s1:processing_level')} RTC (gamma0, terrain corrected); mode {p.get('sar:instrument_mode')}; {p.get('s1:product_timeliness')}"
    r["orbit_state"] = p.get("sat:orbit_state", "")
    r["relative_orbit"] = p.get("sat:relative_orbit", "")
    r["absolute_orbit"] = p.get("sat:absolute_orbit", "")
    r["extra"] = f"orbit_source={p.get('s1:orbit_source')};pol={'/'.join(p.get('sar:polarizations', []))};direction={p.get('sar:observation_direction')};view_azimuth_is_platformHeading"
    return r


COLS = ["aoi_id", "adapter", "item_id", "collection", "datetime", "platform", "status", "off_nadir_deg", "off_nadir_source", "incidence_mid_swath_deg",
        "view_azimuth_deg", "sun_elevation_deg", "sun_azimuth_deg", "cloud_cover_scene_pct", "cloud_cover_aoi_pct",
        "aoi_valid_px", "aoi_cloud_detail", "processing_level", "orbit_state", "relative_orbit", "absolute_orbit", "extra"]


def run():
    d = pd.read_csv(ROOT / "reports/feature_values_long.csv", usecols=["aoi_id", "adapter", "provenance_item"])
    d = d[d.adapter.isin(COLL) & d.provenance_item.notna()].drop_duplicates()
    geoms = aois()
    cache, rows = {}, []
    for _, x in d.sort_values(["adapter", "aoi_id"]).iterrows():
        iid, ad = x.provenance_item, x.adapter
        row = {c: "" for c in COLS}
        row.update(aoi_id=x.aoi_id, adapter=ad, item_id=iid, collection=COLL[ad])
        try:
            key = (ad, iid)
            if key not in cache:
                r = get(f"{STAC}/collections/{COLL[ad]}/items/{iid}")
                cache[key] = r.json() if r.status_code == 200 else None
                if r.status_code != 200:
                    row["status"] = f"item HTTP {r.status_code}"
                time.sleep(0.3)
            it = cache[key]
            if it is None:
                rows.append(row); continue
            row["datetime"] = it["properties"].get("datetime", "")
            row["platform"] = it["properties"].get("platform", "")
            fn = {"sentinel2_l2a": s2_row, "landsat_c2l2_st": ls_row, "sentinel1_rtc": s1_row}[ad]
            row.update(fn(it, geoms[x.aoi_id]))
            row["status"] = "ok"
        except Exception as e:
            row["status"] = f"error {type(e).__name__}: {e}"[:200]
        print(row["aoi_id"], ad, row["status"], row["off_nadir_deg"], row["cloud_cover_aoi_pct"], flush=True)
        rows.append(row)
    pd.DataFrame(rows, columns=COLS).to_csv(OUT / "scene_qc_backfill.csv", index=False)
    return pd.DataFrame(rows, columns=COLS)


if __name__ == "__main__":
    df = run()
    for ad, g in df.groupby("adapter"):
        print(ad, len(g), {c: int((g[c].astype(str).str.len() > 0).sum()) for c in
                           ["off_nadir_deg", "sun_elevation_deg", "sun_azimuth_deg", "cloud_cover_scene_pct", "cloud_cover_aoi_pct", "processing_level", "relative_orbit"]})

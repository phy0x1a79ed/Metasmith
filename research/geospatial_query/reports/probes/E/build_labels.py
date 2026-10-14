"""Label set for StreetCLIP zero-shot: Natural Earth 50m countries (+ representative point) and the 60 most populous
GeoNames cities (pop>=15000) per country."""
import io, json, os, zipfile
import geopandas as gpd, pandas as pd, requests
H = os.path.dirname(os.path.abspath(__file__)); L = os.path.join(H, "labels"); os.makedirs(L, exist_ok=True)
for url, dest in [("https://download.geonames.org/export/dump/cities15000.zip", L), ("https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip", os.path.join(L, "ne50"))]:
    if not os.path.exists(os.path.join(dest, "cities15000.txt" if "geonames" in url else "ne_50m_admin_0_countries.shp")):
        zipfile.ZipFile(io.BytesIO(requests.get(url, timeout=120).content)).extractall(dest)
g = gpd.read_file(os.path.join(L, "ne50", "ne_50m_admin_0_countries.shp"))
g["iso"] = g["ISO_A2_EH"].where(g["ISO_A2_EH"] != "-99", g["ISO_A2"])
g = g[g.iso != "-99"].assign(area=lambda d: d.geometry.area).sort_values("area", ascending=False).drop_duplicates("iso")
def rep(geom):
    if geom.geom_type == "MultiPolygon": geom = max(geom.geoms, key=lambda p: p.area)
    return geom.representative_point()
cols = ["geonameid","name","asciiname","alt","lat","lon","fc","fcode","cc","cc2","a1","a2","a3","a4","pop","elev","dem","tz","mod"]
c = pd.read_csv(os.path.join(L, "cities15000.txt"), sep="\t", header=None, names=cols, keep_default_na=False)
out = {}
for _, r in g.iterrows():
    p = rep(r.geometry)
    cc = c[c.cc == r.iso].sort_values("pop", ascending=False).head(60)
    out[r.iso] = dict(name=r["NAME"], lat=p.y, lon=p.x,
                      cities=[dict(name=x.asciiname, lat=x.lat, lon=x.lon, pop=int(x["pop"])) for _, x in cc.iterrows()])
json.dump(out, open(os.path.join(L, "labels.json"), "w"))
print(len(out), "countries;", sum(len(v["cities"]) for v in out.values()), "city labels;", sum(1 for v in out.values() if not v["cities"]), "countries with no city")

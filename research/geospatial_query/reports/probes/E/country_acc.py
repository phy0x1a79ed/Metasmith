"""Country-level hit rate per model: true and predicted points assigned to a Natural Earth 50m country (nearest within 50 km for coast points)."""
import csv, glob, os
import geopandas as gpd, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
w = gpd.read_file(os.path.join(H, "labels", "ne50", "ne_50m_admin_0_countries.shp"))[["ISO_A2_EH", "geometry"]].to_crs(4326)
def iso(lat, lon):
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon, lat), crs=4326)
    j = gpd.sjoin(pts, w, how="left", predicate="within")
    j = j[~j.index.duplicated()]
    miss = j.ISO_A2_EH.isna()
    if miss.any():
        n = gpd.sjoin_nearest(pts[miss].to_crs(3857), w.to_crs(3857), how="left", max_distance=50000)
        n = n[~n.index.duplicated()]
        j.loc[miss, "ISO_A2_EH"] = n.ISO_A2_EH
    return j.ISO_A2_EH.fillna('??').values
T = pd.read_csv(os.path.join(H, "testset.csv")); T["iso"] = iso(T.true_lat.values, T.true_lon.values)
rows = []
for f in sorted(glob.glob(os.path.join(H, "preds", "*.csv"))):
    P = pd.read_csv(f); P = P.dropna(subset=["pred_lat"]).merge(T[["id", "iso"]], on="id")
    P["piso"] = iso(P.pred_lat.values, P.pred_lon.values)
    rows.append(dict(model=os.path.basename(f)[:-4], n=len(P), country_hits=int((P.piso == P.iso).sum()), country_acc_pct=round(100 * (P.piso == P.iso).mean(), 1)))
pd.DataFrame(rows).to_csv(os.path.join(H, "country_acc.csv"), index=False); print(pd.DataFrame(rows)); print(T.iso.value_counts().head(8))

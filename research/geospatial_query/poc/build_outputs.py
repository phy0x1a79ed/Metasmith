"""poc_records.json -> long feature table, wide feature matrix, coverage matrix, run log."""
import json, sys
import pandas as pd

recs = json.load(open("poc_records.json"))
R = pd.DataFrame(recs)

rows = []
for r in recs:
    for k, v in (r.get("features") or {}).items():
        rows.append({"aoi_id": r["aoi_id"], "slot": r["slot"], "source": r["source"],
                     "family": r["family"], "feature": k, "value": v,
                     "obs_date": r.get("obs_date"), "native_res_m": r.get("res_m"),
                     "licence": r["licence"], "fill_type": r["fill_type"],
                     "provenance_item": r.get("item", "")})
L = pd.DataFrame(rows)

W = L.pivot_table(index="aoi_id", columns="feature", values="value", aggfunc="first")
W = W.reindex(sorted(W.columns), axis=1)

C = R.pivot_table(index="aoi_id", columns="slot", values="status", aggfunc="first")

RUN = R[["aoi_id", "slot", "source", "family", "status", "reason", "n_features", "wall_s",
         "licence", "fill_type"]].copy()

L.to_csv("feature_values_long.csv", index=False)
W.to_csv("feature_matrix.csv")
C.to_csv("coverage_matrix.csv")
RUN.to_csv("run_log.csv", index=False)

print(json.dumps({
    "records": len(R), "aois": R.aoi_id.nunique(), "sources": R.source.nunique(),
    "status": R.status.value_counts().to_dict(),
    "feature_values": len(L), "distinct_features": L.feature.nunique(),
    "matrix_shape": list(W.shape),
    "matrix_density_pct": round(100 * W.notna().mean().mean(), 1),
    "median_wall_s_per_fetch": float(R.wall_s.median()),
    "total_wall_s_serial": round(float(R.wall_s.sum()), 1),
    "per_aoi_serial_s": round(float(R.wall_s.sum()) / R.aoi_id.nunique(), 1),
}, indent=1))

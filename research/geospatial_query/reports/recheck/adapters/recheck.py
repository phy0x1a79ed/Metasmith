"""Compare the design page's listed features against a fresh adapter run.

usage: recheck.py [fresh_long.csv] [overrides.csv]
overrides.csv (feature,status,reason) lets a diagnosed feature be marked fixed or failing.
"""
import os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "..", "feature_values_long.csv")
FRESH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "feature_values_long.csv")
OVR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "overrides.csv")
EXCLUDE = ("control", "bbox_pad", "sample_pad", "skipped")
EMPTY = {"", "nan", "none", "null"}


def real(df):
    s = df["value"].astype(str).str.strip().str.lower()
    return df[df["value"].notna() & ~s.isin(EMPTY)]


old = pd.read_csv(OLD, dtype={"value": str})
listed = old[(old.module_id != "alphaearth")
             & ~old.feature.str.contains("|".join(EXCLUDE), regex=True)]
adapter_of = listed.drop_duplicates("feature").set_index("feature")["adapter"]
n_old = real(listed).groupby("feature").aoi_id.nunique()

fresh = real(pd.read_csv(FRESH, dtype={"value": str}))
n_fresh = fresh.groupby("feature").aoi_id.nunique()

out = pd.DataFrame({"feature": adapter_of.index, "adapter": adapter_of.values})
out["n_aois_old"] = out.feature.map(n_old).fillna(0).astype(int)
out["n_aois_fresh"] = out.feature.map(n_fresh).fillna(0).astype(int)
out["status"] = out.n_aois_fresh.map(lambda n: "ok" if n >= 1 else "failing")
out["reason"] = ""

drop = (out.n_aois_fresh >= 1) & (out.n_aois_fresh < out.n_aois_old / 2)
out.loc[drop, "reason"] = ("partial drop: AOI count fell from "
                           + out.n_aois_old.astype(str) + " to " + out.n_aois_fresh.astype(str))
out.loc[(out.n_aois_fresh == 0) & (out.n_aois_old == 0), "reason"] = "no real value in old table either"

if os.path.exists(OVR):
    ovr = pd.read_csv(OVR).set_index("feature")
    for f, r in ovr.iterrows():
        m = out.feature == f
        assert m.any(), f
        out.loc[m, "status"] = r.status
        out.loc[m, "reason"] = r.reason

out.sort_values(["adapter", "feature"]).to_csv(os.path.join(HERE, "recheck_status.csv"), index=False)
out[drop].sort_values(["adapter", "feature"]).to_csv(os.path.join(HERE, "partial_drops.csv"), index=False)
print(len(out), out.status.value_counts().to_dict(), "partial_drop:", int(drop.sum()))

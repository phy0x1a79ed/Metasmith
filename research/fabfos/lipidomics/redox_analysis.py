import pandas as pd
import re

M = "data/fabfos/runs/scadc_lipidomics/processed/metaboscape/"
mp = pd.read_csv(M + "features_mapped.csv")

# --- (1) miss diagnosis -----------------------------------------------------
miss = mp[mp["map_source"] == "unmapped"]
print("unmapped:", len(miss), "of", len(mp))
deco = miss["name"].astype(str).str.contains(r"_Iso\d|, ?DL-|;|rac-|/", regex=True)
print("unmapped names with iso/stereo/decoration:", int(deco.sum()))
# how many is_lipid==True (MetaboScape's own flag) are unmapped?
if "is_lipid" in mp:
    il = mp[mp["is_lipid"] == True]
    print("MetaboScape is_lipid==True:", len(il),
          "| of those unmapped:", int((il["map_source"] == "unmapped").sum()))
print("\n--- 20 unmapped names (sample) ---")
for n in miss["name"].astype(str).head(20):
    print("  ", n)

# --- (2) redox carriers -----------------------------------------------------
print("\n==================  REDOX / QUINONE CARRIERS  ==================")
redox = mp[
    (mp["super_class"] == "Prenol Lipids")
    | mp["final_class"].astype(str).str.contains(
        "Ubiquinon|Quinone|Vitamin K|Vitamin E|Menaquinon|Tocopher", case=False)
    | mp["name"].astype(str).str.contains(
        "ubiquinone|menaquinone|coenzyme q|tocopher|vitamin k|naphthoquinone|"
        "plastoquinone|demethylmenaquinone|chorismate|quinol", case=False)
]
cols = ["feature_id", "name", "refmet_name", "super_class", "main_class",
        "final_class", "mz", "rt", "msms_score"]
print(redox[cols].to_string())
redox_ids = set(redox["feature_id"])
print("\nredox feature_ids:", sorted(redox_ids))

# --- differential behaviour of redox carriers -------------------------------
def tag(df, fc_col):
    return df[df["feature_id"].isin(redox_ids)].copy()

ds = pd.read_csv(M + "diff_strain_metaboscape.csv")
dsr = ds[ds["feature_id"].isin(redox_ids)]
print("\n--- redox carriers in diff_strain (clone/empty vs parent) ---")
print("any q<0.05?:", int((dsr["qvalue"] < 0.05).sum()),
      "| present_absent flags:", int(dsr["present_absent"].sum()))
sig = dsr[dsr["qvalue"] < 0.05]
if len(sig):
    print(sig[["feature_id", "strain", "parent", "treatment", "fraction",
               "log2fc_strain_vs_parent", "qvalue", "present_absent"]].to_string())
# show the strongest (smallest q) redox rows regardless of threshold
print("\n--- strongest redox diff_strain rows by q ---")
print(dsr.nsmallest(12, "qvalue")[
    ["feature_id", "strain", "parent", "treatment", "fraction", "name"
     if "name" in dsr else "lipid_name",
     "log2fc_strain_vs_parent", "pvalue", "qvalue"]].to_string()
    if "name" in dsr or "lipid_name" in dsr else dsr.nsmallest(12, "qvalue").to_string())

dg = pd.read_csv(M + "diff_global_metaboscape.csv")
dgr = dg[dg["feature_id"].isin(redox_ids)]
print("\n--- redox carriers in diff_global (ANOVA) ---")
print(dgr[["feature_id", "lipid_name", "fraction", "anova_F", "qvalue"]]
      .sort_values("qvalue").to_string())

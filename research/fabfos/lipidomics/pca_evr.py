import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path("research/fabfos/lipidomics").resolve()))
from lipidio import median_normalize, log2

M = Path("data/fabfos/runs/scadc_lipidomics/processed/metaboscape")
df = pd.read_csv(M / "features_mapped.csv")
SAMPLE_RE = r"^(Epi300|EpCC1|ESi300|ESCC1|Clone1|Clone2)_(ctrl|tol)_(P|S)_\d$"
sc = [c for c in df.columns if pd.Series([c]).str.match(SAMPLE_RE)[0]]
X = log2(median_normalize(df[sc].fillna(0.0))).T.values  # samples x features
X = X - X.mean(0)
U, S, Vt = np.linalg.svd(X, full_matrices=False)
evr = S**2 / (S**2).sum()
print("global PCA true EVR: PC1=%.1f%% PC2=%.1f%% PC3=%.1f%% PC4=%.1f%%" %
      tuple(100 * evr[:4]))
# per fraction
for frac in ("P", "S"):
    fc = [c for c in sc if f"_{frac}_" in c]
    Xf = log2(median_normalize(df[fc].fillna(0.0))).T.values
    Xf = Xf - Xf.mean(0)
    s = np.linalg.svd(Xf, compute_uv=False)
    e = s**2 / (s**2).sum()
    print(f"  fraction {frac}: PC1=%.1f%% PC2=%.1f%%" % (100*e[0], 100*e[1]))

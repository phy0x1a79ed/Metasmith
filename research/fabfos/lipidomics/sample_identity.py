"""Correlate each lipidomics sample to every group mean (leave-one-out) to flag mislabelled samples."""
import pandas as pd, numpy as np, sys
D=sys.argv[1]
f=pd.read_csv(f"{D}/features_clean.csv")
m=pd.read_csv(f"{D}/metadata_bio.csv")
cols=[c for c in m.sample_basename if c in f.columns]
for frac in "PS":
    cc=[c for c in cols if f"_{frac}_" in c]
    keep=(f[cc]>0).mean(1)>=0.9
    V=f.loc[keep,cc].fillna(0); V=V.where(V>0, V[V>0].min().min()); X=np.log2(V); X=X-X.median()  # per-sample median norm
    X=X.sub(X.mean(1),axis=0)
    grp={c:c.rsplit("_",1)[0] for c in cc}
    G=sorted(set(grp.values()))
    print(f"\n== {frac}: {keep.sum()} features in >=90% samples. corr of each sample to each group's mean (leave-one-out)")
    print(" "*18+"".join(f"{g[:12]:>13s}" for g in G))
    for c in sorted(cc):
        row=[]
        for g in G:
            mem=[s for s in cc if grp[s]==g and s!=c]
            row.append(np.corrcoef(X[c],X[mem].mean(1))[0,1])
        best=G[int(np.argmax(row))]
        flag="  <-- best match "+best if best!=grp[c] else ""
        print(f"{c:18s}"+"".join(f"{v:13.2f}" for v in row)+flag)

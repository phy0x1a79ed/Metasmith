"""Cluster lipidomics samples blind (correlation, average linkage) and PCA per fraction."""
import pandas as pd, numpy as np, sys
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
D=sys.argv[1]
f=pd.read_csv(f"{D}/features_clean.csv"); m=pd.read_csv(f"{D}/metadata_bio.csv")
cols=[c for c in m.sample_basename if c in f.columns]
for frac in "PS":
    cc=[c for c in cols if f"_{frac}_" in c]
    keep=(f[cc]>0).mean(1)>=0.9
    V=f.loc[keep,cc].fillna(0); V=V.where(V>0,V[V>0].min().min())
    X=np.log2(V); X=X-X.median(); X=X.sub(X.mean(1),axis=0)
    # PCA
    U,S,Vt=np.linalg.svd(X.values-X.values.mean(1,keepdims=True),full_matrices=False)
    ev=S**2/np.sum(S**2); pcs=pd.DataFrame(Vt[:3].T*S[:3],index=cc,columns=["PC1","PC2","PC3"])
    print(f"\n===== {frac}: {keep.sum()} feats; PC var {ev[:4].round(3)}")
    Z=linkage(X.T.values,"average",metric="correlation")
    order=dendrogram(Z,no_plot=True,labels=cc)["ivl"]
    for k in (2,3,4,6,8):
        cl=fcluster(Z,k,"maxclust"); s=pd.Series(cl,index=cc)
        print(f"-- k={k}")
        for c in sorted(set(cl)):
            print("   ",c,sorted(s[s==c].index))
    print("-- dendrogram leaf order:", order)
    print(pcs.sort_values("PC1").round(1).to_string())

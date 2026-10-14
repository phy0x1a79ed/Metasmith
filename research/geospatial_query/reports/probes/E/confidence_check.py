"""Does each model's own confidence rank its hits (error <= 200 km) above its misses? AUROC over the 50 photos."""
import numpy as np, os, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); e = pd.read_csv(os.path.join(H, "errors_per_image.csv"))
for m in ["geoclip", "streetclip_flatcity", "streetclip_city", "plonk_yfcc", "plonk_osv_5m", "g3_align", "ensemble_vote"]:
    p = pd.read_csv(os.path.join(H, "preds", m + ".csv"))[["id", "conf"]].merge(e[e.model == m], on="id")
    y = (p.err_km <= 200).values; c = p.conf.values; pos, neg = c[y], c[~y]
    auc = np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg])
    top = p.sort_values("conf", ascending=False).head(10)
    print(f"{m} AUROC(err<=200km)={auc:.2f} n_hits={y.sum()} top10-by-confidence: median err {top.err_km.median():.0f} km, {(top.err_km <= 200).sum()}/10 within 200 km")

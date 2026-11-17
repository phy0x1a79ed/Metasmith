"""Build the ordination page (PCA and UMAP per CLR variant, plus the checks table) as one HTML file."""
import json
import sys
from pathlib import Path

import pandas as pd

from . import load
from .errors import OUT
from .ordinate import FOCUS, VARIANTS

TEMPLATE = Path(__file__).with_name("page.html")
QC_SHARED_MIN = 0.72
SPREAD_RATIO_MAX = 1.25
DISPARITY_MAX = 0.3


def js(path):
    return json.loads(path.read_text())


def figures():
    o = pd.read_parquet(OUT / "ordination.parquet")
    o["obs"] = o.observation.map(load.LABEL)
    o["x"], o["y"] = o.x.round(4), o.y.round(4)
    cols = ["obs", "sample_id", "strain", "treatment", "x", "y"]
    return {f"{v}_{m}": g[cols].to_dict("list") for (v, m), g in o.groupby(["variant", "method"])}


def cell(value, mark):
    return {"value": value, "mark": mark}


def checks(ordc):
    rows = {k: [] for k in ("Design after rename", "Error model (σ ppm · RT min · mobility %; d² cutoff)",
                            f"Sample / QC read spread (max ratio ≤ {SPREAD_RATIO_MAX})",
                            "Species with two reads from one injection", "CUDA main species detected in",
                            f"QC pairs sharing species (≥ {QC_SHARED_MIN})", "Species raw · blank-kept · core (core ≥ 50)",
                            f"Procrustes disparity of PCA between variants (< {DISPARITY_MAX})",
                            f"Variant A UMAP disparity across seeds (< {DISPARITY_MAX})",
                            "EpCC1 ctrl r2: closer group · 3 nearest")}
    r = list(rows.values())
    for obs in load.OBSERVATIONS:
        d = OUT / obs
        inj = pd.read_parquet(d / "injections.parquet")
        em, mc, tc, oc = js(d / "error_model.json"), js(d / "match_checks.json"), js(d / "tables_checks.json"), ordc[obs]
        n = inj.sample_type.value_counts()
        r[0].append(cell(f"{n['sample']} samples (8 × 3) · {n['qc']} QC · {n['blank']} blanks", "pass"))
        s = em["sigma"]
        capped = " (capped)" if em["d2_equal_density"] > em["d2_cutoff"] else ""
        r[1].append(cell(f"{s['ppm']:.2f} · {s['rt']:.4f} · {s['mob_pct']:.2f}; {em['d2_cutoff']:.0f}{capped}", "pass"))
        rs = mc["resid_sigma"]
        ratio = max(rs["sample"][k] / rs["qc"][k] for k in rs["qc"])
        r[2].append(cell(f"{ratio:.2f}", "pass" if ratio <= SPREAD_RATIO_MAX else "flag"))
        dup = mc["duplicate_read_per_injection"]
        r[3].append(cell(str(dup), "pass" if dup == 0 else "fail"))
        best = max(mc["cuda_species_detected_in"].values())
        r[4].append(cell(f"{best} / {mc['n_injections']} injections", "pass" if best == mc["n_injections"] else "fail"))
        q = mc["qc_pair_shared_frac"]
        r[5].append(cell(f"{q:.2f}", "pass" if q >= QC_SHARED_MIN else "flag"))
        r[6].append(cell(f"{tc['species_raw']} · {tc['species_kept']} · {oc['core']}", "flag" if oc["core_flag"] else "pass"))
        pr = oc["procrustes_pca"]
        r[7].append(cell(" · ".join(f"{k} {v:.2f}" for k, v in pr.items()),
                         "pass" if max(pr.values()) < DISPARITY_MAX else "flag"))
        us = oc["variants"]["A"]["umap_seed_disparity"]
        r[8].append(cell(" · ".join(f"{u:.2f}" for u in us), "pass" if max(us) < DISPARITY_MAX else "flag"))
        fv = {v: oc["variants"][v]["focus"] for v in VARIANTS}
        groups = {f["closer_to"] for f in fv.values()}
        r[9].append(cell("\n".join(f"{v}: {f['closer_to'].replace('_', ' ')} · {', '.join(f['nearest'])}"
                                   for v, f in fv.items()),
                         groups.pop().split("_")[0] if len(groups) == 1 else "mixed"))
    return [{"check": k, "cells": v} for k, v in rows.items()]


def main(out: Path):
    ordc = js(OUT / "ordination_checks.json")
    data = {
        "panels": [load.LABEL[o] for o in load.OBSERVATIONS],
        "variants": VARIANTS,
        "pca_var": {f"{v}_{load.LABEL[o]}": ordc[o]["variants"][v]["pca_var"] for o in load.OBSERVATIONS for v in VARIANTS},
        "figures": figures(),
        "focus": FOCUS,
        "checks": checks(ordc),
    }
    out.write_text(TEMPLATE.read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    print(out, f"{out.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

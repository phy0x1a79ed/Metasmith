"""Build the ordination page (core-only CLR PCA beside the MI ordination, then the checks table) as one HTML file."""
import json
import sys
from pathlib import Path

import pandas as pd

from . import load
from .mi import N_BOOT
from .ordinate import MIN_CORE, VARIANTS

TEMPLATE = Path(__file__).with_name("page.html")
QC_SHARED_MIN = 0.72
SPREAD_RATIO_MAX = 1.25
DISPARITY_MAX = 0.3


def figures():
    o = pd.read_parquet(load.OUT / "ordination.parquet")
    o["obs"] = o.observation.map(load.LABEL)
    o = o[(o.variant == "B") & (o.method == "PCA")].round({"x": 4, "y": 4, "z": 4})
    cols = ["obs", "sample_id", "strain", "treatment", "x", "y"]
    figs = {"B_PCA": o[cols + ["z"]].to_dict("list")}
    mi = pd.read_parquet(load.OUT / "mi.parquet")
    mi["obs"] = mi.observation.map(load.LABEL)
    figs["MI_MDS"] = mi[cols + ["cxx", "cxy", "cyy"]].round(5).to_dict("list")
    return figs


def column(c: dict) -> list[tuple[str, str, str, str]]:
    em, mc, tc, oc, mi = c["error_model"], c["match"], c["tables"], c["ordination"], c["mi"]
    n, s = mc["injections"], em["sigma"]
    capped = " (capped)" if em["d2_equal_density"] > em["d2_cutoff"] else ""
    rs = mc["resid_sigma"]
    ratio = max(rs["sample"][k] / rs["qc"][k] for k in rs["qc"])
    dup = mc["duplicate_read_per_injection"]
    best = max(mc["cuda_species_detected_in"].values())
    q = mc["qc_pair_shared_frac"]
    pr = oc["procrustes_pca"]
    us = oc["variants"]["A"]["umap_seed_disparity"]
    fv = {v: oc["variants"][v]["focus"] for v in VARIANTS}
    groups = {f["closer_to"] for f in fv.values()}
    return [
        ("Design",
         "Sample labels after the spelling fix (Epi300, ESi300 → EPI300; EpCC1, ESCC1 → PCC1). "
         "Normal: 24 samples (8 conditions × 3 replicates), 4 QCs, 4 blanks (pellet) or 8 (supernatant).",
         f"{n['sample']} samples · {n['qc']} QC · {n['blank']} blanks", "pass"),
        ("Measurement error",
         "How much one ion's m/z, retention time and mobility vary between repeated QC injections, and the "
         "match cutoff (squared distance in σ units) derived from it. Normal: 1–2 ppm · under 0.015 min · "
         "under 0.5 %; cutoff at most 144 (12σ), marked capped when the data alone would allow a wider one.",
         f"{s['ppm']:.2f} ppm · {s['rt']:.4f} min · {s['mob_pct']:.2f} %; cutoff {em['d2_cutoff']:.0f}{capped}",
         "pass"),
        ("Sample vs QC scatter",
         "Whether reads in biological samples scatter around their species more widely than reads in QCs "
         "(matrix effects would make the QC-derived cutoff too tight). Value: largest sample / QC ratio over "
         f"m/z, RT and mobility. Normal: near 1, at most {SPREAD_RATIO_MAX}.",
         f"{ratio:.2f}", "pass" if ratio <= SPREAD_RATIO_MAX else "flag"),
        ("Double-assigned reads",
         "Species holding two reads from one injection, which the matcher forbids. Normal: 0.",
         str(dup), "pass" if dup == 0 else "fail"),
        ("Internal standard",
         "The CUDA standard is spiked into every injection, so it must land in one species found in all of "
         "them. Normal: every injection.",
         f"{best} / {mc['n_injections']} injections", "pass" if best == mc["n_injections"] else "fail"),
        ("QC reproducibility",
         "Mean share of species that two QC injections have in common after matching. Normal: at least "
         f"{QC_SHARED_MIN}, the low end of the earlier pairwise read-match rate (0.72–0.84).",
         f"{q:.2f}", "pass" if q >= QC_SHARED_MIN else "flag"),
        ("Species counts",
         "Species found · kept by the blank filter (sample mean at least 3× blank mean) · core detected in "
         f"all 24 samples, which variants A and B rely on. Normal: core at least {MIN_CORE}.",
         f"{tc['species_raw']} · {tc['species_kept']} · {oc['core']}", "flag" if oc["core_flag"] else "pass"),
        ("Variant agreement",
         "How differently the three zero-handling variants lay out the samples in PCA, per pair (Procrustes "
         f"disparity: 0 identical, 1 unrelated). Normal: below {DISPARITY_MAX}, so the variant choice does not "
         "drive the picture.",
         " · ".join(f"{k} {v:.2f}" for k, v in pr.items()), "pass" if max(pr.values()) < DISPARITY_MAX else "flag"),
        ("UMAP stability",
         "How far variant A's UMAP moves when re-run with two other random seeds (Procrustes disparity). "
         f"Normal: below {DISPARITY_MAX}.",
         " · ".join(f"{u:.2f}" for u in us), "pass" if max(us) < DISPARITY_MAX else "flag"),
        ("PCC1 ctrl r2 placement",
         "Per variant: which group's other replicates sit closer on average to PCC1 ctrl r2, then its 3 "
         "nearest samples. PCC1 ctrl fits the label as recorded; EPI300 ctrl supports a swap. Not pass/fail.",
         "\n".join(f"{v}: {f['closer_to'].replace('_', ' ')} · {', '.join(f['nearest'])}" for v, f in fv.items()),
         groups.pop().split("_")[0] if len(groups) == 1 else "mixed"),
        ("MI replicate signal",
         "Species each sample pair shares above its pair floor (min–max), then the mean MI distance between "
         "replicates and between samples of different conditions. Normal: replicates closer.",
         f"{mi['support'][0]}–{mi['support'][1]} species\nreplicates {mi['d_replicates']:.3f} · "
         f"others {mi['d_between']:.3f}", "pass" if mi["d_replicates"] < mi["d_between"] else "flag"),
        ("MI cross-checks",
         "Rank correlation of the MI distances with Kendall-τ distances on the same species; of each sample's "
         "cloud size with its size factor (negative: low-loading samples get wider clouds); MDS stress. "
         "Not pass/fail.",
         f"τ {mi['rho_mi_kendall']:.2f} · loading {mi['rho_cloud_size_factor']:.2f}\nstress {mi['stress']:.3f}",
         "info"),
    ]


def main(out: Path):
    checks = json.loads((load.OUT / "checks.json").read_text())
    cols = [column(checks[o]) for o in load.OBSERVATIONS]
    data = {
        "panels": [load.LABEL[o] for o in load.OBSERVATIONS],
        "pca_var": {load.LABEL[o]: checks[o]["ordination"]["variants"]["B"]["pca_var"] for o in load.OBSERVATIONS},
        "n_features": {load.LABEL[o]: checks[o]["ordination"]["variants"]["B"]["n_features"] for o in load.OBSERVATIONS},
        "n_boot": N_BOOT,
        "mi_support": {load.LABEL[o]: checks[o]["mi"]["support"] for o in load.OBSERVATIONS},
        "figures": figures(),
        "checks": [{"check": row[0][0], "about": row[0][1],
                    "cells": [{"value": value, "mark": mark} for *_, value, mark in row]} for row in zip(*cols)],
    }
    out.write_text(TEMPLATE.read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    print(out, f"{out.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

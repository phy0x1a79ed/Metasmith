#!/usr/bin/env python3
"""Which LCA* transform each engcyc plan runs, and whether the template's pin is what decides it:
full and lite as shipped, then each with its LCA* target swapped for the other form."""
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "metasmith_libraries"))
import engcyc_metagenomics as M  # noqa: E402

FORMS = {"taxonomy::contig_lcastar_metabuli": "taxonomy::contig_lcastar_no_metabuli",
         "taxonomy::contig_lcastar_no_metabuli": "taxonomy::contig_lcastar_metabuli"}


def swapped(case_targets):
    return {c: [t | {"type": FORMS[t["type"]]} if isinstance(t, dict) and t["type"] in FORMS else t
                for t in ts] for c, ts in case_targets.items()}


def lca_steps(case_targets, label, references=M.REFERENCES):
    task = M.template_for("engcyc_metagenomics", M.DEFAULT_SAMPLES, case_targets=case_targets,
                          references=references).Plan()
    names = collections.Counter(s.transform.name for s in task.plan.steps)
    picked = {k: v for k, v in names.items() if k.startswith("lcastar") or k in ("metabuli", "buildMetabuliDB")}
    print(f"{label:28s} ok={task.ok} steps={len(task.plan.steps)} {picked}", flush=True)


lca_steps(M.CASE_TARGETS, "full")
lca_steps(M.LITE_CASE_TARGETS, "lite", M.LITE_REFERENCES)
lca_steps(swapped(M.CASE_TARGETS), "full, pin swapped")
lca_steps(swapped(M.LITE_CASE_TARGETS), "lite, pin swapped", M.LITE_REFERENCES)

"""Solve the engcyc full template and report size, time and what each DAS Tool step reads."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "metasmith_libraries"))

import engcyc_metagenomics as E  # noqa: E402

t0 = time.perf_counter()
template = E.build_template(rebuild=True)
task = template.Plan()
dt = time.perf_counter() - t0
steps = task.plan.steps
print(f"ok={task.ok} steps={len(steps)} dropped={sorted(task.plan.dropped_targets)} wall={dt:.1f}s")
for s in steps:
    if "das_tool" in (s.transform.name or ""):
        uses = sorted({str(d.dtype_name).split("::")[-1] for d in s.uses if "contig_to_bin_table" in str(d.dtype_name)})
        print(f"  step {s.order} {s.transform.name} cases={s.cases} bin tables={uses}")
for h in getattr(task.plan, "hints", [])[:8]:
    print("HINT", h.kind, h.target, "|", str(h.message)[:300], "| chain:", str(getattr(h, "chain", ""))[:200])

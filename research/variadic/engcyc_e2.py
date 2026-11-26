"""engcyc full plus a second DAS Tool target over the lite binner set, in one plan."""
import sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "metasmith_libraries"))
import engcyc_metagenomics as E
lite_set = {"type": "binning::das_tool_summary", "parents": [0],
            "set": [f"binning::{b}_contig_to_bin_table" for b in ("metabat2", "semibin2", "metadecoder")]}
cases = {c: ts + [lite_set] for c, ts in E.CASE_TARGETS.items()}
t0 = time.perf_counter()
task = E.template_for(E.NAME, E.DEFAULT_SAMPLES, rebuild=True, case_targets=cases).Plan()
print(f"ok={task.ok} steps={len(task.plan.steps)} wall={time.perf_counter()-t0:.1f}s dropped={sorted(task.plan.dropped_targets)}")
for s in task.plan.steps:
    if s.transform.name in ("das_tool", "metadecoder", "comebin"):
        tabs = sorted({str(d.dtype_name).split("::")[-1].replace("_contig_to_bin_table", "") for d in s.uses if "contig_to_bin_table" in str(d.dtype_name)})
        print(f"  step {s.order} {s.transform.name} cases={s.cases} members={tabs}")

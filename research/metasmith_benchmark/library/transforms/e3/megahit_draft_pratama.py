# Ablation rung R3: E3's MEGAHIT assembly again, as OPERA-MS's contig input. The command is the standard
# megahit.py's, without the graph. CAUTION the product must not be sequences::megahit_assembly. Lineage
# requirements are ancestral, so OPERA-MS's contig batches would then satisfy the merge's MEGAHIT lane, and
# the solver drops that lane's own calls.
from metasmith.python_api import *
import json

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("env::megahit.env"))
meta    = model.AddRequirement(lib.GetType("sequences::read_metadata"))
reads   = model.AddRequirement(lib.GetType("sequences::clean_short_reads"), parents={meta})
# Unread. The MinION run limits this step to the 17 hybrid pairings instead of all 65 samples.
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"), parents={meta})
nano    = model.AddRequirement(lib.GetType("e3::nanopore_reads"), parents={pair})
out     = model.AddProduct(lib.GetType("e3::megahit_draft"))


def protocol(context: ExecutionContext):
    ireads, imeta, iout = context.Input(reads), context.Input(meta), context.Output(out)
    parity = json.loads(open(imeta.local).read())["parity"]
    assert parity in {"single", "paired"}, f"unknown parity: [{parity}]"
    parg = "--12" if parity == "paired" else "-r"
    threads = context.params.get('cpus')
    threads = "" if threads is None else f"--num-cpu-threads {threads}"
    mem_gb = context.params.get('memory')
    mem = f"--memory {int(mem_gb * 0.85 * 1024**3)}" if mem_gb else ""
    context.ExecWithEnv(env=image, cmd=f"""
        megahit {threads} {mem} {parg} {ireads.container} -o megahit_ws
        [[ $(head megahit_ws/final.contigs.fa | wc -c) -ne 0 ]] && mv megahit_ws/final.contigs.fa {iout.container} || echo "assembly was empty"
    """)
    return ExecutionResult(manifest=[{out: iout.local}], success=iout.local.exists())


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=meta,
    resources=Resources(cpus=32, memory=Size.GB(32), duration=Duration(hours=18)),
)

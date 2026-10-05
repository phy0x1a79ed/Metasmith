# Ablation rung R4, second half: POLCA polishes Flye's draft with the Illumina replicate's clean reads and
# emits the hybrid lane's assembly. POLCA rather than pypolca: POLCA batches freebayes across threads.
# Ported from E5's e5/polca.py.
from metasmith.python_api import *

lib    = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model  = Transform()
image  = model.AddRequirement(lib.GetType("e3::masurca.env"))
meta   = model.AddRequirement(lib.GetType("sequences::read_metadata"))
asm    = model.AddRequirement(lib.GetType("e3::flye_assembly"), parents={meta})
reads  = model.AddRequirement(lib.GetType("sequences::clean_short_reads"), parents={meta})
out    = model.AddProduct(lib.GetType("e3::hybrid_spades_assembly"))


def protocol(context: ExecutionContext):
    iasm, ireads, iout = context.Input(asm), context.Input(reads), context.Output(out)
    threads = context.params.get("cpus") or 4
    mem_gb = context.params.get("memory")
    # samtools sort's -m is per thread.
    sort_mem = f"-m {max(1, int(mem_gb * 0.5 / threads))}G" if mem_gb else ""

    # POLCA maps with bwa mem single-ended, so the interleaved reads go in as they are. It names its
    # outputs after the assembly it was given, so the draft is copied to a fixed name first.
    context.ExecWithEnv(env=image, cmd=f"""
        cp {iasm.container} flye.fa
        polca.sh -a flye.fa -r {ireads.container} -t {threads} {sort_mem}
        cat flye.fa.report
        cp flye.fa.PolcaCorrected.fa {iout.container}
    """)
    return ExecutionResult(manifest=[{out: iout.local}], success=iout.local.exists() and iout.local.stat().st_size > 0)


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=meta,
    # E5's pilot: 10-13 CPU-h per Pratama pairing at 16 cpus.
    resources=Resources(cpus=16, memory=Size.GB(48), duration=Duration(hours=12)),
)

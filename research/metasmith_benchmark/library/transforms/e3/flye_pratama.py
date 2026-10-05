# Ablation rung R4, first half: Flye --meta on the well's MinION run alone. --nano-hq as in E5's Pratama
# pilot. POLCA (polca_pratama.py) polishes the draft with the Illumina replicate's clean reads.
from metasmith.python_api import *

lib    = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model  = Transform()
image  = model.AddRequirement(lib.GetType("env::flye.env"))
meta   = model.AddRequirement(lib.GetType("sequences::read_metadata"))
pair   = model.AddRequirement(lib.GetType("sequences::read_pair"), parents={meta})
nano   = model.AddRequirement(lib.GetType("e3::nanopore_reads"), parents={pair})
out    = model.AddProduct(lib.GetType("e3::flye_assembly"))


def protocol(context: ExecutionContext):
    inano, iout = context.Input(nano), context.Output(out)
    threads = context.params.get("cpus") or 1
    context.ExecWithEnv(env=image, cmd=f"""
        flye --nano-hq {inano.container} --meta --out-dir flye --threads {threads}
        cp flye/assembly.fasta {iout.container}
    """)
    return ExecutionResult(manifest=[{out: iout.local}], success=iout.local.exists() and iout.local.stat().st_size > 0)


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=meta,
    # E5's pilot: 25-40 CPU-h per Pratama pairing at 16 cpus.
    resources=Resources(cpus=16, memory=Size.GB(64), duration=Duration(hours=12)),
)

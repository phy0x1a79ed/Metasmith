# CLEAN EC prediction for the ORFs on CPU -> clean_cpu_predictions, a clean_predictions the lane reads
# as it reads clean.py's. Same image, model and output as clean.py, with the embedding and maxsep
# rewritten for CPU: removing clean.py's GPU request and keeping its wrapper costs about 9x the
# core-hours of this one. The measurements are in data/engcyc/clean_cpu_bench/RESULTS.md.
#
# Plans only in a run that holds annotation::clean_on_cpu. Such a run pins its CLEAN targets under
# annotation::clean_cpu_predictions, since clean.py is still a producer of clean_predictions.
from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("env::clean.env"))
wrapper = model.AddRequirement(lib.GetType("lib::clean_cpu_wrapper.py"))
opt_in  = model.AddRequirement(lib.GetType("annotation::clean_on_cpu"))
orfs    = model.AddRequirement(lib.GetType("sequences::orfs"))
pred    = model.AddProduct(lib.GetType("annotation::clean_cpu_predictions"))


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    opred = context.Output(pred)
    context.LocalShell(
        'if [ -n "${SLURM_TMPDIR:-}" ] && [ -d "${SLURM_TMPDIR}" ]; then '
        '  rm -rf clean_tmp; mkdir -p "${SLURM_TMPDIR}/clean_tmp"; '
        '  ln -sfn "${SLURM_TMPDIR}/clean_tmp" clean_tmp; '
        'else mkdir -p clean_tmp; fi'
    )
    tmp = context.Mount(context.external_cwd / "clean_tmp", "/clean_tmp")
    context.ExecWithEnv(
        env=image,
        binds=[tmp],
        exports={"TORCH_HOME": "/opt/torch_cache"},
        cmd=f"""
            python {context.Input(wrapper).container} \
                --fasta {iorfs.container} \
                --out {opred.container} \
                --tmp {tmp} \
                --cpus {context.params.get("cpus", 0)}
        """,
    )
    return ExecutionResult(manifest=[{pred: opred.local}], success=opred.local.exists())


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    # 6 workers x 8 threads ran 28-36 ORF/s at a 47 GB peak on fir's EPYC 9655 nodes. 12 h covers an
    # unchunked 300,000-ORF sample (~3.8 h expected) at more than 2x.
    resources=Resources(cpus=48, memory=Size.GB(64), duration=Duration(hours=12)),
)

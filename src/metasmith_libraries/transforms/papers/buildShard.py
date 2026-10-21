from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
shard   = model.AddRequirement(lib.GetType("papers::shard_inputs"))
source  = model.AddRequirement(lib.GetType("papers::kb_source"))
root    = model.AddRequirement(lib.GetType("papers::kb_root"))
weights = model.AddRequirement(lib.GetType("papers::llm_weights"))
image   = model.AddRequirement(lib.GetType("env::llamacpp.env"))
out     = model.AddProduct(lib.GetType("papers::shard_build"))

def protocol(context: ExecutionContext):
    ishard, isrc, iroot, iw = (context.Input(x) for x in (shard, source, root, weights))
    iout = context.Output(out)
    context.ExecWithEnv(
        env=image,
        binds=[(p.external, p.external) for p in (ishard, isrc, iroot)] + [(iw.external, iw.external)],
        cmd=f"K={iroot.external} SRC={isrc.external} MISTRAL={iw.external} COPY_MODELS=0 TMPDIR=$PWD "
            f"bash {isrc.external}/pipeline/shard_step.sh {ishard.external} {iout.container}",
    )
    return ExecutionResult(
        manifest=[{out: iout.local}],
        success=(iout.local / "store").is_dir() and (iout.local / "build.json").exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=shard,
    resources=Resources(
        cpus=8,
        memory=Size.GB(64),
        duration=Duration(hours=8),
        gpus=Gpus.REQUIRED,
        gpu_memory=Size.GB(32),
    ),
)

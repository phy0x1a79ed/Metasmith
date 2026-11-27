from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("env::psortm.env"))
code  = model.AddRequirement(lib.GetType("lib::psortm"))
chunk = model.AddRequirement(lib.GetType("annotation::psortm_input_chunk"))
out   = model.AddProduct(lib.GetType("annotation::psortm_results_chunk"))


def protocol(context: ExecutionContext):
    iout = context.Output(out)
    context.ExecWithEnv(env=image, cmd=f"""
        bash {context.Input(code).container}/psortm.sh {context.Input(chunk).container} {iout.container}
    """)
    return ExecutionResult(manifest=[{out: iout.local}], success=iout.local.exists())


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=chunk,
    resources=Resources(cpus=1, memory=Size.GB(2), duration=Duration(hours=4)),
)

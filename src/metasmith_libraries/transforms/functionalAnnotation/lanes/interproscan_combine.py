from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

# The lanes a template runs differ (full runs all five, lite three), so the target names
# them as its member set, the way DAS Tool takes its binners.
image   = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
orfs    = model.AddRequirement(lib.GetType("sequences::orfs"))
lanes   = model.AddRequirement(lib.GetType("annotation::interproscan_lane_hits"), parents={orfs}, variadic=True)
ev_lib  = model.AddRequirement(lib.GetType("lib::fabfos_evidence.py"))
gpr_lib = model.AddRequirement(lib.GetType("lib::fabfos_gpr"))
out     = model.AddProduct(lib.GetType("annotation::interproscan_hits"))


def protocol(context: ExecutionContext):
    iout = context.Output(out)
    context.ExecWithEnv(env=image, cmd=f"""
        python3 {context.Input(gpr_lib).container}/annotation_table.py \
            --ev-lib {context.Input(ev_lib).container} \
            --table {" ".join(str(m.path.container) for m in context.Inputs(lanes))} \
            --out {iout.container}
    """)
    return ExecutionResult(manifest=[{out: iout.local}], success=iout.local.exists())


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(cpus=1, memory=Size.GB(8), duration=Duration(hours=1)),
)

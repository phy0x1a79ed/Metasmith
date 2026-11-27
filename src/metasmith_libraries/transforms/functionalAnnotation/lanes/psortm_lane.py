from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image  = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
orfs   = model.AddRequirement(lib.GetType("sequences::orfs"))
chunks = model.AddRequirement(lib.GetType("annotation::psortm_results_chunk"), parents={orfs})
merged = model.AddProduct(lib.GetType("annotation::psortm_results"))
ev_lib  = model.AddRequirement(lib.GetType("lib::fabfos_evidence.py"))
gpr_lib = model.AddRequirement(lib.GetType("lib::fabfos_gpr"))
out     = model.AddProduct(lib.GetType("annotation::psortm_lane_table"))


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    iout  = context.Output(out)
    imerged = context.Output(merged)
    group = sorted(context.InputGroup(chunks), key=lambda p: str(p.local))
    gpr = context.Input(gpr_lib).container
    context.ExecWithEnv(env=image, cmd=f"python3 {gpr}/fold_chunks.py header --merge {imerged.container} "
                                      + " ".join(str(p.container) for p in group))
    context.ExecWithEnv(env=image, cmd=f"""
        python3 {gpr}/annotation_table.py \
            --ev-lib {context.Input(ev_lib).container} \
            --orfs {iorfs.container} --source {iorfs.local.stem} \
            --lane psortm {imerged.container} --out {iout.container}
    """)
    for p in group:
        p.local.unlink(missing_ok=True)
    return ExecutionResult(manifest=[{out: iout.local, merged: imerged.local}], success=iout.local.exists())


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(cpus=1, memory=Size.GB(8), duration=Duration(hours=2)),
)

from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
orfs  = model.AddRequirement(lib.GetType("sequences::orfs"))
chunks = [
    model.AddRequirement(lib.GetType("annotation::diamond_uniref90_results_chunk"), parents={orfs}),
    model.AddRequirement(lib.GetType("annotation::diamond_uniref90_descriptions_chunk"), parents={orfs}),
]
merged = [
    model.AddProduct(lib.GetType("annotation::diamond_uniref90_results")),
    model.AddProduct(lib.GetType("annotation::diamond_uniref90_descriptions")),
]
bsr_lib = model.AddRequirement(lib.GetType("lib::diamond_bsr.py"))
ev_lib  = model.AddRequirement(lib.GetType("lib::fabfos_evidence.py"))
gpr_lib = model.AddRequirement(lib.GetType("lib::fabfos_gpr"))
out     = model.AddProduct(lib.GetType("annotation::uniref90_lane_table"))

THREADS = 2


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    iout  = context.Output(out)
    group = lambda slot: sorted(context.InputGroup(slot), key=lambda p: str(p.local))
    ins = [" ".join(str(p.container) for p in group(c)) for c in chunks]
    context.ExecWithEnv(env=image, cmd=f"""
        python3 {context.Input(bsr_lib).container} merge --hits {context.Output(merged[0]).container} \
            --descriptions {context.Output(merged[1]).container} \
            --hit-chunks {ins[0]} --description-chunks {ins[1]}
    """)
    paths = " ".join(str(context.Output(m).container) for m in merged)
    context.ExecWithEnv(env=image, cmd=f"""
        python3 {context.Input(gpr_lib).container}/annotation_table.py \
            --ev-lib {context.Input(ev_lib).container} \
            --orfs {iorfs.container} --source {iorfs.local.stem} \
            --lane uniref90 {paths} --out {iout.container}
    """)
    for c in chunks:
        for p in group(c):
            p.local.unlink(missing_ok=True)
    return ExecutionResult(manifest=[{out: iout.local, **{m: context.Output(m).local for m in merged}}], success=iout.local.exists())


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(cpus=THREADS, memory=Size.GB(8), duration=Duration(hours=2)),
)

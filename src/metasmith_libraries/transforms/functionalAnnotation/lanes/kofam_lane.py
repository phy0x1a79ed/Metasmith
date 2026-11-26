from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
orfs  = model.AddRequirement(lib.GetType("sequences::orfs"))
chunks = [
    model.AddRequirement(lib.GetType("annotation::kofamscan_results_chunk"), parents={orfs}),
    model.AddRequirement(lib.GetType("annotation::kofamscan_descriptions_chunk"), parents={orfs}),
]
merged = [
    model.AddProduct(lib.GetType("annotation::kofamscan_results")),
    model.AddProduct(lib.GetType("annotation::kofamscan_descriptions")),
]
ev_lib  = model.AddRequirement(lib.GetType("lib::fabfos_evidence.py"))
gpr_lib = model.AddRequirement(lib.GetType("lib::fabfos_gpr"))
out     = model.AddProduct(lib.GetType("annotation::kofam_lane_table"))

THREADS = 2


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    iout  = context.Output(out)
    group = lambda slot: sorted(context.InputGroup(slot), key=lambda p: str(p.local))
    gpr = context.Input(gpr_lib).container
    for kind, c, m in zip(("header", "unique-csv"), chunks, merged):
        context.ExecWithEnv(env=image, cmd=f"python3 {gpr}/fold_chunks.py {kind} --merge {context.Output(m).container} "
                                          + " ".join(str(p.container) for p in group(c)))
    paths = " ".join(str(context.Output(m).container) for m in merged)
    context.ExecWithEnv(env=image, cmd=f"""
        python3 {context.Input(gpr_lib).container}/annotation_table.py \
            --ev-lib {context.Input(ev_lib).container} \
            --orfs {iorfs.container} --source {iorfs.local.stem} \
            --lane kofam {paths} --out {iout.container}
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

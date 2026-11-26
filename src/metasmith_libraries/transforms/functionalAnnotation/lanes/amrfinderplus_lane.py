from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
norm  = model.AddRequirement(lib.GetType("env::argnorm.env"))
orfs  = model.AddRequirement(lib.GetType("sequences::orfs"))
chunks = [
    model.AddRequirement(lib.GetType("annotation::amrfinderplus_results_chunk"), parents={orfs}),
]
merged = [
    model.AddProduct(lib.GetType("annotation::amrfinderplus_results")),
]
ev_lib  = model.AddRequirement(lib.GetType("lib::fabfos_evidence.py"))
gpr_lib = model.AddRequirement(lib.GetType("lib::fabfos_gpr"))
out     = model.AddProduct(lib.GetType("annotation::amrfinderplus_lane_table"))

THREADS = 2


# argNorm names the lane's genes as AROs, as PathoFact 2.0's rule argnorm_amrfinder does;
# the lane table carries them as extra columns.
def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    iout  = context.Output(out)
    group = lambda slot: sorted(context.InputGroup(slot), key=lambda p: str(p.local))
    merges = " ".join(f"--merge {context.Output(m).container} " + " ".join(str(p.container) for p in group(c))
                      for c, m in zip(chunks, merged))
    context.ExecWithEnv(env=image, cmd=f"python3 {context.Input(gpr_lib).container}/fold_chunks.py header {merges} ")
    context.ExecWithEnv(env=norm, cmd=f"argnorm amrfinderplus -i {context.Output(merged[0]).container} -o normalised.tsv")
    paths = "normalised.tsv"
    context.ExecWithEnv(env=image, cmd=f"""
        python3 {context.Input(gpr_lib).container}/annotation_table.py \
            --ev-lib {context.Input(ev_lib).container} \
            --orfs {iorfs.container} --source {iorfs.local.stem} \
            --lane amrfinderplus {paths} --out {iout.container}
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

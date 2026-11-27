# lcastar_contig_taxonomy.py without the Metabuli vote, for runs that leave out Metabuli and its
# 192 GB database: UniRef50 ORF LCAs and SSU rRNA vote alone.
from metasmith.python_api import *

lib      = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model    = Transform()
image    = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
asm      = model.AddRequirement(lib.GetType("sequences::assembly"))
orfs     = model.AddRequirement(lib.GetType("sequences::orfs"), parents={asm})
hits     = model.AddRequirement(lib.GetType("annotation::diamond_uniref50_results"), parents={orfs})
descs    = model.AddRequirement(lib.GetType("annotation::diamond_uniref50_descriptions"), parents={orfs})
rrna     = model.AddRequirement(lib.GetType("taxonomy::rrna_gtdb"), parents={asm})
tax_map  = model.AddRequirement(lib.GetType("ref::ncbi_to_gtdb_map"))
lca_lib  = model.AddRequirement(lib.GetType("lib::lcastar"))
out      = model.AddProduct(lib.GetType("taxonomy::contig_lcastar_no_metabuli"))


def protocol(context: ExecutionContext):
    ilib = context.Input(lca_lib)
    iout = context.Output(out)
    weights = " ".join(
        f"--{k.replace('_', '-')} {context.params[k]}"
        for k in ("orf_weight", "rrna_weight")
        if context.params.get(k) is not None)
    context.ExecWithEnv(env=image, cmd=f"""
        PYTHONPATH={ilib.container} python3 {ilib.container}/contig_taxonomy.py \
            --hits {context.Input(hits).container} --descriptions {context.Input(descs).container} \
            --map {context.Input(tax_map).container} --rrna {context.Input(rrna).container} \
            --out {iout.container} {weights}
    """)
    return ExecutionResult(
        manifest=[{out: iout.local}],
        success=iout.local.exists() and iout.local.stat().st_size > 0,
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=asm,
    resources=Resources(cpus=1, memory=Size.GB(32), duration=Duration(hours=6)),
)

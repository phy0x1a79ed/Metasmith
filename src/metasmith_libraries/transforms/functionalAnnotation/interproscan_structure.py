from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image   = model.AddRequirement(lib.GetType("env::interproscan.env"))
orfs    = model.AddRequirement(lib.GetType("sequences::orf_chunk"))
data    = model.AddRequirement(lib.GetType("ref::interproscan_structure_data"))
parser  = model.AddRequirement(lib.GetType("lib::interproscan_gff.py"))
results = model.AddProduct(lib.GetType("annotation::interproscan_structure_results_chunk"))
descriptions = model.AddProduct(lib.GetType("annotation::interproscan_structure_descriptions_chunk"))

APPLICATIONS = "Gene3D,FunFam,SUPERFAMILY"


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    ires  = context.Output(results)
    idesc = context.Output(descriptions)
    cpus  = context.params.get("cpus")
    cpu_flag = "" if cpus is None else f"--cpu {cpus}"

    context.LocalShell(f"pigz -dc {context.Input(data).local} | tar xf -")
    ipr_data = context.Mount(context.external_cwd/"data", "/opt/interproscan/data")
    context.ExecWithEnv(
        env=image,
        binds=[ipr_data],
        cmd=f"""
            sed '/^[^>]/s/\\*//g' {iorfs.container} > orfs.faa
            /opt/interproscan/interproscan.sh --disable-precalc --goterms --seqtype p \
                {cpu_flag} -appl {APPLICATIONS} \
                -i orfs.faa -f gff3 -o matches.gff3
            python3 {context.Input(parser).container} matches.gff3 {ires.container} {idesc.container}
        """,
    )
    context.LocalShell("rm -rf ./data")
    return ExecutionResult(
        manifest=[{results: ires.local, descriptions: idesc.local}],
        success=ires.local.exists() and idesc.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    # 2,000 E. coli ORFs with 8 cores offered: 98 min, 12.5 GB peak, 1.8 cores used (2026-11-27).
    # FunFam searches one superfamily at a time, so cores past a few sit idle.
    resources=Resources(cpus=4, memory=Size.GB(24), duration=Duration(hours=24)),
)

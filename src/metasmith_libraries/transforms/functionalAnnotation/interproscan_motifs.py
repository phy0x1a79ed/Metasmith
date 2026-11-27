from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image   = model.AddRequirement(lib.GetType("env::interproscan.env"))
orfs    = model.AddRequirement(lib.GetType("sequences::orf_chunk"))
data    = model.AddRequirement(lib.GetType("ref::interproscan_motifs_data"))
parser  = model.AddRequirement(lib.GetType("lib::interproscan_gff.py"))
results = model.AddProduct(lib.GetType("annotation::interproscan_motifs_results_chunk"))
descriptions = model.AddProduct(lib.GetType("annotation::interproscan_motifs_descriptions_chunk"))

APPLICATIONS = "ProSitePatterns,ProSiteProfiles,Hamap,PRINTS,CDD,Coils,MobiDBLite"


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    ires  = context.Output(results)
    idesc = context.Output(descriptions)
    cpus  = context.params.get("cpus")

    context.LocalShell(f"pigz -dc {context.Input(data).local} | tar xf -")
    ipr_data = context.Mount(context.external_cwd/"data", "/opt/interproscan/data")
    context.ExecWithEnv(
        env=image,
        binds=[ipr_data],
        cmd=f"""
            sed '/^[^>]/s/\\*//g' {iorfs.container} > orfs.faa
            /opt/interproscan/interproscan.sh --disable-precalc --goterms --seqtype p \
                {"" if cpus is None else f"--cpu {cpus}"} -appl {APPLICATIONS} \
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
    resources=Resources(cpus=8, memory=Size.GB(16), duration=Duration(hours=8)),
)

# PSORTm reads a taxon per protein and takes its envelope from that taxon's phylum, so each ORF
# is tagged from its contig's LCA* lineage. An ORF whose contig LCA* places no deeper than its
# domain keeps a row as Unknown.
from metasmith.python_api import *
from pathlib import Path

lib    = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model  = Transform()
python = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
prep   = model.AddRequirement(lib.GetType("lib::psortm"))
asm    = model.AddRequirement(lib.GetType("sequences::assembly"))
orfs   = model.AddRequirement(lib.GetType("sequences::assembly_orfs"), parents={asm})
taxa   = model.AddRequirement(lib.GetType("taxonomy::contig_lcastar"), parents={asm})
chunk  = model.AddProduct(lib.GetType("annotation::psortm_input_chunk"))

# PSORTm runs about 5,000 proteins a core-hour (research/psortm_pilot), and psortm runs a
# chunk on 4 cores, so a chunk is about an hour.
CHUNK_SIZE = 20000


def protocol(context: ExecutionContext):
    staging = Path("chunks")
    chunk_size = int(context.params.get("psortm_chunk_size", CHUNK_SIZE))
    context.ExecWithEnv(env=python, cmd=f"""
        python3 {context.Input(prep).container}/psortm_prep.py --orfs {context.Input(orfs).container} \
            --contig-taxonomy {context.Input(taxa).container} --chunk-size {chunk_size} --out-dir {staging}
    """)
    manifest_entries = []
    for i, cf in enumerate(sorted(staging.glob("chunk_*.faa"))):
        o = context.Output(chunk, i=i)
        cf.rename(o.local)
        manifest_entries.append({chunk: o.local})
    return ExecutionResult(manifest=manifest_entries, success=len(manifest_entries) > 0)


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(cpus=1, memory=Size.GB(4), duration=Duration(hours=1)),
)

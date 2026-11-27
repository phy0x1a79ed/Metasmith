# PSORTm reads a taxon per protein and takes its envelope from that taxon's phylum, so it runs
# only on the ORFs of quality MAGs, each tagged from its MAG's GTDB-Tk classification. ORFs on
# unbinned or low-quality contigs have no taxonomy and get no localization.
from metasmith.python_api import *
from pathlib import Path

lib    = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model  = Transform()
python = model.AddRequirement(lib.GetType("env::python_for_data_science.env"))
prep   = model.AddRequirement(lib.GetType("lib::psortm"))
asm    = model.AddRequirement(lib.GetType("sequences::assembly"))
orfs   = model.AddRequirement(lib.GetType("sequences::assembly_orfs"), parents={asm})
mags   = model.AddRequirement(lib.GetType("binning_local::quality_bin_fasta"), parents={asm})
taxa   = model.AddRequirement(lib.GetType("taxonomy::gtdbtk_quality"), parents={mags})
chunk  = model.AddProduct(lib.GetType("annotation::psortm_input_chunk"))

# PSORTm runs about 5,000 proteins a core-hour (research/psortm_pilot), and psortm runs a
# chunk on 4 cores, so a chunk is about an hour.
CHUNK_SIZE = 20000


def protocol(context: ExecutionContext):
    taxon_of = {}
    for t in context.InputGroup(taxa):
        m = context.SourceOf(t, mags)
        assert m is not None, f"no quality MAG in the lineage of [{t.local.name}]"
        taxon_of[str(m.local)] = t
    manifest = Path("mags.tsv")
    with open(manifest, "w") as f:
        f.write("mag\tfasta\tgtdbtk\n")
        for m in context.InputGroup(mags):
            t = taxon_of.get(str(m.local))
            if t is None:
                Log.Warn(f"quality MAG [{m.local.name}] has no GTDB-Tk table; its ORFs get no localization")
                continue
            f.write(f"{m.local.stem}\t{m.container}\t{t.container}\n")

    staging = Path("chunks")
    chunk_size = int(context.params.get("psortm_chunk_size", CHUNK_SIZE))
    context.ExecWithEnv(env=python, cmd=f"""
        python3 {context.Input(prep).container}/psortm_prep.py --orfs {context.Input(orfs).container} \
            --mags {manifest} --chunk-size {chunk_size} --out-dir {staging}
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

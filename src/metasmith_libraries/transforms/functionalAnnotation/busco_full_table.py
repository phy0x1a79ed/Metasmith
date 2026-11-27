from metasmith.python_api import *

lib      = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model    = Transform()
image    = model.AddRequirement(lib.GetType("env::busco.env"))
orfs     = model.AddRequirement(lib.GetType("sequences::orf_chunk"))
lineages = model.AddRequirement(lib.GetType("ref::busco_prokaryote_lineages"))
out      = model.AddProduct(lib.GetType("annotation::busco_full_table_chunk"))

# Protein mode on the ORFs already called, so every hit names an ORF. Genome mode would
# re-predict genes per contig and report contig coordinates instead. Both domains run on
# every chunk: an assembly holds bacteria and archaea, and the lane keeps each lineage's
# hits under its own name.
LINEAGES = ("bacteria_odb10", "archaea_odb10")


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    ilin  = context.Input(lineages)
    iout  = context.Output(out)
    cpus  = context.params.get("cpus", 4)

    # Each full_table.tsv carries its lineage in its own `# The lineage dataset is:` line,
    # which is how the lane tells the two apart once concatenated.
    context.ExecWithEnv(
        env=image,
        cmd="\n".join([
            "set -euo pipefail",
            "mkdir -p busco_downloads/lineages",
            *(f"tar -xzf {ilin.container}/{name}.tar.gz -C busco_downloads/lineages" for name in LINEAGES),
            *(f"busco -i {iorfs.container} -o busco_{name} -m proteins -l {name} -c {cpus} -f "
              f"--offline --download_path busco_downloads" for name in LINEAGES),
            f"cat {' '.join(f'busco_{name}/run_{name}/full_table.tsv' for name in LINEAGES)} > {iout.container}",
        ]),
    )

    return ExecutionResult(
        manifest=[{out: iout.local}],
        success=iout.local.exists() and iout.local.stat().st_size > 0,
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=2),
    ),
)

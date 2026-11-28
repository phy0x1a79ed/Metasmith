from metasmith.python_api import *

lib    = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model  = Transform()
image  = model.AddRequirement(lib.GetType("env::diamond.env"))
sprot  = model.AddProduct(lib.GetType("ref::uniprot_sprot_2025_04"))
uniref = model.AddProduct(lib.GetType("ref::uniref_2025_04"))

RELEASE = "previous_releases/release-2025_04"
MIRRORS = ["https://ftp.uniprot.org/pub/databases/uniprot", "https://ftp.ebi.ac.uk/pub/databases/uniprot",
           "https://ftp.expasy.org/databases/uniprot"]
# 1.6 GB and 243 GB.
FILES = {sprot: f"{RELEASE}/knowledgebase/uniprot_sprot-only2025_04.tar.gz",
         uniref: f"{RELEASE}/uniref/uniref2025_04.tar.gz"}
URLS = {path.rsplit("/", 1)[-1]: [f"{m}/{path}" for m in MIRRORS] for path in FILES.values()}


def protocol(context: ExecutionContext):
    staged = context.StagingDir()
    outs = {t: context.Output(t) for t in FILES}
    names = {t: path.rsplit("/", 1)[-1] for t, path in FILES.items()}
    if context.LocalShell("\n".join([
        "set -euo pipefail",
        *(FetchCommand(URLS[names[t]], staged.local/names[t], label=names[t]) for t in FILES),
    ])) != 0:
        return ExecutionResult(manifest=[], success=False)
    res = context.external_shell.Exec(
        " && ".join(f"mv {staged.external/names[t]} {outs[t].external}" for t in FILES),
        timeout=None, history=True)
    if res.exit_code != 0:
        return ExecutionResult(manifest=[], success=False)
    return ExecutionResult(manifest=[{t: o.local for t, o in outs.items()}],
                           success=all(o.local.stat().st_size > 0 for o in outs.values()))


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=image,
    labels=["local"],
    resources=Resources(cpus=1, memory=Size.GB(2), duration=Duration(hours=48)),
)

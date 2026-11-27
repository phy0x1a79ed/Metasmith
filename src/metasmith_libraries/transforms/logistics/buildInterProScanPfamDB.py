from pathlib import Path
from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
img_ipr = model.AddRequirement(lib.GetType("env::interproscan.env"))
sources = model.AddRequirement(lib.GetType("ref::interproscan_sources"))
data    = model.AddProduct(lib.GetType("ref::interproscan_pfam_data"))

# The Pfam lane's member databases under data/. A run reads nothing else there: the
# InterPro entry and GO lookups ship in the image's own work/, and Coils and MobiDB-lite
# are binaries with no data.
MEMBERS = ["pfam"]
RELEASE = "interproscan-5.67-99.0"


def protocol(context: ExecutionContext):
    isrc  = context.Input(sources)
    idata = context.Output(data)

    keep = " ".join(f"{RELEASE}/data/{d}" for d in MEMBERS)
    if context.LocalShell("\n".join([
        "set -euo pipefail",
        "mkdir -p ipr_data",
        f"tar xzf {isrc.local} -C ipr_data --strip-components=1 {keep}",
    ])) != 0:
        return ExecutionResult(manifest=[], success=False)

    # setup.py and interproscan.properties are the IMAGE's copies at /opt/interproscan,
    # so the indexing runs from there over the unpacked data/ bound into place. setup.py
    # presses whichever HMM libraries are present and passes over the absent members.
    ipr_data = context.Mount(context.external_cwd/"ipr_data/data", "/opt/interproscan/data")
    context.ExecWithEnv(
        env=img_ipr,
        binds=[ipr_data],
        cmd="cd /opt/interproscan && python3 setup.py -f interproscan.properties --force",
    )

    threads = context.params.get("cpus")
    threads = "" if threads is None else f"-p {threads}"
    if context.LocalShell(f"mv ipr_data/data ./ && tar -I 'pigz {threads}' -cf {idata.local} ./data") != 0:
        return ExecutionResult(manifest=[], success=False)
    missing = [d for d in MEMBERS if not Path("data", d).is_dir()]
    Log.Info(f"pressed [{len(list(Path('data').rglob('*.h3i')))}] HMM libraries; missing {missing}")
    # The unpacked tree counts against the inode quota on a noscratch step; the product is the archive.
    context.LocalShell("rm -rf ./data ./ipr_data")
    return ExecutionResult(
        manifest=[{data: idata.local}],
        success=idata.local.exists() and not missing,
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=sources,
    labels=["noscratch"],
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=8),
    ),
)

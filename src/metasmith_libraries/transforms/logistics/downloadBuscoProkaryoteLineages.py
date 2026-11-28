from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("env::busco.env"))
out   = model.AddProduct(lib.GetType("ref::busco_prokaryote_lineages"))

# odb10, because busco.env is BUSCO 5.8.3 and odb12 needs BUSCO 6. The md5s are the
# server's own file_versions.tsv for this release.
BASE_URL = "https://busco-data.ezlab.org/v5/data/lineages"
RELEASE = "2024-01-08"
LINEAGES = {
    "bacteria_odb10": "bff9523df89980699c01e8f31e490496",
    "archaea_odb10": "3eb26c670c520c0f3b32bff46fce03d7",
}
URLS = {name: f"{BASE_URL}/{name}.{RELEASE}.tar.gz" for name in LINEAGES}


def protocol(context: ExecutionContext):
    iout = context.Output(out)
    staged = context.StagingDir()
    if context.LocalShell("\n".join([
        "set -euo pipefail",
        *(FetchCommand(URLS[name], staged.local/f"{name}.tar.gz", label=f"BUSCO {name}", md5=md5)
          for name, md5 in LINEAGES.items()),
    ])) != 0:
        return ExecutionResult(manifest=[], success=False)
    res = context.external_shell.Exec(" && ".join([
        f"mkdir -p {iout.external}",
        *(f"mv {staged.external}/{name}.tar.gz {iout.external}/" for name in LINEAGES),
    ]), timeout=None, history=True)
    if res.exit_code != 0:
        return ExecutionResult(manifest=[], success=False)

    return ExecutionResult(
        manifest=[{out: iout.local}],
        success=all((iout.local/f"{name}.tar.gz").stat().st_size > 0 for name in LINEAGES),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=image,
    labels=["local"],
    download_size=Size.GB(0.011),  # 6.3 + 4.8 MB, Content-Length of the two archives
    resources=Resources(
        cpus=1,
        memory=Size.GB(2),
        duration=Duration(hours=1),
    ),
)

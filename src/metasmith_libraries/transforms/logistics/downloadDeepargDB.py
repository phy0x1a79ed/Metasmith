from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("env::deeparg.env"))
sources = model.AddProduct(lib.GetType("ref::deeparg_sources"))

# What `deeparg download_data` fetches (deeparg 1.0.4 entry.py), 1.88 GB.
URLS = {"deeparg": "https://zenodo.org/records/8280582/files/deeparg.zip"}
MD5 = "52198e9d89d5e953ca498f6af1f1b374"


def protocol(context: ExecutionContext):
    isrc = context.Output(sources)
    staged = context.StagingDir()

    if context.LocalShell("\n".join([
        "set -euo pipefail",
        FetchCommand(URLS["deeparg"], staged.local/"deeparg.zip", label="DeepARG data"),
        f'echo "{MD5}  {staged.local}/deeparg.zip" | md5sum -c -',
    ])) != 0:
        return ExecutionResult(manifest=[], success=False)
    res = context.external_shell.Exec(" && ".join([
        f"mkdir -p {isrc.external}",
        f"mv {staged.external}/deeparg.zip {isrc.external}/",
    ]), timeout=None, history=True)
    if res.exit_code != 0:
        return ExecutionResult(manifest=[], success=False)

    return ExecutionResult(
        manifest=[{sources: isrc.local}],
        success=(isrc.local/"deeparg.zip").stat().st_size > 0,
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=image,
    labels=["local"],
    download_size=Size.GB(1.75),  # deeparg.zip Content-Length 1,883,983,799 B, 2026-11-23
    resources=Resources(
        cpus=1,
        memory=Size.GB(2),
        duration=Duration(hours=2),
    ),
)

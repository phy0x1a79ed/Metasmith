from metasmith.python_api import *
import json
import pandas as pd
import numpy as np
import gzip

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

# One transform per read class: a requirement binds one concrete given type, so a generic
# `sequences::reads` slot in a sample holding short and long reads takes the given long reads
# and never the short reads interleaved from their pair, which BBDuk then cannot read.
reads   = model.AddRequirement(lib.GetType("sequences::short_reads"))
img_sqk = model.AddRequirement(lib.GetType("env::seqkit.env"))
stats   = model.AddProduct(lib.GetType("sequences::read_qc_stats"))

# seqkit's own guess (`convert --dry-run`) intersects a per-read range test, so a single
# read scored entirely in B..J, common in clean modern Illumina data, empties it and seqkit
# exits. Phred+64 never scores below '@', and Phred+33 data shows a base under Q31 within
# the first reads.
def phred_encoding(path, records=100_000) -> str:
    with open(path, "rb") as raw:
        gz = raw.read(2) == b"\x1f\x8b"
    with (gzip.open if gz else open)(path, "rt") as f:
        for i, line in enumerate(f):
            if i >= 4*records: break
            if i % 4 == 3 and min(line.rstrip("\n"), default="~") < "@":
                return "sanger"
    return "illumina-1.5+"

def protocol(context: ExecutionContext):
    istats = context.Output(stats)
    ireads = context.Input(reads)

    threads = context.params.get('cpus')
    threads = "" if threads is None else f"--threads {threads}"
    seqkit_stats_file = "seqkit_stats.tsv"
    _cmd = f"""
            seqkit stat {threads} --all --tabular {ireads.container} | tee {seqkit_stats_file}
        """
    context.ExecWithEnv(env=img_sqk, cmd=_cmd)
    encoding = phred_encoding(ireads.local)

    def _as_number(x):
        if "." not in x:
            try:
                return int(x)
            except ValueError:
                pass
        try:
            return float(x)
        except ValueError:
            return x
    def _from_np(x):
        if pd.isna(x):
            return None
        if isinstance(x, str):
            if x.endswith("%"):
                x = x[:-1]
            return _as_number(x)
        if isinstance(x, np.floating) or isinstance(x, np.integer):
            return x.item()
        return x
    df = pd.read_csv(seqkit_stats_file, sep="\t")
    seqkit_stats = {k:_from_np(v) for k, v in dict(df.iloc[0]).items()}

    curated_stats = dict(
        reads=seqkit_stats["num_seqs"],
        bases=seqkit_stats["sum_len"],
        mean_quality=seqkit_stats["AvgQual"],
        q20=seqkit_stats.get("Q20(%)"),
        q30=seqkit_stats.get("Q30(%)"),
        phred_encoding=encoding,
        N50=seqkit_stats["N50"],
        GC=seqkit_stats["GC(%)"],
        _raw=seqkit_stats,
    )
    print(f"stats:")
    for k, v in curated_stats.items():
        if k.startswith("_"): continue
        print(f"    {k}: {v}")

    with open(istats.local, "w") as j:
        json.dump(curated_stats, j)
        
    return ExecutionResult(
        manifest=[{
            stats:istats.local,
        }],
        success=istats.local.exists()
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=reads,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=1),
    )
)

# Ablation rung R3: OPERA-MS in place of hybrid metaSPAdes. It scaffolds E3's MEGAHIT contigs, rebuilt by
# megahit_draft_pratama.py, with the well's MinION run. MEGAHIT is OPERA-MS's own default short-read assembler.
# --no-ref-clustering: the reference database names public
# genomes a novel groundwater community never gets. --no-polishing drops Pilon: the contigs are already
# short-read accurate, and the rung measures graph resolution. Ported from E5's e5/opera_ms.py.
from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("e3::opera_ms.env"))
meta    = model.AddRequirement(lib.GetType("sequences::read_metadata"))
contigs = model.AddRequirement(lib.GetType("e3::megahit_draft"), parents={meta})
reads   = model.AddRequirement(lib.GetType("sequences::clean_short_reads"), parents={meta})
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"), parents={meta})
nano    = model.AddRequirement(lib.GetType("e3::nanopore_reads"), parents={pair})
out     = model.AddProduct(lib.GetType("e3::hybrid_spades_assembly"))

OPERA_MS = "/home/mambauser/operams/OPERA-MS.pl"


def protocol(context: ExecutionContext):
    icontigs, ireads, inano, iout = context.Input(contigs), context.Input(reads), context.Input(nano), context.Output(out)
    threads = context.params.get("cpus") or 2

    # OPERA-MS 0.9.0 refuses a gzipped long-read file and wants R1 and R2 apart. The uncompressed copies
    # are the whole read set, so they go before the product is copied out.
    context.ExecWithEnv(env=image, cmd=f"""
        gzip -dcf {ireads.container} \\
            | awk '{{ if (int((NR-1)/4) % 2 == 0) print > "r1.fastq"; else print > "r2.fastq" }}'
        gzip -dcf {inano.container} > long.fastq
        perl {OPERA_MS} --contig-file {icontigs.container} --short-read1 r1.fastq --short-read2 r2.fastq \\
            --long-read long.fastq --no-ref-clustering --no-polishing --num-processors {threads} --out-dir opera
        rm -f r1.fastq r2.fastq long.fastq
        cat opera/assembly.stats || true
        cp opera/contigs.fasta {iout.container}
    """)
    return ExecutionResult(manifest=[{out: iout.local}], success=iout.local.exists() and iout.local.stat().st_size > 0)


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=meta,
    # E5 scaffolded all 17 Pratama pairings at 16 cpu / 64 GB first try, 3.0-3.4 h wall for the largest.
    resources=Resources(cpus=16, memory=Size.GB(64), duration=Duration(hours=12)),
)

"""Per-genome pilot numbers from the chunk outputs: envelope PSORTm used, ORFs, proteins per
core-hour, peak RSS, and the Unknown fraction per localization class.

    summarise.py WORK_DIR
"""
import collections
import csv
import sys
from pathlib import Path

from make_inputs import GENOMES


def main():
    work = Path(sys.argv[1])
    print("| genome | true envelope | PSORTm envelope | ORFs | proteins / core-hour | peak RSS (MB) | Unknown % |")
    print("|---|---|---|---:|---:|---:|---:|")
    classes = collections.Counter()
    totals = collections.Counter()
    for g, (truth, _) in GENOMES.items():
        envs, locs, cpu, rss, n = collections.Counter(), collections.Counter(), 0.0, 0, 0
        for out in sorted((work / g / "chunks").glob("chunk_*.out")):
            t = dict(zip(*[iter(out.joinpath("time.txt").read_text().split())] * 2))
            cpu += float(t["user_s"]) + float(t["sys_s"])
            rss = max(rss, int(t["maxrss_kb"]))
            with open(out / "psortm_results.tsv") as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    n += 1
                    envs[row["envelope"]] += 1
                    locs[row["localization"] or "(not run)"] += 1
        unknown = locs["Unknown"] + locs["(not run)"]
        totals["orfs"] += n
        totals["cpu"] += cpu
        for k, v in locs.items():
            classes[(g, k)] = v
        env = ", ".join(f"{e} ({c})" for e, c in envs.most_common())
        print(f"| {g} | {truth} | {env} | {n:,} | {n / (cpu / 3600):,.0f} | {rss / 1024:,.0f} "
              f"| {100 * unknown / max(n, 1):.1f} |")
    print(f"\nall genomes: {totals['orfs']:,} ORFs, {totals['cpu'] / 3600:.2f} core-hours, "
          f"{totals['orfs'] / (totals['cpu'] / 3600):,.0f} proteins / core-hour\n")
    locs_all = sorted({k for _, k in classes})
    print("| genome | " + " | ".join(locs_all) + " |")
    print("|---|" + "---:|" * len(locs_all))
    for g in GENOMES:
        n = sum(classes[(g, k)] for k in locs_all)
        print(f"| {g} | " + " | ".join(f"{100 * classes[(g, k)] / max(n, 1):.1f}" for k in locs_all) + " |")


if __name__ == "__main__":
    main()

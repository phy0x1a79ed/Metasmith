"""POC: variadic requirement specialized from target lineage, solved by the Rust engine."""
import statistics
import time

from metasmith.models.solver import Endpoint, Transform, solve_by_mcts
from metasmith.models.variadic import SpecializeForTarget, VariadicError

RAW = {"contig_to_bin_table", "raw"}
DAS = {"contig_to_bin_table", "method:das_tool"}
BINNERS = [f"b{i}" for i in range(1, 11)]


def table(b):
    return RAW | {f"method:{b}"}


def givens():
    meta = Endpoint({"read_metadata"})
    asm = Endpoint({"assembly"}, parents={meta})
    orfs = Endpoint({"orfs"}, parents={asm})
    return [{meta, asm, orfs}]


def binner(b):
    t = Transform()
    t.AddRequirement(properties={"assembly"})
    t.AddProduct(properties=table(b))
    return t


def das_variadic():
    t = Transform()
    asm = t.AddRequirement(properties={"assembly"})
    t.AddRequirement(properties={"orfs"}, parents={asm})
    t.AddRequirement(properties=RAW, parents={asm}, variadic=True)
    t.AddProduct(properties=DAS)
    return t


def das_fixed(bs):
    t = Transform()
    asm = t.AddRequirement(properties={"assembly"})
    t.AddRequirement(properties={"orfs"}, parents={asm})
    for b in bs:
        t.AddRequirement(properties=table(b), parents={asm})
    t.AddProduct(properties=DAS)
    return t


def target(groups, member_targets=True, extra_parent_props=()):
    """One DAS Tool target per group of member binners."""
    t = Transform()
    slots = {}
    for g in groups:
        ps = set()
        for b in g:
            if b not in slots:
                slots[b] = t.AddRequirement(properties=table(b))
            ps.add(slots[b])
        for props in extra_parent_props:
            ps.add(t.AddRequirement(properties=set(props)))
        t.AddRequirement(properties=DAS, parents=ps if member_targets else set())
    return t


def library():
    return [binner(b) for b in BINNERS] + [das_variadic()]


def run(label, transforms, tgt, seed=42, exact=False):
    t0 = time.perf_counter()
    try:
        trs, tgt = SpecializeForTarget(transforms, tgt, exact=exact)
    except VariadicError as e:
        print(f"{label:44s} REFUSED before solve: {e}")
        return
    try:
        sol = solve_by_mcts(givens(), trs, tgt, seed=seed)
    except Exception as e:
        print(f"{label:44s} SOLVER RAISED {type(e).__name__}: {str(e)[:200]}")
        return
    dt = (time.perf_counter() - t0) * 1000
    das = []
    for st in sol.dependency_plan:
        if st.transform is not tgt and "method:das_tool" in str(st.transform):
            das.append(sorted(p.split(":")[1] for e in st.used.values() for p in e.properties if p.startswith("method:")))
    print(f"{label:44s} complete={sol.complete!s:5} steps={len(sol.dependency_plan):2d} {dt:7.1f} ms  das_tool steps use: {das}")


if __name__ == "__main__":
    print("== E1 correctness: DAS Tool from b1,b2,b3 (7 other binners in the library)")
    run("variadic, members as parent targets", library(), target([["b1", "b2", "b3"]]))
    print("== E2 exactness: targets {b1,b2} and {b1,b2,b3} in one solve")
    run("variadic, plain lineage", library(), target([["b1", "b2"], ["b1", "b2", "b3"]]))
    run("variadic, exact members", library(), target([["b1", "b2"], ["b1", "b2", "b3"]]), exact=True)
    print("== E3 missing producer: no binner makes b3")
    run("variadic", [binner("b1"), binner("b2"), das_variadic()], target([["b1", "b2", "b3"]]))
    print("== E4 no members named")
    run("variadic", library(), target([[]]))
    print("== E5 a non-member parent (an assembly pin) stays an ordinary lineage pin")
    run("variadic, parents b1,b2 + assembly", library(), target([["b1", "b2"]], extra_parent_props=[{"assembly"}]))

    print("== E6 solve cost by arity N, median of 5 seeds, 10 binners in the library")
    print(f"{'N':>3} {'variadic+parents ms':>20} {'fixed+parents ms':>17} {'fixed, das only ms':>19}")
    for n in range(1, 9):
        bs = BINNERS[:n]
        cols = []
        for trs, tgt in [
            (library(), target([bs])),
            ([binner(b) for b in BINNERS] + [das_fixed(bs)], target([bs])),
            ([binner(b) for b in BINNERS] + [das_fixed(bs)], target([bs], member_targets=False)),
        ]:
            ts, ok = [], True
            for seed in (1, 2, 3, 4, 5):
                t0 = time.perf_counter()
                strs, stgt = SpecializeForTarget(trs, tgt)
                sol = solve_by_mcts(givens(), strs, stgt, seed=seed)
                ts.append((time.perf_counter() - t0) * 1000)
                # given + n binners + das_tool + target sink
                ok &= sol.complete and len(sol.dependency_plan) == n + 3
            cols.append(f"{statistics.median(ts):8.1f}{'' if ok else ' FAIL'}")
        print(f"{n:>3} {cols[0]:>20} {cols[1]:>17} {cols[2]:>19}")

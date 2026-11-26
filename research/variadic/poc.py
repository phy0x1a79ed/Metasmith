"""POC: a target names a member set as one parent; the variadic slot is specialized per member before the Rust solve."""
import statistics
import time

from metasmith.models.solver import Endpoint, Node, Transform, solve_by_mcts
from metasmith.models.variadic import SetToken, SpecializeForTarget, VariadicError

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


def target(groups, publish_members=False, pin_assembly=False):
    """One DAS Tool target per member set. Returns the target model and its slot -> set map."""
    t = Transform()
    sets = {}
    pubs = {}
    for g in groups:
        if publish_members:
            for b in g:
                pubs.setdefault(b, t.AddRequirement(properties=table(b)))
        pins = {t.AddRequirement(properties={"assembly"})} if pin_assembly else set()
        if g is None:
            t.AddRequirement(properties=DAS, parents=pins)
            continue
        members = [Node(properties=table(b), parents=set()) for b in g]
        slot = t.AddRequirement(properties=DAS | {SetToken(m.properties for m in members)}, parents=pins)
        sets[slot] = members
    return t, sets


def library():
    return [binner(b) for b in BINNERS] + [das_variadic()]


def das_uses(sol, tgt):
    out = []
    for st in sol.dependency_plan:
        if st.transform is not tgt and "method:das_tool" in str(st.transform):
            out.append(sorted(p.split(":")[1] for e in st.used.values() for p in e.properties if p.startswith("method:")))
    return out


def run(label, transforms, groups, seed=42, **kw):
    tgt, sets = target(groups, **kw)
    t0 = time.perf_counter()
    try:
        trs = SpecializeForTarget(transforms, tgt, sets)
    except VariadicError as e:
        print(f"{label:40s} REFUSED before solve: {e}")
        return
    sol = solve_by_mcts(givens(), trs, tgt, seed=seed)
    dt = (time.perf_counter() - t0) * 1000
    print(f"{label:40s} complete={sol.complete!s:5} steps={len(sol.dependency_plan):2d} {dt:6.1f} ms  das_tool steps use: {das_uses(sol, tgt)}")


if __name__ == "__main__":
    print("== E1 DAS Tool from the set {b1,b2,b3}; 7 other binners in the library")
    run("set as one parent", library(), [["b1", "b2", "b3"]])
    print("== E2 sets {b1,b2} and {b1,b2,b3} in one solve")
    run("set as one parent", library(), [["b1", "b2"], ["b1", "b2", "b3"]])
    print("== E3 no binner makes b3")
    run("set as one parent", [binner("b1"), binner("b2"), das_variadic()], [["b1", "b2", "b3"]])
    print("== E4 DAS Tool target with no set")
    run("no set", library(), [None])
    print("== E5 a set plus an ordinary assembly pin")
    run("set + assembly pin", library(), [["b1", "b2"]], pin_assembly=True)
    print("== E5b a member that is not a raw bin table (DAS Tool's own output)")
    tgt, _ = target([])
    bad = Node(properties=DAS, parents=set())
    slot = tgt.AddRequirement(properties=DAS | {SetToken([bad.properties])})
    try:
        SpecializeForTarget(library(), tgt, {slot: [bad]})
        print("   accepted (WRONG)")
    except VariadicError as e:
        print(f"   REFUSED before solve: {e}")

    print("== E6 solve cost by set size N, median of 5 seeds, 10 binners in the library")
    print(f"{'N':>3} {'set, 1 target':>14} {'set + members published':>24} {'fixed das, 1 target':>20}")
    for n in range(1, 9):
        bs = BINNERS[:n]
        cols = []
        for trs, groups, kw, fixed in [
            (library(), [bs], {}, False),
            (library(), [bs], {"publish_members": True}, False),
            ([binner(b) for b in BINNERS] + [das_fixed(bs)], [None], {}, True),
        ]:
            ts, ok = [], True
            for seed in (1, 2, 3, 4, 5):
                tgt, sets = target(groups, **kw)
                t0 = time.perf_counter()
                sol = solve_by_mcts(givens(), SpecializeForTarget(trs, tgt, sets), tgt, seed=seed)
                ts.append((time.perf_counter() - t0) * 1000)
                ok &= sol.complete and das_uses(sol, tgt) == [sorted(bs)]
            cols.append(f"{statistics.median(ts):6.1f}{'' if ok else ' FAIL'}")
        print(f"{n:>3} {cols[0]:>14} {cols[1]:>24} {cols[2]:>20}")

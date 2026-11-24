"""CLEAN EC calls for an ORF FASTA on CPU: ESM-1b mean embeddings, then max-separation, in one process tree.

Runs inside the external_clean image. Writes the 3-column TSV `clean.py` writes. The setup and the
measurements behind it are in the fir benchmark pinned at `data/engcyc/clean_cpu_bench` (RESULTS.md).
"""
import argparse
import multiprocessing as mp
import os
import sys
import time

APP = "/app"
ESM_CKPT = "/opt/torch_cache/hub/checkpoints/esm1b_t33_650M_UR50S"
ALPHA = set("ACDEFGHIKLMNPQRSTVWYXBUZO")
TRUNC = 1022
LAYER = 33


def read_orfs(path):
    """First header token and the sequence ESM-1b can encode: `*` dropped, anything else foreign as X."""
    name, seq, n = None, [], 0
    for line in open(path):
        if line.startswith(">"):
            if name is not None:
                yield name, "".join(seq) or "X"
            n += 1
            name, seq = (line[1:].split() or [f"orf_{n}"])[0], []
        else:
            seq.append("".join(c if c in ALPHA else "X" for c in line.strip().upper() if c != "*"))
    if name is not None:
        yield name, "".join(seq) or "X"


def token_batches(items, toks):
    """Length-sorted batches whose padded size stays within `toks`; a longer sequence goes alone."""
    batches, cur, longest = [], [], 0
    for it in sorted(items, key=lambda x: len(x[1])):
        L = min(len(it[1]), TRUNC) + 2
        if cur and max(longest, L) * (len(cur) + 1) > toks:
            batches.append(cur)
            cur, longest = [], 0
        cur.append(it)
        longest = max(longest, L)
    if cur:
        batches.append(cur)
    return batches


def worker(rank, block, items, a):
    # The block and the OpenMP binding must be in place before torch loads: libgomp reads them once.
    # Each worker binds its 8 threads inside one L3 domain (Zen 5: 8 cores per CCD); a 1,024-token
    # batch's FFN activation (~21 MB) then stays in that L3.
    os.sched_setaffinity(0, block)
    os.environ.update(OMP_NUM_THREADS=str(len(block)), MKL_NUM_THREADS=str(len(block)),
                      OMP_PROC_BIND="close", OMP_PLACES="cores")
    import numpy as np
    import torch
    import esm

    torch.set_num_threads(len(block))
    model, alphabet = esm.pretrained.load_model_and_alphabet_local(a.model)
    model.eval()
    convert = alphabet.get_batch_converter()
    ids, embs = [], []
    autocast = torch.autocast("cpu", dtype=torch.bfloat16, enabled=a.precision == "bf16")
    with torch.inference_mode(), autocast:
        for b in token_batches(items, a.toks):
            _, _, toks = convert([(n, s[:TRUNC]) for n, s in b])
            rep = model(toks, repr_layers=[LAYER])["representations"][LAYER].float()
            for i, (n, s) in enumerate(b):
                ids.append(n)
                embs.append(rep[i, 1:min(len(s), TRUNC) + 1].mean(0).numpy())
    np.save(f"{a.tmp}/emb.r{rank}.npy", np.stack(embs).astype(np.float32))
    with open(f"{a.tmp}/emb.r{rank}.ids", "w") as f:
        f.write("\n".join(ids) + "\n")


def slim_checkpoint(dst):
    """ESM-1b's weights without its optimizer state: 2.6 GB per worker load instead of 7.8 GB."""
    import shutil
    import torch

    os.makedirs(dst, exist_ok=True)
    out = f"{dst}/{os.path.basename(ESM_CKPT)}.pt"
    if not os.path.exists(out):
        d = torch.load(f"{ESM_CKPT}.pt", map_location="cpu")
        torch.save({k: d[k] for k in ("args", "cfg", "model") if k in d}, out + ".part")
        os.replace(out + ".part", out)
        shutil.copy(f"{ESM_CKPT}-contact-regression.pt", dst)
    return out


def embed(items, a):
    blocks = cpu_blocks(sorted(os.sched_getaffinity(0))[:a.cpus], a.threads)
    by_length = sorted(items, key=lambda x: len(x[1]))
    shards = [by_length[r::len(blocks)] for r in range(len(blocks))]
    print(f"[clean_cpu] {len(items)} ORFs on {len(blocks)} workers x {len(blocks[0])} threads, "
          f"{a.precision}, <= {a.toks} tokens per batch", flush=True)
    ctx = mp.get_context("spawn")
    ps = [ctx.Process(target=worker, args=(r, b, s, a)) for r, (b, s) in enumerate(zip(blocks, shards)) if s]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    if any(p.exitcode != 0 for p in ps):
        sys.exit(f"[clean_cpu] embedding failed: worker exit codes {[p.exitcode for p in ps]}")
    import numpy as np

    ids, embs = [], []
    for r in range(len(ps)):
        ids += open(f"{a.tmp}/emb.r{r}.ids").read().split()
        embs.append(np.load(f"{a.tmp}/emb.r{r}.npy"))
    return ids, np.concatenate(embs)


def cpu_blocks(cpus, threads):
    """Disjoint blocks of `threads` allotted cpus, one per worker; fewer cpus than that is one block."""
    if len(cpus) < threads:
        return [cpus]
    return [cpus[i:i + threads] for i in range(0, len(cpus) - threads + 1, threads)]


def maxsep(ids, emb, threads):
    """CLEAN's max-separation calls, as `CLEAN_infer_fasta.py` writes them, without its per-ORF files.

    One MLP pass and a batched distance matrix to the EC centres, a stable top 10, CLEAN's own
    `maximum_separation`, then each GMM's `predict_proba` once over every chosen distance. The bench
    measured the same rows as CLEAN's own writer (24,608 of 24,608 on 20,000 ORFs), 9-13x faster.
    """
    import pickle
    import warnings

    import numpy as np
    import torch
    from CLEAN.evaluate import maximum_separation
    from CLEAN.model import LayerNormNet
    from CLEAN.utils import get_ec_id_dict

    warnings.filterwarnings("ignore", category=UserWarning)
    torch.set_num_threads(threads)
    _, ec_ids = get_ec_id_dict(f"{APP}/data/split100.csv")
    net = LayerNormNet(512, 128, torch.device("cpu"), torch.float32)
    net.load_state_dict(torch.load(f"{APP}/data/pretrained/split100.pth", map_location="cpu"))
    net.eval()
    train = torch.load(f"{APP}/data/pretrained/100.pt", map_location="cpu")
    ecs, centres, i0 = list(ec_ids), [], 0
    for ec in ecs:
        n = len(ec_ids[ec])
        centres.append(train[i0:i0 + n].mean(dim=0))
        i0 += n
    centres = torch.stack(centres)
    gmms = pickle.load(open(f"{APP}/data/pretrained/gmm_ensumble.pkl", "rb"))
    true_component = [0 if g.means_[0][0] < g.means_[1][0] else 1 for g in gmms]
    tops, dists = [], []
    with torch.no_grad():
        q = net(torch.from_numpy(emb))
        for c in range(0, len(q), 64):
            d = (q[c:c + 64, None, :] - centres[None]).norm(dim=2, p=2).numpy()
            top = np.argsort(d, axis=1, kind="stable")[:, :10]
            tops.append(top)
            dists.append(np.take_along_axis(d, top, axis=1))
    top, dist = np.concatenate(tops), np.concatenate(dists)
    chosen = [(i, j) for i, dl in enumerate(dist) for j in range(maximum_separation(list(dl), True, False) + 1)]
    d = np.array([[dist[i, j]] for i, j in chosen])
    conf = np.mean([g.predict_proba(d)[:, t] for g, t in zip(gmms, true_component)], axis=0)
    return [(ids[i], ecs[top[i, j]], c) for (i, j), c in zip(chosen, conf)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fasta", required=True, help="ORF FASTA")
    p.add_argument("--out", required=True, help="standardized TSV: Query ID, Predicted EC number, clean_score")
    p.add_argument("--tmp", required=True, help="writable node-local dir for the slim checkpoint and worker output")
    p.add_argument("--cpus", type=int, default=0, help="use at most this many of the allotted cpus; 0 takes all")
    p.add_argument("--threads", type=int, default=8, help="torch threads per embedding worker")
    p.add_argument("--toks", type=int, default=1024, help="padded tokens per batch")
    p.add_argument("--precision", choices=["bf16", "fp32"], default="bf16")
    p.add_argument("--model", default="", help="ESM-1b checkpoint; default writes a slim copy of the image's into --tmp")
    a = p.parse_args()
    a.cpus = a.cpus or len(os.sched_getaffinity(0))

    t0 = time.time()
    items = list(read_orfs(a.fasta))
    if not items:
        sys.exit("[clean_cpu] the ORF FASTA is empty")
    os.makedirs(a.tmp, exist_ok=True)
    a.model = a.model or slim_checkpoint(f"{a.tmp}/esm")
    ids, emb = embed(items, a)
    t_embed = time.time() - t0
    calls = maxsep(ids, emb, min(a.cpus, len(os.sched_getaffinity(0))))
    with open(a.out, "w") as f:
        f.write("Query ID\tPredicted EC number\tclean_score\n")
        for orf, ec, c in calls:
            f.write(f"{orf}\t{ec}\t{c:.4f}\n")
    called = len({orf for orf, _, _ in calls})
    print(f"[clean_cpu] {len(calls)} EC calls across {called} ORFs; embed {t_embed:.0f} s, "
          f"total {time.time() - t0:.0f} s -> {a.out}", flush=True)
    # CLEAN never abstains, so an ORF without a call is a lost shard, not an empty answer.
    if called != len({n for n, _ in items}):
        sys.exit(f"[clean_cpu] INCOMPLETE: {called} of {len(items)} input ORFs carry a call")


if __name__ == "__main__":
    main()

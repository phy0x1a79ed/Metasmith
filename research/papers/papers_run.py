#!/usr/bin/env python3
"""Build kb paper batches' shards on sockeye through metasmith: one GPU task per shard.

    papers_run.py deploy
    papers_run.py run BATCH [--nice N] [--dry]
    papers_run.py sweep

kb's pipeline selects each batch (kb.pipeline select) into P/batches/BATCH/s*/ and merges it afterwards
(pipeline/merge.sbatch). Its tick, run with SUBMIT=msm, queues each batch to submit in P/msm/pending. `sweep`, run
nightly from altair after the tick, launches the queued batches, and hands each finished run to the merge. `run`
launches one batch by hand. `deploy` prepares the agent home and imports the inputs every batch shares.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if os.environ.get("MSM_SRC"):
    sys.path.insert(0, os.environ["MSM_SRC"])
import metasmith
from metasmith.python_api import Agent, DataInstanceLibrary, Gpu, Runtime, Size, Spec, SshSource

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "metasmith_libraries"))
import _authoring as A

HOST = os.environ.get("MSM_HPC_HOST", "sockeye")
HOME = Path(os.environ.get("PAPERS_MSM_HOME", "/scratch/st-shallam-1/pwy_group/kb/msm"))
P = Path(os.environ.get("P", "/scratch/st-shallam-1/pwy_group/kb/pipeline"))
K = Path("/arc/project/st-shallam-1/pwy_group/kb")
SRC = Path(os.environ.get("KB_SRC", K / "src/t15"))
MISTRAL = Path("/arc/project/st-shallam-1/pwy_group/hpcllm/models/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf")
IMAGE = os.environ.get("PAPERS_MSM_IMAGE", "docker://quay.io/hallamlab/metasmith:0.24.2")
ACCOUNT = "st-shallam-1-gpu"
CACHE = Path(__file__).resolve().parent / "cache"


def ssh(cmd: str, timeout: int = 120) -> str:
    res = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, cmd], capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"{cmd}: {res.stderr.strip()}")
    return res.stdout


def agent() -> Agent:
    tmp = "/scratch/st-shallam-1/pwy_group/apptainer_tmp"
    return Agent(
        home=SshSource(host=HOST, path=HOME).AsSource(),
        runtime=Runtime.APPTAINER,
        container=IMAGE,
        setup_commands=[
            "module load gcc/9.4.0",
            "module load apptainer/1.3.1",
            f"export APPTAINER_TMPDIR={tmp} TMPDIR={tmp} APPTAINER_CACHEDIR={HOME}/container_images",
        ],
    )


INPUT_TYPES = {"kb/source": (SRC, "papers::kb_source"), "kb/root": (K, "papers::kb_root"),
               "kb/mistral": (MISTRAL, "papers::llm_weights")}


def import_cmd(path, dtype: str, name: str) -> str:
    return (f"BINDS='--bind {K},{P},{MISTRAL.parent}' {HOME}/msm data import {path} --dtype {dtype} --name {name} "
            f"--agent-home {HOME} --type-lib papers={HOME}/types/papers.yml")


def imports(pairs: list[tuple]) -> None:
    """Import each (path, dtype, name) into the agent's pool. Every import mints a new identity, so a name already
    imported is skipped: importing it again would move every plan key that references it."""
    done = CACHE / "imported.json"
    have = set(json.loads(done.read_text())) if done.exists() else set()
    todo = [p for p in pairs if p[2] not in have]
    if not todo:
        return
    setup = " && ".join(["module load gcc/9.4.0 apptainer/1.3.1", *(import_cmd(*p) for p in todo)])
    ssh(setup, timeout=600)
    CACHE.mkdir(parents=True, exist_ok=True)
    done.write_text(json.dumps(sorted(have | {p[2] for p in todo})))


def inputs(batch: str) -> DataInstanceLibrary:
    shards = ssh(f"find {P}/batches/{batch} -mindepth 1 -maxdepth 1 -type d -name 's[0-9]*' | sort").split()
    if not shards:
        raise SystemExit(f"{batch} has no shards under {P}/batches")
    refs = [f"{batch}/{Path(s).name}" for s in shards]
    imports([(s, "papers::shard_inputs", r) for s, r in zip(shards, refs)])
    return agent().GivenLibrary(
        [*INPUT_TYPES, *refs], location=CACHE / f"{batch}.xgdb",
        type_library_paths=[A.TYPES / "papers.yml", A.TYPES / "env.yml"],
    )


def cmd_deploy(a):
    ssh(f"mkdir -p {HOME}/dev")
    src = Path(metasmith.__file__).parent
    subprocess.run(["rsync", "-a", "--delete", "--exclude", "__pycache__", f"{src}/", f"{HOST}:{HOME}/dev/metasmith/"],
                   check=True)
    agent().Deploy()
    ssh(f"mkdir -p {HOME}/types")
    subprocess.run(["scp", "-q", str(A.TYPES / "papers.yml"), f"{HOST}:{HOME}/types/papers.yml"], check=True)
    imports([(p, t, n) for n, (p, t) in INPUT_TYPES.items()])


def launch(batch: str, nice: int, dry: bool = False) -> str | None:
    """Plan buildShard over the batch's shards, stage it and start it. Returns the task key."""
    CACHE.mkdir(parents=True, exist_ok=True)
    lib = inputs(batch)
    task = Spec(
        input_library=lib,
        target_types=["papers::shard_build"],
        transform_libraries=A.transforms("papers"),
        resource_libraries=[A.envs()],
    ).Solve(seed=1)
    if not task.ok or not task.plan.steps:
        raise SystemExit(f"no plan for {batch}: {task.plan}")
    print(f"{len(task.plan.steps)} steps: " + ", ".join(sorted({s.transform.name for s in task.plan.steps})))
    if dry:
        return None
    smith = agent()
    smith.StageWorkflow(task, on_exist="clear", verify_external_paths=False)
    # A compute node has no route to a registry, so the tool images are fetched here, on the login node.
    smith.MaterialiseImages(task)
    # Sockeye's job_submit plugin takes only an untyped --gpus-per-node, so the device carries no type.
    gpu = Gpu(memory=Size.GB(32), count=1, extra=["--partition=gpu", "--constraint=gpu_mem_32"])
    smith.RunWorkflow(task=task, config_file=smith.GetNxfConfigPresets()["slurm"], gpus=gpu, params=dict(
        slurmAccount=ACCOUNT, executor=dict(queueSize=50),
        process=dict(tries=2, clusterOptions=f"--nodes=1 --ntasks=1 --account={ACCOUNT} --nice={nice}")))
    print(json.dumps({"batch": batch, "task": task.GetKey(), "steps": len(task.plan.steps)}))
    return task.GetKey()


def cmd_run(a):
    launch(a.batch, a.nice, a.dry)


def link_stores(batch: str, key: str) -> tuple[int, int]:
    """Link each built store to P/batches/BATCH/stores/<shard>, where the merge reads it. A product directory is named
    for its build, not its shard, so the copy of papers.jsonl it carries says which shard it was. Returns (linked,
    shards)."""
    b = P / "batches" / batch
    script = (f"mkdir -p {b}/stores; "
              f"for d in $(find {HOME}/runs/{key}/results -name build.json -printf '%h\\n'); do "
              f"for f in {b}/s[0-9]*/papers.jsonl; do cmp -s $f $d/papers.jsonl && "
              f"ln -sfn $(realpath $d/store) {b}/stores/$(basename $(dirname $f)) && echo linked; done; done; "
              f"ls -d {b}/s[0-9]* | wc -l")
    out = ssh(script, timeout=600).split()
    return out.count("linked"), int(out[-1])


def cmd_sweep(a):
    """Launch every batch the sockeye tick queued, and hand every finished run to kb's merge. A run whose shards did
    not all build marks its batch failed, so the next tick retries it, and the shards that did build come back from
    metasmith's cache."""
    q = P / "msm"
    ssh(f"mkdir -p {q}/runs && touch {q}/pending")
    for line in ssh(f"cat {q}/pending && : > {q}/pending").splitlines():
        batch, nice = line.split()
        key = launch(batch, int(nice))
        ssh(f"echo '{key} {nice}' > {q}/runs/{batch}")
    for path in ssh(f"ls {q}/runs").split():
        key, nice = ssh(f"cat {q}/runs/{path}").split()
        log = HOME / "runs" / key / "_metasmith/logs.latest/main.log"
        if "run completed at" not in ssh(f"tail -3 {log} 2>/dev/null || true"):
            print(json.dumps({"batch": path, "task": key, "state": "running"}))
            continue
        linked, shards = link_stores(path, key)
        if linked == shards:
            out = ssh(f"cd {P} && MERGE_ONLY=1 bash {SRC}/pipeline/submit.sh batches/{path} {nice}", timeout=600)
            state = "merging " + out.strip()
        else:
            ssh(f"cd {P} && PYTHONPATH={SRC}/src {K}/env/bin/python -m kb.pipeline finish ledger.db {path} --failed")
            state = f"failed: {linked} of {shards} shards built"
        ssh(f"rm {q}/runs/{path}")
        print(json.dumps({"batch": path, "task": key, "state": state}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("deploy").set_defaults(func=cmd_deploy)
    r = sub.add_parser("run")
    r.add_argument("batch")
    r.add_argument("--nice", type=int, default=0)
    r.add_argument("--dry", action="store_true", help="plan only")
    r.set_defaults(func=cmd_run)
    sub.add_parser("sweep").set_defaults(func=cmd_sweep)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()

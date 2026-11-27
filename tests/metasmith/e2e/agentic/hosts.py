"""Per-cluster facts for the first-install harness and its watcher, in one table."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Host:
    ssh: str  # alias in the operator's ~/.ssh/config, also the name the naive agent is told
    account: str  # Slurm account the agent is told to charge
    gpu_account: str  # the account a GPU step charges; a CPU account cannot take GPUs
    scratch_root: str  # parent of every run dir on the cluster
    modules: str  # shell line that makes `apptainer` work, used only when the harness stages an image
    gui_port: int  # distinct per host so concurrent GUIs on altair do not collide
    max_gb: float
    max_files: int = 700_000
    login_nodes: tuple[str, ...] = ()  # the watcher's stop must reach a driver on any of these


HOSTS: dict[str, Host] = {
    "sockeye": Host(
        ssh="sockeye",
        account="st-shallam-1",
        gpu_account="st-shallam-1-gpu",
        # /scratch/<alloc>/$USER, never bare /scratch/$USER (mkdir refused) or /arc/home (Slurm refuses to submit).
        scratch_root="/scratch/st-shallam-1/txyliu/msm_e2e",
        modules="module load gcc/9.4.0 && module load apptainer",
        gui_port=8091,
        max_gb=450.0,
    ),
    "fir": Host(
        ssh="fir",
        account="def-shallam_cpu",
        gpu_account="def-shallam_gpu",
        scratch_root="/scratch/phyberos/msm_e2e",
        modules="module load apptainer",
        gui_port=8092,
        max_gb=1500.0,
        login_nodes=("login1", "login2", "login3"),
    ),
    "nibi": Host(
        ssh="nibi",
        account="def-shallam_cpu",
        gpu_account="def-shallam_gpu",
        scratch_root="/scratch/phyberos/msm_e2e",
        modules="module load apptainer/1.3.5",
        gui_port=8093,
        max_gb=550.0,
    ),
}


def run_tag(run: int, host: str) -> str:
    """Key for every per-run name: local dir, cluster dir, systemd unit, STOP file."""
    return f"run-{run}-{host}"

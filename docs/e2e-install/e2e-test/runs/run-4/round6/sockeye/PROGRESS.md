# PROGRESS
- Session 1 started. No prior notes. Read docs: setup/install.rst, setup/gui.rst, setup/deployment.rst, workflows/engcyc_metagenomics.rst.
PID/log: mamba create (install) log=tmp/install.log
- Monitor bojrsketx armed on install completion.
- install pid 3115820 (my mamba create); monitor bcu0sxssm waits on it. Note pgrep on 'mamba create' also matches another run's process; use pid.
- Agent honored-sockeye deploy clicked via GUI; watch status in GUI agent panel.
- DONE: agent deployed to sockeye (honored-sockeye). NEXT: workflow engcyc_prep_references_lite via GUI Workflows.
- prep_references_lite setup run launched via GUI (run url #runs/enigmatic-llama/enigmatic-llama-xnzAX).
- setup run pU61olfk (staged ShUeUoct) RUNNING on sockeye as of 06:38. Next: monitor via ssh (runs dir /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye/runs/ShUeUoct).
- stirring-rottweiler workflow corrupted; deleting and rebuilding. setup run still running (monitor bmaufcw74).
- piquant-lizard (engcyc_metagenomics_lite, SRR9658108) SOLVED. Waiting for setup run pU61olfk to finish before staging real run on honored-sockeye/slurm.
- SETUP DONE (GUI status completed). NEXT: stage+run piquant-lizard on honored-sockeye/slurm via GUI.
- REAL RUN launched via GUI: piquant-lizard-dkMSp (engcyc_metagenomics_lite, SRR9658108). Monitor on sockeye needed; collect results to ./results at end.
- DONE-ish: real run failed at compile; REPORT.md and CONTROL.json (give_up) written.

# PROGRESS (updated 06:52 UTC 2026-11-28)
Done: metasmith 0.26.2 installed (envs/msm_env). GUI on http://127.0.0.1:8094 (PID 1187795, gui.log, workspace metasmith_ws/).
Done: ssh fir works. Agent speedy-fir deployed (apptainer, slurm preset) at /scratch/phyberos/msm_e2e/run-4-fir-lite.
Done: setup run 0ocSc (engcyc_prep_references_lite, task cg00v0p0) completed; refs 219G at runs/cgO0v0p0/results/references.
RUNNING: metagenomics run fETcI (super-seriema = engcyc_metagenomics_lite, SRR9658108, task key UNX38Kf7) on fir, folder runs/UNX38Kf7. Still running at 06:52 UTC; 6 slurm jobs (promotech, bakta_noncoding, virsorter2, buildGanon2DB, interproscan families/motifs).
FAILED tasks so far (GUI: 5 tasks failed): p60 metadecoder (joblib SyntaxError in image), one UnicodeDecodeError task (nxf_work/41/4429cd1e). Others not yet inspected.
Watch: Monitor bltih99ce expired; re-arm if still needed.
Next: when run ends, collect completed outputs to ./results, write REPORT.md (ERROR/AMBIGUITY/GUESS/WORKAROUND labels) and CONTROL.json.
Known issues: agent "+ a param" did nothing; workflow-panel "+ a param" worked. Avoid full snapshots on workflow pages. Don't ls fir home (wrong path earlier).

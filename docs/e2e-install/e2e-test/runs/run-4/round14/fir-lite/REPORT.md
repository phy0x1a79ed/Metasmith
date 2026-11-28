# REPORT (run 4, fir-lite) — PARTIAL

## Achieved
- metasmith 0.26.2 installed in envs/msm_env (conda, from docs/setup/install.rst).
- GUI started on port 8094 (`msm gui --port 8094 --no-browser`), driven through the browser tools only.
- Agent `misty-fir` deployed through the GUI to ssh://fir:/scratch/phyberos/msm_e2e/run-4-fir-lite (slurm, def-shallam_cpu / def-shallam_gpu, gpuType=h100).
- engcyc_prep_references_lite set up through the GUI (run U3QhuEEA): references present on fir (28 reference dirs).
- engcyc_metagenomics_lite run ufzXt67u (SRR9658108, default targets, misty-fir) started through the GUI. NOT COMPLETE at time of writing.
  - Trace at last check: 208 COMPLETED, 2 FAILED, 2 Slurm jobs still running on fir (promotech 6831407, clean 6831429; ~2h45m left each).
- Partial results copy: sandbox/results/ufzXt67u_results (23 GB, 57 entries). The copy was stopped before it finished, and nxf_trace.tsv was not copied. Treat as incomplete.

## Issues
- ERROR: shipped transform merge_candidate_calls.py (workflow code, transforms/PKo3UlmRwbU5) uses `sample` at line 118 before assigning it at line 145 inside protocol(); Python raises "cannot access local variable 'sample'". Blocks merge_candidate_calls and its downstream steps. Not patched. Doc section: docs/usage/nextflow.rst has no coverage of this; no doc for workflow transform bugs.
- DATA OUTCOME (not setup fault): p80__das_tool exits with "No bins with bin-score >0.5 found". Doc section: none.
- WORKAROUND (GUI): browser_snapshot on the solve page exceeded token limits; used browser_find/screenshots. Doc: docs/setup/gui.rst (no mention).
- WORKAROUND (GUI): typing into the read_pair type combobox appended text; cleared and re-selected. Doc: docs/workflows/engcyc_metagenomics.rst ('change its read_pair row's type ...').
- WORKAROUND (GUI): ref-based clicks on discard buttons hit trail x markers; used indexed selectors. Earlier mis-clicks may have unlinked trail items (not verified). Doc: docs/workflows/engcyc_metagenomics.rst.
- GUESS: GPU memory set to 80 GB (H100). Doc: docs/setup/gui.rst step 5 (no per-card value given).
- AMBIGUITY: setup run reported all 84 steps as cached; references appeared pre-cached on fir. Doc: docs/setup/deployment.rst 'Set up a workflow before its first run'.
- AMBIGUITY: "run param [gpuType] is read by no transform in this plan" log message. Doc: docs/setup/deployment.rst SLURM section.
- AMBIGUITY: a job (nf-p122__buildGanon2DB, 6826532) on fir belongs to another user's run (run-4-fir, ekrKC9dy); not touched.

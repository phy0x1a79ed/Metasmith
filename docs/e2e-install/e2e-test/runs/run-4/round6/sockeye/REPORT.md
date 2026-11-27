# REPORT: metasmith on sockeye, engcyc_metagenomics_lite (SRR9658108)

## Achieved
- Installed metasmith 0.26.2 from the docs' Conda command (install.rst, Conda section) into envs/msm_env.
- Started the web GUI at http://127.0.0.1:8091 from metasmith_ws (gui.rst) and drove it with browser tools.
- Created agent `honored-sockeye` on the `sockeye` host (home /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, apptainer, slurm preset, slurmAccount st-shallam-1, slurmGpuAccount st-shallam-1-gpu). Deploy completed ("deployment complete relay-deployed").
- Ran engcyc_prep_references_lite via "set up" (confirmed "fetch ~162 GB"). Run xnzAX shows completed in the GUI; Nextflow finished 06:43 with 27 tasks served from cache shards.
- Ran engcyc_metagenomics_lite (default targets, short-read sample set to ncbi::sra_short_read_accession SRR9658108, hybrid/long cases removed). Run dkMSp (runs/aFZoT3r0) FAILED at compile time: no results were produced.
- Logs from the failed run are in results/metagenomics_run_logs/ (run_logs.tgz plus extracted files). No analysis outputs exist to collect.

## Issues
- ERROR: engcyc_metagenomics_lite (82-step plan) fails with "Script compilation failed: groovyjarjarasm.asm.MethodTooLargeException: Method too large" in the generated workflow.nf (nxf.log in logs). Blocks the real run. Not covered by the docs; the workflows section gives no step-count limit. Needs a metasmith engine fix or a smaller plan.
- AMBIGUITY: docs/workflows/engcyc_metagenomics.rst names engcyc_metagenomics and engcyc_prep_references; the GUI templates are the _lite variants. I used the _lite names given in the task.
- AMBIGUITY: docs/setup/deployment.rst says slurmGpuAccount is for GPU jobs; the setup run logged "run param [slurmGpuAccount] is read by no transform in this plan... changes nothing" (no GPU step in that plan). The real plan has a GPU step (16 GB default).
- GUI/WORKAROUND: "+ a param" needed a second snapshot to show new rows; removing a row in the recipe needs two clicks (arm, then confirm) and rows reorder after each edit. Several of my edits first hit the wrong row (the hybrid case's read row); I deleted and rebuilt the workflow (stirring-rottweiler -> piquant-lizard).
- WORKAROUND: agent log had no "run completed at" sentinel (docs/agentic/lifecycle_recipes.rst); I used the GUI status and Nextflow's completion lines instead.
- GUIDE: the template left empty long_reads rows after the long case was removed; the planner rejected them ("has no path"). Removed them manually (docs/workflows/engcyc_metagenomics.rst, case-removal guidance does not mention this).

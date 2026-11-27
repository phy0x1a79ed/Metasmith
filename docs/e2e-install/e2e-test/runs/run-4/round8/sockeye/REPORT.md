# REPORT

## Achieved
- metasmith 0.26.2 installed with mamba into envs/msm_env (docs/setup/install.rst, "Conda").
- Web GUI started on http://127.0.0.1:8091 from metasmith_ws (docs/setup/gui.rst).
- Agent `convivial-sockeye` deployed through the GUI to ssh://sockeye:/scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, apptainer runtime, slurm preset with slurmAccount=st-shallam-1 and slurmGpuAccount=st-shallam-1-gpu (docs/setup/deployment.rst).
- engcyc_prep_references_lite run through the GUI (run PsgUD): 22/22 tasks COMPLETED, 20 reference products built on sockeye. Launched with "stage and run" because the GUI "set up" button never launched a run.
- engcyc_metagenomics_lite run through the GUI (workflow festive-cow, run oe91c, SRR9658108 as ncbi::sra_short_read_accession on the short case; hybrid and long cases removed; references case kept; default targets; GPU 16 GB): 21 of 24 tasks COMPLETED. Nextflow finished, but 3 tasks FAILED.
- Collected via GUI "collect results" into ./results (23 entries, 931 MB).

## Not achieved
- The metagenomics run is partial. Missing: seqkit reads, sylph profile, kraken2 report, and every downstream step that needs them. Downstream lanes that depend on those outputs are not in ./results.

## Issues
- ERROR (docs/setup/deployment.rst, "Compute nodes with no internet" / "Set up a workflow before its first run"): compute nodes cannot reach registry-1.docker.io. Tasks p27__seqkit_reads (staphb/seqkit:2.13.0), p29__sylph and p31__kraken2 (staphb/bbtools:39.49) failed to pull their container images. The metagenomics run was started without a setup run that pre-pulls tool images on the login node. Fix: run the workflow setup (pull images) from the login node, then re-run.
- ERROR (docs/setup/gui.rst step 5, docs/setup/deployment.rst "Set up a workflow before its first run"): the GUI "set up" button did nothing on both the prep workflow and the metagenomics workflow (no run, no server log entry). "stage and run" was used on the prep workflow instead. Could not locate a working set-up path in the GUI.
- ERROR (GUI status): the run PsgUD showed "running" for about 11 minutes after Nextflow exited; it changed to "completed" later.
- ERROR (GUI behaviour, not in docs): the workflow row "discard" control is two-step ("click again to confirm"), and clicking the row's .trail x removes a parent link, not the row. This caused a duplicate input row, so I deleted and recreated the silent-shark workflow (now festive-cow).
- AMBIGUITY (docs/workflows/engcyc_metagenomics.rst): "put the run in" the read_pair row. The row carried the template value (short_1 after recreation). I replaced the value with SRR9658108.
- AMBIGUITY (docs/workflows/engcyc_metagenomics.rst, "Delete each read case you have no samples for"): the GUI solve failed until the hybrid and long cases were removed. The docs say to delete them, so I did.
- WORKAROUND (docs/setup/deployment.rst, "SLURM"): the slurmAccount and slurmGpuAccount were inherited from the agent; no extra params were needed.
- WORKAROUND: leftover empty zipped_reverse_short_reads row kept the plan unfinished ("has no path"); removed it manually.
- The docs give no example of the GUI's "set up" flow; I followed the GUI labels.
- WORKAROUND: the ssh config ProxyCommand (.no-fresh-login) points to a stub that always fails; `ssh sockeye` still worked, so I used it for read-only monitoring of the run directories.

## Outputs
- ./results: 23 entries from the collected outputs of run festive-cow-oe91c (partial; see failures above).

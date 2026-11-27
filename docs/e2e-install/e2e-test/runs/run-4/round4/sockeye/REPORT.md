# REPORT (partial: the engcyc_metagenomics_lite run was NOT started)

## Achieved
- metasmith 0.26.2 installed from the docs (envs/msm_env). GUI running on port 8091 (PID 2718304, log logs/gui.log).
- Agent `interesting-sockeye` deployed through the GUI to `ssh sockeye`, home /scratch/st-shallam-1/txyliu/msm_e2e/run-4-sockeye, slurm preset, slurmAccount st-shallam-1.
- engcyc_prep_references_lite set up through the GUI (workflow perfect-alligator, run UnyqV, task ShUeUoct): COMPLETED 03:20 on 2026-11-27 (~162 GB of references, 10 images). Slurm jobs ran on the cluster; large downloads ran on login02.
- engcyc_metagenomics_lite: workflow ancient-cricket created in the GUI, hybrid and long cases removed, SRR9658108 entered as ENA FASTQ URLs (paired). The solve still reports "no plan", so the run was not started.
- Results: not collected. The setup run's outputs are reference databases, not analysis results, and there are no metagenomics results yet.

## Issues
- ERROR (docs/setup/gui.rst, "Start it from an empty workspace folder" / install): first launch via `mamba run -n msm_env msm gui` died with `PackageNotFoundError: werkzeug`. Worked around by launching envs/msm_env/bin/msm directly.
- AMBIGUITY (docs/setup/deployment.rst, "Set up a workflow before its first run"): the docs only name engcyc_prep_references / engcyc_metagenomics; the _lite variants exist only in the GUI template list.
- AMBIGUITY (docs/setup/deployment.rst): the real run must use the same agent and task as the setup run. The setup ran on workflow perfect-alligator, but the metagenomics run is a different workflow (ancient-cricket), so cache reuse of the references is not confirmed.
- GUESS (docs/workflows/engcyc_metagenomics.rst; template description says an SRA accession may be given in place of a read set): the GUI's sample paste box takes CSV of file paths or URLs. SRR9658108 was entered as ENA URLs (ftp.sra.ebi.ac.uk/vol1/fastq/SRR965/008/SRR9658108/SRR9658108_{1,2}.fastq.gz) from the ENA filereport; I did not find a native SRA input in the GUI.
- WORKAROUND (docs/workflows/engcyc_metagenomics.rst): read the template spec under envs/msm_env/.../vendor/templates/engcyc_metagenomics/spec.yml to learn which cases to keep (the template says delete cases with no samples and keep references).
- ERROR (GUI, engcyc_metagenomics_lite, docs/setup/gui.rst steps 2-4): after the sample sheet was pasted, the constant inputs (complete_medium.tsv, complete_medium_name, contig_study JSON, eggnog_source JSON, read_metadata JSON) lost their literal value fields and show only a column selector. The solver then reports "no given input matches" for those types, so no plan is found. Not resolved. Likely fix: upload the constants as files, or find the GUI's literal-value path.
- NOTE: 10 Slurm jobs named `rescue` (14229317-14229326) run under txyliu from /scratch/st-shallam-1/txyliu/rescue. They are not from this run and were left alone.

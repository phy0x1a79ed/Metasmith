# PROGRESS
- [x] install metasmith 0.26.2 into env msm_env (install.log)
- [x] GUI serving http://127.0.0.1:8092 (gui.log; pgrep -f "msm gui --port 8092")
- [x] agent imperial-fir deployed to ssh fir, home /scratch/phyberos/msm_e2e/run-4-fir
- [~] engcyc_prep_references setup run RUNNING via GUI: workflow righteous-beluga, run righteous-beluga-0KqRy (started 08:35 local). ~860 GB, 19 images, slurm preset.
- [ ] engcyc_metagenomics SRR9658108 via GUI (after prep finishes, same agent)
- [ ] collect results to ./results
Notes: ssh fir works. Another run's GUI (run-4-sockeye) on 8091, not mine.
- [!] setup run righteous-beluga-0KqRy FAILED (ConcurrentModificationException in Orchestrator, nxf.log on fir). Retrying once via GUI.
- [~] engcyc_metagenomics workflow "saffron-sturgeon" being configured in GUI: hybrid+long cases deleted, short kept. read_pair row needs type ncbi::sra_short_read_accession + SRR9658108; read rows removed.
- [!] retry #1 (run 6q5pn) FAILED: NPE in Orchestrator._closed. Failure is in Nextflow orchestrator close handler on fir, not data.

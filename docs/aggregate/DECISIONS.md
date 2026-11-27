# Aggregate — decisions

## survey — 2026-11-27

**Question.** What does "aggregated" mean when done, and in what order do the stages run?

**User's words.** "Yeah, that's basically it. Probably want to run a curation pass though and decide what was dropped or replaced, represented by, and then journal that. So, for future sessions. But yeah, I want to try and hit every tool we've ever run."

**Decided.**
- Done means: every tool the workspace has ever run is either a standard-library transform or has a recorded disposition, and every template plus the 121 IWC workflows passes a three-layer gate — solve (released solver), plan with download sizes, tiny-fixture run in Docker. A cluster run comes only after a template is green on all three.
- A curation pass comes first: a ledger of every tool ever run, each with one disposition — kept as a transform, represented by another transform, replaced by another tool, or dropped — with the reason. Journal the ledger so future sessions inherit it.
- Order: curation ledger → solve gate over templates and research roots → promote proven code (RNA-seq, phylogenetics, CoverM, MMseqs2, binners) → ML template → Galaxy ingest (codex + IWC) → generalise geoquery.

**Landed.** Survey in `SURVEY.md` (b4b2c814). This section and the stack update, in the commit that adds this file.

## curation-ledger rules — 2026-11-27

**Question.** How is each of the 209 harvested tools disposed of, and who decides?

**User's words.** "if it's in the ENGCYC template, then like that's already in. All we need to do is discuss what other tools it may be shadowing and see if that needs dropping or not." "Logistic stuff like rsync and globus, we can drop those." "You'll probably need to drop all the machine learning stuff like PyTorch, honestly, because I don't have enough experience to know what we actually need."

**Decided.**
- A tool used by a shipped template counts as in. Curation looks only at the tools it shadows.
- Logistics tools (rsync, globus, aria2, dvc) are dropped from the library.
- ML training tools (PyTorch, embedding VAEs, faiss, NMF/LDA, scGen, VEGA, sentence-transformers) are dropped for now. scikit-learn and UMAP move to `viz-set`.
- TOSICA is dropped: a human single-cell cell-type classifier.
- CONCOCT and MaxBin2 are represented by ENGCYC's binners (MetaBAT2, SemiBin2, COMEBin → DAS Tool); they survive only inside metaWRAP.
- Pilon, Racon and MUMmer are represented by OPERA-MS, ENGCYC's hybrid assembler (E5 decision 5ad5727e); they run only inside its env.
- dgbyg (with equilibrator and RDKit) belongs to the ECSPr bake, not the transform library.
- New topics: `viz-set`, `fabfos-into-std`, `lipidomics-pipeline`, `euk-transcriptomics`.

**Landed.** This section and the stack update. The ledger itself is still open.

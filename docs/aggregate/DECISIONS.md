# Aggregate — decisions

## survey — 2026-11-27

**Question.** What does "aggregated" mean when done, and in what order do the stages run?

**User's words.** "Yeah, that's basically it. Probably want to run a curation pass though and decide what was dropped or replaced, represented by, and then journal that. So, for future sessions. But yeah, I want to try and hit every tool we've ever run."

**Decided.**
- Done means: every tool the workspace has ever run is either a standard-library transform or has a recorded disposition, and every template plus the 121 IWC workflows passes a three-layer gate — solve (released solver), plan with download sizes, tiny-fixture run in Docker. A cluster run comes only after a template is green on all three.
- A curation pass comes first: a ledger of every tool ever run, each with one disposition — kept as a transform, represented by another transform, replaced by another tool, or dropped — with the reason. Journal the ledger so future sessions inherit it.
- Order: curation ledger → solve gate over templates and research roots → promote proven code (RNA-seq, phylogenetics, CoverM, MMseqs2, binners) → ML template → Galaxy ingest (codex + IWC) → generalise geoquery.

**Landed.** Survey in `SURVEY.md` (b4b2c814). This section and the stack update, in the commit that adds this file.

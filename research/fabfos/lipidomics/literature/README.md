# Lipidomics / metabolomics SOTA — curated literature

A ~33-paper corpus assembled for the **scadc/lipidomics** scope to ground a discussion of state-of-the-art untargeted lipidomics / metabolomics workflows, with a specific focus on whether per-feature MS2 library annotation can be sidestepped via unsupervised feature clustering + cluster-level classification + cluster-level differential abundance. The corpus is the input to a planning conversation; it does **not** carry a recommendation.

- **Discussion briefing (the actual deliverable):** [`../../../.awm/data/ai/lipidomics_sota_review.md`](../../../.awm/data/ai/lipidomics_sota_review.md) — synthesizes the corpus into a hypothesis answer, per-bucket synthesis, adversarial checks, tradeoff matrix (no winner), discussion prompts, open questions.
- **Raw deep-research output (claim log):** `../../../.awm/data/ai/lipidomics_sota_review.raw.json`
- **Index of papers:** [`index.md`](index.md) — citation, DOI, bucket, one-line rationale.
- **BibTeX:** `bibliography.bib` — emitted by `scripts/build_bib.py` from `search/final_corpus.tsv` (deferred — see "Build status" below).
- **PDFs:** `../../../.awm/data/literature/pdfs/` — deferred (see Build status).
- **Search record:** `search/candidates.tsv` — 33 rows merged from the deep-research workflow + foundational additions.

## Scope

- **In:** untargeted LC-MS metabolomics + lipidomics SOTA 2024–2026; molecular networking (GNPS / FBMN / IIMN / MolNetEnhancer / MCN); MS2 substructure clustering (MS2LDA, NPClassifier, ClassyFire); SIRIUS pipeline (SIRIUS / CSI:FingerID / ZODIAC / CANOPUS / MIST / MS2Lipid); lipid-specific tools (LipidBlast / MS-DIAL); ion-mobility / timsTOF / PASEF / CCS (Meier, Vasilopoulou, Ross 2023, AllCCS, CCSbase); cluster-level statistics (ChemRICH, mummichog, MetaboAnalyst); MS1 ion-grouping (CAMERA, RAMClustR, khipu); E. coli phospholipid composition reference (Sohlenkamp & Geiger).
- **Out:** targeted lipidomics / SRM-MRM methods; proteomics-only PASEF; plant / mammalian lipid pathway-specific reviews unless they ground a cited method.
- **Sample-type ceiling:** the corpus is dominated by human plasma / NIST reference benchmarks. Microbial bacterial lipidomics on timsTOF DDA-PASEF has *no surveyed direct benchmark* — flagged in the briefing.

## Search strategy

"Reviews first, then fan out from citations" — same template as the `projects/scadc/literature/` betweenness corpus.

- **Phase A (anchor reviews + verified findings):** executed via the `deep-research` skill, run id `wf_3f09963d-bac`. 108 subagents, 5 search angles, 26 sources fetched, 117 claims extracted, 25 claims adversarially verified (22 confirmed, 3 killed), 13 findings retained. Output: 22 primary-quality sources with DOIs ✓ in `search/candidates.tsv` (column `cited_by_reviews = DR`).
- **Phase B (foundational primaries the search underweighted):** added by hand from the user's original bucket list — MS2LDA / SIRIUS / CSI:FingerID / ZODIAC / ClassyFire / NPClassifier / Spec2Vec / MS2DeepScore / MIST / CAMERA / RAMClustR / mummichog / MetaboAnalyst / GNPS / Vasilopoulou / PASEF / AllCCS / CCSbase / LIPID MAPS shorthand / Sohlenkamp. Marked `cited_by_reviews = manual` in candidates.tsv.

## Layout

```
research/fabfos/lipidomics/literature/
  README.md            ← this file
  index.md             ← curated 33-paper table, grouped by bucket
  bibliography.bib     ← BibTeX (deferred)
  search/
    candidates.tsv     ← 33-row merged candidate pool (DR + manual)
    abstracts.tsv      ← fetched abstracts (deferred — run scripts/fetch_abstracts.py)
    final_corpus.tsv   ← curation output (deferred — run scripts/select_corpus.py)
    pdf_status.tsv     ← PDF status (deferred — run scripts/fetch_pdf.py)
  scripts/
    fetch_abstracts.py       ← Crossref + PMC + PubMed
    fetch_abstracts_retry.py ← PubMed retry
    fetch_abstracts_s2.py    ← Semantic Scholar + OpenAlex final pass
    select_corpus.py         ← curates final_corpus.tsv + selection_notes.md
    fetch_pdf.py             ← PMC → Unpaywall → bioRxiv
    fetch_pdf_retry.py       ← Europe PMC + publisher-landing fallback
    build_bib.py             ← emits bibliography.bib + index.md (lipidomics band names need to be edited)
```

Scripts are copied verbatim from `projects/scadc/literature/main/literature/scripts/`. The `build_bib.py` script has betweenness-corpus-specific band names hardcoded (`review`, `methodology`, `biological`, `bipartite`); when running it for the lipidomics corpus, edit lines 60-66 to use the lipidomics buckets defined in `index.md` (e.g. `review`, `networking`, `annotation`, `imms_lipidomics`, `statistics`).

## Build status

For this round, the user requested a discussion-ready synthesis — no commitment, no PoC. Highest-value deliverable is the synthesis briefing at `.awm/data/ai/lipidomics_sota_review.md`, which is already complete and stand-alone.

| Step | Status | Notes |
|---|---|---|
| Phase A — anchor reviews via deep-research | done | Workflow `wf_3f09963d-bac` |
| Phase B — fan-out to method/tool papers | done | Manual additions for buckets the search underweighted |
| Phase D — corpus structure assembled | done | `candidates.tsv` + `index.md` + `README.md` |
| Phase E — synthesis briefing | done | `.awm/data/ai/lipidomics_sota_review.md` |
| Abstract fetching (`scripts/fetch_abstracts.py`) | deferred | Briefing's evidence quotes already grounded in primary sources via deep-research; abstracts useful for paper writing but not for discussion |
| PDF fetching (`scripts/fetch_pdf.py`) | deferred | Same reasoning; can be batched later |
| BibTeX generation (`scripts/build_bib.py`) | deferred | Requires editing band names for lipidomics buckets |

To complete the full corpus build later, in order: `cd projects/scadc/lipidomics/research/fabfos/lipidomics/literature && python scripts/fetch_abstracts.py && python scripts/fetch_abstracts_retry.py && python scripts/fetch_abstracts_s2.py && python scripts/select_corpus.py && python scripts/fetch_pdf.py && python scripts/fetch_pdf_retry.py && python scripts/build_bib.py` — same pipeline as the betweenness corpus.

## Provenance

- Discussion briefing authored 2026-06-09 against scadc/lipidomics session #407 (MSDIAL first-pass sparse output, 0/143 features annotated).
- Deep-research workflow `wf_3f09963d-bac` executed 2026-06-09, ~13.6 min wall, 108 subagents, 2.6M tokens.
- 3 claims killed during adversarial verification (see briefing §3.5).
- 1 known survey gap: bonus bioRxiv 2025–2026 DDA-PASEF lipidomics sweep was not separately completed; flagged in briefing §6.

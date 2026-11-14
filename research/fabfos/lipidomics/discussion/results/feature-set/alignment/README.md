# results/feature-set/alignment

## Purpose & Contents

The result of the alignment topic: how the project builds its own ion tables from the raw runs, then lines ions up across samples into a common table.

## Decisions so far

- Build the raw per-injection ion tables first, before alignment.

> maybe, lets first create the raw feature table for alll samples/replicates. how many tables?

- 136 tables: 68 injections per polarity (48 biological, 12 blanks, 8 pooled QC). The facility table holds only 6 of the 8 QCs.
- Detect ions with MZmine 4. Keep its `.mzmine` project as the full record.

> .mzmine holds all right? lets start with that

- Derive working files from the project for analysis.

> then we would coupled files that let's us actually work with the data... 1 or a series of paraquets?

## Proposed working layout (awaiting confirmation)

- Partitioned Parquet datasets keyed by polarity and injection: `ions/` (scalars, one row per ion) and `traces/` (long format: `ion_id, kind, x, y`), plus one `injections.parquet` of sample metadata.
- MS2 spectra also exported as MGF.

## First MZmine trial (2026-11-13)

`mzmine/batches/per_injection_v0.mzbatch` on `QC 2 P` (POS), template settings untuned:

- Reads Bruker `.d` directly. 48 s wall, 2.3 GB peak RSS. Import is 36 s of that.
- 1620 ions. 1034 carry MS2. Charge 1: 1202, charge 2: 6, unassigned: 412. CCS on 1133.
- RT 0.64–6.06 min. m/z 168–1762. Median height about 25k.

## QC check and full per-injection run (2026-11-14)

> run the 8 QC, then move on to all, can you use sockeye?
> confirm the objective is to match up ions across all samples right

- Objective confirmed: one common table, ions matched across all 136 injections. Per-injection detection is step one; drift correction, matching and gap-fill follow.
- Ran locally, not on sockeye: the 98 GB upload outweighs a 26 min local run, and sockeye `/scratch` is 97% full.
- Fixes: `/tmp` is a 16 GB tmpfs and parallel `-memory none` runs filled it (SIGBUS on import), so each run now gets its own on-disk temp dir. The chromatogram builder's polarity filter was `+`; set to `Any` so one batch serves both modes.
- QC (8 per polarity): CUDA found in every QC, RT 0.802–0.814 min, mobility stable. Pairwise ion match within a fraction (10 ppm, 0.1 min, 3% mobility): POS P 84%, POS SN 83%, NEG P 81%, NEG SN 72%. NEG SN is the weak spot: many ions, few MS2.
- Full run: 136/136 tables, 6 parallel, 26 min. POS median 1465 ions (1097–1984), NEG median 698 (248–1447). Blanks lowest. CUDA in all 136.
- Output: `data/fabfos/runs/scadc_mzmine_per_injection_v0/` (DVC), one CSV and log per injection, with the batch copied alongside.

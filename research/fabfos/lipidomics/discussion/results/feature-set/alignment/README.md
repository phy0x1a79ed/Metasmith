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

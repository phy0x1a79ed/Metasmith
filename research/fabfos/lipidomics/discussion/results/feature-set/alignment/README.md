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

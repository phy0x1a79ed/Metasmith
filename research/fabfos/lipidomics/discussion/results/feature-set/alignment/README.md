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

The v0 batch (detection only, since folded into `per_injection_v1.mzbatch`) on `QC 2 P` (POS), template settings untuned:

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
- Output superseded by the v1 run below (same detection, ion counts identical).

## Parquet export (2026-11-14)

> paraquet export first, then matching to get a common feature set...

- `per_injection_v1.mzbatch` adds an FBMN MGF export (one merged MS2 per ion, keyed by `FEATURE_ID`) and a referencing `.mzmine` project save. Rerun on all 136: ion counts identical to v0.
- `mzmine/to_parquet.py` writes `ions/` and `ms2/` (hive-partitioned by polarity and injection) and `injections.parquet` (joined to `metadata.csv`). 149,849 ion reads; 86,614 MS2 spectra.
- Raw outputs: `data/fabfos/runs/scadc_mzmine_per_injection_v1/` (DVC, 588 MB). Parquet: `data/fabfos/runs/scadc_mzmine_parquet_v1/` (DVC, 27 MB).
- **CAUTION:** the `.mzmine` projects reference the raw `.d` paths in this worktree. They break if the raw chunk moves.
- Gap: EIC and mobilogram traces are not exported. Extract from `.d` per species window later if componentization needs shapes.

## Matching design (open)

> this bit needs a bit of thinking, since depending on the precision, we need to balence something like optimal transport with a union that actually gets new species when detected. aggregating the feature set may also let us transpose the M2 features. Essentially we should get multiple reads of ions and covariance for identification. For teh actual signal, we should just get a single abundance number (relative?) per sample, just like transcriptomics or ASV tables

- Terms: a **read** is one row of a per-injection ion table (one detected peak). A **species** is a cross-injection cluster of reads, at most one read per injection; it becomes one row of the common table. Its **centroid** is the consensus m/z, RT and mobility.
- Proposed: learn the error model (Δppm, ΔRT, Δmobility) from QC replicates against a random-pair background. Assign each injection's reads to centroids one-to-one with a "new species" cost (unbalanced assignment). Refit centroids, iterate.
- Abundance: raw area per species per injection, gap-filled from raw where undetected, with a flag. Normalization is a later choice.
- Per species: pool MS2 reads into a consensus spectrum. Componentization by covariance, co-elution and mobility comes after the table.
- Align POS and NEG separately; P and S jointly within a polarity.
- Open: error model first, or MZmine join aligner as a baseline first.

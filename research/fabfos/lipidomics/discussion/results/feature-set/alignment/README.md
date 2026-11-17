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

## Matching design

> this bit needs a bit of thinking, since depending on the precision, we need to balence something like optimal transport with a union that actually gets new species when detected. aggregating the feature set may also let us transpose the M2 features. Essentially we should get multiple reads of ions and covariance for identification. For teh actual signal, we should just get a single abundance number (relative?) per sample, just like transcriptomics or ASV tables

- Terms: a **read** is one row of a per-injection ion table (one detected peak). A **species** is a cross-injection cluster of reads, at most one read per injection; it becomes one row of the common table. Its **centroid** is the consensus m/z, RT and mobility.
- Built as `align/` (see the lipidomics README for the command). The error model comes from QC replicate pairs against a background of the same pairs shifted 1 min in RT. The match cutoff sits where the two densities cross, capped at d² = 144 (12σ). Beyond that, the QC excess is mobility conformers, not measurement error. Each injection's reads go to centroids by one-to-one assignment, with opening a new species costing the cutoff. Centroids refit until under 0.5% of reads move. Centroid pairs inside the cutoff that never share an injection merge, because MZmine splits some peaks.
- POS and NEG align separately. P and S also align separately, as the 4 observations below.

## Decisions (2026-11-16)

> ok, it looks like + and - need to be kept separate since they dont behave like 1 set (cant rel abundance norm across the aggregate). that's fine, so for each biological condition, we also have sup+, sup-, pel+, pel- observations (henceforth called the "4 obsevations").

> when we import and create our working table, we should do 1 rename and confirm it is correct as per the labels, then we can forget about it and only document it as part of the raw data.

- One feature table per observation (pel+, pel-, sup+, sup-). Relative abundance is normalized within an observation only.
- Rename once at import: `ESi300` → EPI300 and `ESCC1` → EpCC1 (the supernatant file labels). Verify against the labels, then document it only in the raw-data notes.
- Compute: nibi, not fir (offline) and not the local box. nibi scratch is wiped at the end of each batch of work.
- No gap-fill and no imputation. A zero means not detected. The ordination handles zeros three ways (below) instead of filling them.
- No normalization by OD or by CUDA. OD values are tied to the sample labels, so they would carry the suspected swap into the evidence for it. CUDA corrects extraction, not cell load.

## Outcome (2026-11-16)

- Error model per observation: σ 1.4–2.2 ppm, 0.008–0.011 min RT, 0.20–0.36% mobility. The cutoff is d² 105–116 in POS and capped at 144 in NEG.
- Matcher checks: no species holds two reads from one injection. CUDA lands in one species per observation, found in every injection. Sample reads scatter at most 1.12× the QC scatter, so the samples show no matrix widening. Reversing the injection order gives ARI 0.984–0.996.
- QC pairs share 0.79–0.81 of their species, except sup− at 0.68. sup− stays the weak observation.
- Blank filter: keep a species when its sample mean is at least 3× its blank mean. CUDA fails this filter by design, because it is spiked into the blanks too. Kept: pel+ 3100, pel− 1642, sup+ 2262, sup− 2799.
- Size factors (median of ratios to the QC median) span 0.78–1.44 across samples. OD spans 0.1–0.8. Comparing them waits for the biology stage.
- Zero handling, all drawn: A floors every value at the most dilute sample's detection floor and takes CLR against the core. B takes CLR on the core alone, the species found in all 24 samples. C replaces zeros multiplicatively, then takes CLR. The supernatant cores are small (sup+ 44, sup− 36).
- The variants disagree in geometry (PCA Procrustes disparity 0.16–0.81). Variant A's UMAP is unstable in sup− across seeds.

Where EpCC1 ctrl r2 falls, as the group whose replicates sit closer on average:

| observation | A | B | C |
|---|---|---|---|
| pel+ | EpCC1 ctrl | EpCC1 ctrl | EpCC1 ctrl |
| pel− | EPI300 ctrl | EPI300 ctrl | EPI300 ctrl |
| sup+ | EPI300 ctrl | EPI300 ctrl | EPI300 ctrl |
| sup− | EpCC1 ctrl | EPI300 ctrl | EPI300 ctrl |

- Verdict: mixed. The supernatant and pel− lean towards a swap with EPI300 ctrl, and pel+ fits the recorded label. The pel− margins are small.
- Deferred to the biology stage: marker-ion load estimates, the OD-to-replicate mapping, the size-factor-against-OD check, and a per-cell table.

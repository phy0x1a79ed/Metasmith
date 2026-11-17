# SCADC lipidomics: four observation feature tables and an unsupervised view

## Context

We have per-injection ion reads for all 136 injections in Parquet. They are not matched across injections yet. This plan builds one ASV-like feature table per observation (pel+, pel−, sup+, sup−). It then draws PCA and UMAP of the 24 biological samples, one panel per observation. The plots are data-driven evidence for or against the suspected EpCC1 ctrl rep 2 swap, for the Armando consult.

## What you said

> We have 8 biological conditions (the 4 cell types x 2 conditions: ctrl/tol). Using your proposed methods utilizing, please establish a unified table for each of the 4 observations (1 table per observation) that is analogous to an ASV count table. These should include an ID vs relative abundance but each feature (ion) should also have the list of MS features that could be used later to tease out presence of likely metabolites. This can be 2 files for QoL

> please then do some unsupervised visualization, ie PCA and UMAP for all samples x replicates [...] this will be the deliverable, please create in artifact. artifact can be completely empty aside from the 2 figures. no need for text, title, figure legend, etc, but please have a light/dark mode toggle button (using icons).

> can try zero = not detected but please plan a contingency and do it directly in this round. I want to avoid gapfill and imputation. Is there a way, like some normalization that enables numeric representation of near/below threshold of detection?

> the objective of these plots is to present data-driven evidence of the swap, so label as is, but with typo corrections (ESCC1, etc -> EPI300, etc.)

> show blanks dropped, but please keep the raw pre-filtered feature tables. Im guessing we will also get feature tables for the QC and blank runs?

> when we import and create our working table, we should do 1 rename and confirm it is correct as per the labels, then we can forget about it and only document it as part of the raw data.

> you may use nibi as supplemental compute and also run fast but still compute intensive jobs locally. You may use sonnet medium subagents to help with concrete tasks and work in parallel.

> we cant use CUDA since this doesnt let us normalize against cell concentration. What makes this worse is that we have OD values becuase the experimenter didnt dilute to the same density. We cant use the OD values because of the suspected switch.

> lets just draw all, so 3 sets of the 2 figures
> will need labels now, so some text in artifact

> ok, points 2 and 3 defer to later for analyzing biology then.

> scratch is scratch though so prepare to clean up and basically delete everything when done

## Issues

- I1. Reads are not matched across injections, so no injection-by-feature table exists.
- I2. The supernatant file labels spell two strains differently (`ESi300`, `ESCC1`), and the pellet labels use `Epi300`.
- I3. Undetected cells are zero, and a log transform or a ratio cannot use a zero directly.
- I4. Blank-level background ions sit in the reads alongside biological ions.
- I5. No figure shows how the 24 biological samples group without their labels.

## High-level goals

- G1. Get one ASV-like table per observation: a feature ID against relative abundance in every sample, plus the MS features that describe each ion.
- G2. Label every sample once, correctly, and never think about the file spellings again.
- G3. Handle near and below detection values honestly, without gap-fill or imputation.
- G4. Show, without supervision, whether the samples group by strain and treatment, and where EpCC1 ctrl rep 2 falls.

## Acceptance criteria

- A rename table maps every file label to one of EPI300, EpCC1, Clone1, Clone2. Each observation then holds exactly 3 replicates of each of the 8 conditions, plus 4 QCs and its blanks. The import refuses to continue otherwise.
- Each observation has four files in one DVC chunk `data/fabfos/runs/scadc_feature_tables_v1/<obs>/`:
  - `abundance_raw.parquet`: species × every injection (samples, QCs, blanks), raw area, 0 = not detected, no filter.
  - `abundance_rel.parquet`: blank-filtered species × samples and QCs, relative abundance (columns sum to 1).
  - `abundance_scaled.parquet`: the same species × samples and QCs, divided by a median-of-ratios size factor. The size factors go in a per-injection table.
  - `features.parquet`: one row per species: centroid m/z, RT, mobility, CCS, their spreads, charge, read count, detection counts per sample group, blank ratio and filter flag, isotope pattern, and pooled MS2 (merged spectrum plus contributing read IDs).
- No normalization uses OD or CUDA. OD is tied to sample labels, so it would carry the suspected swap into the evidence for it. CUDA corrects extraction but not cell load.
- No species holds two reads from one injection.
- CUDA lands in one species per observation, detected in every injection of that observation.
- QC reproducibility after matching is at least the pairwise read-match rate from the earlier check (72–84%).
- The artifact holds 3 sets (zero-handling variants A, B, C) of 2 figures (PCA, UMAP). Each figure has 4 panels (one per observation) of 24 dots. Text is limited to labels: set names, figure names, panel names, axis titles, and one shared legend for strain and treatment. An icon light/dark toggle is included. A check / QC results section at the bottom lists each check below with its value and a pass, flag or fail mark. EpCC1 ctrl rep 2 is labelled as recorded, with the spelling fix only.
- Variants: A = CLR against the core-feature geometric mean, values censored at a common floor. B = CLR on core features only. C = CLR on all features with multiplicative replacement of zeros. The check report gives core size, Procrustes agreement between variants, and EpCC1 ctrl rep 2's nearest neighbours per variant and observation.
- nibi scratch holds nothing from this work at the end.

## Tasks

- T1. Build the import with the single rename and its check (G2)
- T2. Fit the error model from the QC replicates (G1)
- T3. Build the matcher and write the raw tables (G1)
- T4. Commit a checkpoint
- T5. Compact
- T6. Filter blanks, normalize, and write the relative tables and feature files (G1, G3)
- T7. Ordinate under three zero-handling variants (G3, G4)
- T8. Build and publish the artifact (G4)
- T9. Compact
- T10. Simplify
- T11. Draft the doc updates
- T12. Debrief

## Approach by task

### T1. Build the import with the single rename and its check

New `research/fabfos/lipidomics/align/load.py` reads `scadc_mzmine_parquet_v1` and `metadata.csv`. It holds one rename map: `ESi300`, `Epi300` → EPI300, `ESCC1` → EpCC1. It derives `observation` (pel+, pel−, sup+, sup−) from fraction and polarity, and a `sample_id` such as `EPI300_ctrl_r1` that is shared across the 4 observations. It asserts the design counts from the acceptance criteria and stops with the offending rows if one fails. I print the rename table once for you to confirm.

Removes: none. New code.
Gotchas: the blanks have no strain, and supernatant blanks come in ctrl and tol. QC and blank `sample_id`s must stay unique per injection. `metadata.csv` spells polarity in lower case, and the Parquet partitions use upper case.

### T2. Fit the error model from the QC replicates

Same package, `align/errors.py`. Steps:
1. Shift each injection's RT by its CUDA offset from the median CUDA RT.
2. For each QC pair in one observation, take mutual nearest reads inside a wide window (50 ppm, 0.3 min, 10% mobility).
3. Fit robust spreads (MAD) of Δppm, ΔRT and Δmobility %. Let the m/z spread grow at low intensity if the data show it.
4. Build the background from the same pairs with one side's RT shifted by a fixed 1 min.
5. Set the match cutoff on the scaled distance d² where the true-match density equals the background density.

The fitted spreads and cutoff go into a small JSON per observation, next to the tables.

Removes: none.
Gotchas:
- A mutual-nearest pair inside a wide window can still be a wrong match. Fit the spreads robustly, not by standard deviation.
- NEG supernatant matched worst (72%), so expect it to have the widest spread.
- The spread between samples may be wider than between QCs (matrix effects). T3 checks this.

### T3. Build the matcher and write the raw tables

`align/match.py`, run per observation over all of that observation's injections. Steps:
1. Seed the centroids from the injection with the most reads.
2. For each injection, solve a one-to-one assignment of its reads to the centroids (`scipy.optimize.linear_sum_assignment` on the sparse candidate costs). A dummy "new species" column costs the T2 cutoff. Unmatched reads found new centroids.
3. Refit the centroids (intensity-weighted median) and re-run the assignment until fewer than 0.5% of reads change.
4. Merge centroid pairs that fall within the cutoff and never co-occur in one injection. This catches peaks that MZmine split.
5. Write `abundance_raw.parquet` and a read → species map.
6. Report the spread of sample reads around their centroids against the QC spread.

Runs locally: about 150k reads over 4 independent observations takes minutes. nibi stays a fallback if the iteration is slow. In that case, run one container job per observation and wipe scratch at the end.

Removes: none.
Gotchas:
- Assignment order can bias the centroids. The refit loop absorbs most of this. Check stability by running a second seed order on one observation.
- A species detected only in blanks still belongs in the raw table.

### T4. Commit a checkpoint

Commit `align/` and the T1–T3 outputs pinned as a DVC chunk. Push to `origin fabfos/lipidomics`, with code and pins only.

### T5. Compact

Handoff:
- On disk: `align/` modules and `scadc_feature_tables_v1/<obs>/abundance_raw.parquet`, plus the error-model JSONs.
- Not recoverable by re-reading: your choices of 4 panels, zeros handled by 3 CLR variants (A floor, B core-only, C multiplicative replacement) all drawn, labels-only text plus a checks section, as-labelled with the spelling fix, blanks dropped but raw kept, no OD or CUDA normalization (deferred to biology). Also the per-observation cutoffs and the QC spread vs sample spread finding.

Follow-up: "continue with T6".

### T6. Filter blanks, normalize, and write the relative tables and feature files

`align/tables.py`:
- **Blank filter:** keep a species if its mean raw area across the observation's samples is at least 3× its mean across that observation's blanks. Record the ratio and the flag in `features.parquet`, and keep every species there.
- **Relative abundance:** divide by each injection's total over the kept species, for samples and QCs. This is the ASV-style table.
- **Size-factor scaled:** divide each injection by its median-of-ratios size factor sᵢ. Compute sᵢ as the median, over the kept species detected in both, of the injection's area divided by that species' median area across the observation's QCs. sᵢ uses no labels and no OD, so it cannot inherit a swap. It is also a data-derived estimate of how much material the injection held. Write `abundance_scaled.parquet` and keep sᵢ in a per-injection table.
- **MS2:** pool each species' reads from `ms2/` into one merged spectrum. Bin at 10 ppm, take the max intensity, keep peaks present in at least 2 reads (or the single spectrum when only 1 read exists). Keep the contributing read IDs.

Removes: none.
Gotchas:
- After the blank filter, the totals change. Normalize after filtering, never before.
- A merged spectrum from reads of different collision energies stays one spectrum here. The collision energies are kept as a list.

### T7. Ordinate under three zero-handling variants

`align/ordinate.py`, per observation, on the 24 samples only (QCs and blanks out of the plots). All three variants use CLR, which cancels any per-sample load factor. They differ only in the zeros.

- **Core:** the features detected in all 24 samples of the observation. Report the core size first. A small core makes A and B noisy.
- **A. Floor-CLR.** Divide by the median-of-ratios size factor sᵢ, used only to put the per-sample floors on a common footing. The common floor is the highest per-sample floor (1st percentile of detected areas / sᵢ), which comes from the most dilute sample. Censor every value below it to the floor, detected or not. This is the rarefaction analogue. Take CLR against the geometric mean of the core features.
- **B. Core-only CLR.** CLR on the core features alone. There are no zeros at all.
- **C. Standard baseline.** CLR on all blank-filtered features, with zeros replaced multiplicatively (half the per-sample minimum, non-zeros rescaled to keep their ratios).

For each variant and observation, run PCA (sklearn, mean-centred) and UMAP (umap-learn, `n_neighbors=5`, fixed seed). Write the coordinates and a check report with:
- core size per observation,
- PCA variance explained,
- Procrustes agreement between each pair of variants,
- EpCC1 ctrl rep 2's nearest neighbours, and whether it falls in the EpCC1 ctrl or EPI300 ctrl group, per variant and observation,
- the variant A UMAP under 3 seeds.

Removes: none.
Gotchas:
- UMAP on 24 points is unstable. Check that the picture holds across 3 seeds before publishing.
- Sparse toluene-diluted samples can shrink the core. If the core falls below about 50 features in an observation, flag it in the report rather than silently loosening the definition.

### T8. Build and publish the artifact

Load `artifact-design` first (via the quickstart). One HTML page with 3 sets of 2 figures: variant A, B and C, each with a PCA figure and a UMAP figure. Each figure is a 2×2 grid of observation panels. The data is inlined.
- **Text is labels only:** set names (variant name), figure names (PCA, UMAP), panel names (pel+, pel−, sup+, sup−), axis titles (with variance explained on PCA), and one shared legend.
- **Encoding:** colour is strain (4 hues), marker is treatment (circle ctrl, triangle tol). Hover shows the `sample_id`.
- **Theme:** an icon toggle (sun/moon) switches light and dark, and the plot colours follow it.
- **Drawing:** Plotly from a pinned CDN version.
- **Check / QC results section** at the bottom, itemized, one row per check with its value and a pass, flag or fail mark:
  1. Design counts after the rename: 3 reps × 8 conditions, plus 4 QCs and the blanks, per observation.
  2. Error model per observation: spreads (ppm, RT, mobility %) and the match cutoff.
  3. Sample-read spread around centroids against the QC spread (the matrix-widening check).
  4. No species holds two reads from one injection.
  5. CUDA in one species per observation, detected in every injection.
  6. QC reproducibility after matching, against the earlier pairwise rate (72–84%).
  7. Species counts per observation: raw, after the blank filter, core.
  8. Procrustes agreement between variants A–B, A–C, B–C per observation.
  9. Variant A UMAP stability across 3 seeds.
  10. EpCC1 ctrl rep 2: nearest neighbours and group (EpCC1 ctrl or EPI300 ctrl), per variant and observation.

Subagent split, Sonnet at medium effort, in parallel once T7's coordinate files exist:
- One agent builds the HTML page and toggle from a coordinate-file contract.
- I review the page and publish it.

Gotchas:
- Plotly needs its layout colours swapped on toggle, not only the page CSS.
- Phone width needs the 2×2 grid to stack to one column.
- The checks section is a generated table, built from the T1–T7 check outputs, never typed by hand.
- Six 4-panel figures is 24 plots. Keep the page fast by drawing each figure as one Plotly subplot figure, not 24 separate ones.

### T9. Compact

Handoff: the artifact URL and the T7 check-report verdict (do A, B and C agree on EpCC1 ctrl rep 2). Follow-up: "continue with T10".

### T10. Simplify

Run the `simplify` skill over `align/` and the artifact source. The target behaviour: four observation tables plus one ordination page, from the Parquet set, in one command.

### T11. Draft the doc updates

- Lipidomics `README.md`: add the feature-table chunk and the one-line raw-data note on the rename.
- `alignment/README.md`: add the outcome (the matcher as built, the cutoffs, and the swap verdict from the plots).
- Point the `mzmine/README.md` reruns at nibi, not the local box.

### T12. Debrief

Run the `debrief` skill. Confirm nibi scratch is empty, since nothing in this plan should land there unless T3 falls back.

## Callouts

- Deferred to the biology stage: marker-ion load estimates, the OD-to-replicate mapping, the sᵢ-vs-OD check, and the per-cell table.
- The matcher runs locally. It is light (minutes over 27 MB), within your "fast but compute-intensive locally" allowance. nibi is used only if a step turns out slow.
- QC and blank columns appear in `abundance_raw.parquet` for every observation. QC columns also appear in `abundance_rel.parquet`. Blanks are dropped from the relative tables and from the plots.

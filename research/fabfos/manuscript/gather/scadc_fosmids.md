# SCADC fosmids: where the results stand (research report, 2026-10-18)

Paths are relative to the scope worktree
`/home/tony/agentic_workspace/projects/metasmith/fabfos/scadc` (called SC below)
unless given in full. "J:xxxxxxxx" is a journal id; read the full entry with
`search get` / `journal fetch post_id=`.

## Bottom line

- The canonical insert set is **170 inserts**. The other counts are earlier
  generations of the same recovery (see 1a).
- **No ECSPr run carrying a null supports "clone 2 preferentially raises carbon
  conductance towards lipids."** On the deployed r10 bake no insert clears its
  size-matched null on glucose-to-biomass carbon, and clone 2 ranks 25 of 170 at
  z 0.55. The sketch's lipid claim traces to earlier capella work on the retired
  132-clone set, and parts of that work were retracted there.
- Lipidomics is independent evidence and is untouched by the above; what is gone
  is ECSPr's corroboration of it.

## 1. Pipeline inventory

### 1a. Insert recovery: which count is which

| count | what it is | provenance | status |
|---|---|---|---|
| **132** | legacy `C0xx` clones: 938 contigs >=10kb -> 197 clusters@0.99 -> 199 dedup -> 132 inside the 29-44kb lambda window; 4,635 ORFs | capella `scadc` (recover-fosmids / fig-resolve); J:4c5ae525, J:9306bd08 | retired; ids map to nothing current, ORF FASTA only on fir. All capella CFBC/ESPER work to mid-July used it |
| **199** | the same legacy run before the lambda-window cut, under a different identity metric | capella `fabfos_2026` run | retired; several figures in `figures/data/figures/latest/` (circos, ORA/GSEA, `ECSPr_signal_heatmap.v2_CLEAN_199`) are drawn on it |
| 157 | first metasmith recovery, silhouette-swept cut (identity 0.579) | fabfos `dev-resolve` 2026-07-27, J:4e72e8d9 | rejected: costs ~10% of clones (`research/fabfos/clustering_sweep/RECALL.md`) |
| **183** | identity-0.99 cut of that recovery: 287 pieces -> 183 inserts, 6,064,622 bp, 5,892 ORFs; first 7-lane annotation (Aug 6) | J:ebf56118, J:9306bd08 | superseded; still the basis of the union-183 concept networks and the 2026-08-04 tier4 ECSPr null |
| **170** | **canonical.** Same 0.99 cut after similarity moved to summing non-overlapping HSPs and the absorb pass became closure-aware: 272 clusters absorb to 170 | `data/fabfos/runs/scadc_fosmids/sequences/inserts/inserts.fna` (170 records; `mapping_reference.fna` has 171 because it adds pCC1fos) | the GPR tables were retargeted onto it and it is the r10 ECSPr input |

Checks I ran on the 170 set (`insert_metadata/inserts.csv`):

- junction counts are exactly **107 / 47 / 16** for two, one and no junctions,
  matching the sketch;
- lengths 10,139 - 76,522 bp, median 34,552;
- `research/fabfos/figures/inserts/pieces.py --verify` re-derives all 170
  centroids exactly (inserts README).

**Caveat on ">96.4% of reads".** The mapping reference is the inserts *plus* the
pCC1fos backbone. `sequences/insert_coverage/pool_summary.tsv` gives per-pool
mapped fraction 0.9624 (pool01_GTAACGAC, day 6) to 0.988, so ">=96.2%" is exact
and 96.4% holds only if that pool is excluded. Inserts alone take 79-85% of
host-depleted reads (183-set measurement, J:ebf56118); the backbone row is a
seventh to a fifth of each pool's aligned bases (inserts README, "Three things to
say when reporting these").

35 read sets come from 33 pools: pool 01, the day-6 founder, was plated as three
barcodes.

### 1b. Selection dynamics

From `pools/pool_lineage.csv` and `sequences/insert_coverage/insert_coverage_matrix.tsv`
(I recomputed the per-pool composition):

- **Design**: a branching serial passage, days 6, 11, 19, 23, 33, 42; one arm
  without vitamins (pools 02-16) and one with (pools 17-33).
- **Clone 2** = `pool33_TTGTCGGT:spades:NODE_1_length_52418_cov_24948.204228:1211-45739`
  (44,529 bp, both junctions, 39 ORFs). It dominates **16 of 35** read sets at
  >90% of insert bases (`dominant_clone.py`, J:98f5e877): every vitamin-arm pool
  from day 19 on, plus the pool04 branch of the vitamin-free arm.
- **Clone 1** = `pool14_ATGCCTGT:megahit:k141_67:6979-38390`. It takes over only
  the pool03 branch of the vitamin-free arm (pools 05, 07, 09-11, 13-15) and is
  never above 0.1% in any vitamin pool. This matches the standing capella
  confound that clone 1 may be winning on vitamin prototrophy (riboflavin/GTP;
  J:0d3c0e21).
- **Long-read confirmation**: I re-ran the clone-to-insert blast. Plasmidsaurus
  `L9PH9L_2_SCADC_C2_D19_2_wellA1` is **clone 1** (31.2 of 39.4 kb aligned to the
  pool14 insert) and `L9PH9L_1_SCADC_C1_D19_3_wellD4` is **clone 2** (tandem-dimer
  record, 86 kb aligned to pool33 NODE_1). The file names are swapped relative to
  clone numbering; `research/fabfos/figures/inserts/clone_alignment.py` encodes the
  correct mapping and identifies each clone by alignment, reporting 100% coverage
  of both.
- Inserts README: 28 of 33 pools are more than half one insert, and the two clones
  dominate 25 of those 28. The earlier figure drew one clone as six wedges; the
  dedup fix is what collapsed it.

### 1c. Annotation lanes and GPR tables

`gpr/gpr_4lane.parquet` - 63,914 rows, 5,388 ORFs, 12,637 MNXR, 170 `genome_unit`s.
Rows per channel: CLEAN 53,619, ProteinBERT 7,496, KofamScan 1,941,
**UniRef50 858**. The sketch says UniRef90; every shipped fosmid and metagenome
table uses **UniRef50** (UniRef90 exists only under `annotation_alts/`).

`gpr/gpr_7lane.parquet` - 81,636 rows, 5,395 ORFs, 13,143 MNXR, adding ESM-C
(15,322), EZpred (2,260) and DeepEC (140 - thin by nature, 19 ORFs).

Unit attribution: since commit `038bb281` each insert is its own `genome_unit`,
which raised E on 7,920 of 12,637 reactions (4-lane) and 8,243 of 13,143
(7-lane), every move upward, by up to 0.731. Earlier tables pooled all 170 as one
anonymous copy, so no number crosses that boundary.

Metagenome side: `runs/scadc_metagenome/gpr/gpr_4lane.parquet`, 19.7M rows over
1,438,372 ORFs, same four lanes - this is the null pool.

Lane benchmarking lives in `metasmith/fabfos/annotations`: the seven-lane
precision/recall ablation is **not started** there; the pbert refusal knob is done
(P 0.899, coverage 0.849 on DH10B). The original ablation is on capella, project
`scadc`, scope `fig-annotate`.

ORA/GSEA (sketch: signalling and regulation; only BRITE-level-2 transcription
factors significant) is capella-side, on the legacy 199/132 basis. I found no ORA
or GSEA artifact in the metasmith tree.

### 1d. ECSPr runs on the fosmids

**The current run** - `data/fabfos/runs/scadc_fosmids/ecspr/` (13 files, DVC
pinned at `2f5c835a`), account of record `PROVENANCE.md`, drivers
`research/fabfos/examples/scadc_ecspr_basis.py` and `scadc_ecspr_arm.py`,
debrief J:162b8687.

- Bake **r10** (identity `0ffd4c8c...:554b4d8f...`), the first generation whose
  direction ratio is `exp(dG'/RT)` against measured E. coli concentrations.
- Readout: one condition per insert, host GEM rows plus that insert's rows;
  glucose `MNXM1364061` injected, four biomass hubs (acetyl-CoA, malonyl-CoA,
  oxaloacetate, AMP) merged into one ground; `total` is the effective conductance
  of the whole glucose-to-biomass carbon path. Host baseline **1.94037893**.
- 171 observed solves, 26,000 null solves, all converged, conservation at machine
  epsilon.
- Two nulls, 1,000 draws per ORF-count stratum each, from the metagenome 4-lane
  table: **A** uniform over the 1.44M-ORF inventory (`ecspr draw`), **D**
  contiguous run on one contig (built in the arm). Strata are counted in ORFs, not
  units - `insert_sizes.parquet` gives n_orf 9-81, median 32.5, median 3.7% lost
  to the stratum match.
- **Result: 0 of 170 clear BH under either null.** Best z_stratum 3.44 (A) / 2.99
  (D) at p 0.020 / 0.030, q 0.93 / 0.95. Median insert z_stratum -0.372; 41 of 170
  above zero. Spearman between the nulls 0.995, same 41 positive, while A adds
  1.20x and D 0.94x an insert's reactions - so the answer survives a null 20% too
  hard and one 6% too easy.
- No `is_control` arms exist: all 170 reach the r10 carbon universe, so the
  noise floor is the null, not a control.
- Every insert raises the conductance by Rayleigh monotonicity, so the sign
  carries no information; only the magnitude against the null does.

**Earlier generations, for the record:**

- **2026-08-04, tier4 basis** (fabfos `dev2`, J:36e89050): 183-era tables, a
  3-lane metagenome null (a mismatch the r10 PROVENANCE names), 13 N-buckets x 2
  sampler styles x 1,000 draws. **0 of 1,464 (unit, condition, metric) rows
  survive q<0.05.** The null's mean delta_total (0.0715) exceeded the observed
  mean (0.062). Same verdict, different basis.
- Against that retired generation the r10 run shares 166 insert ids (18
  retired-only, 4 new-only), Spearman 0.63, medians ~40% lower - confounded,
  because basis and unit attribution both moved.
- The tier4 route was **retired, not repaired**: `scadc_ecspr_t1_refs.py` reads a
  pin dropped 2026-08-14, so it cannot run. All four sinks re-resolved by name to
  the same ids, which is a check passing rather than an assumption.

**The flux-balance arm** (scope `fabfos/bench-fba`, J:87768cd6, bake r11):
`data/fabfos/runs/scadc_fosmids/fba/` reads the conductance arm's own
`conditions.parquet`, so both arms measure one construction. SCADC is "a clean
negative": no insert clears BH on any of the four hubs, 6-10 of 170 clear the
size-matched p against ~8.5 expected by chance, max |z| 3.04. Two findings worth
carrying: a per-unit draw over a library *is* the library (all 170 drawn sets were
observed inserts, each 20x), and SCADC has no control arm in that arm either.

**A further 100-axis arm was built and never run to a null.** Commits `d4af58b8`,
`159eb215`, `1dfaafd4`, `27ccc6a6` (Aug 26) bring the curated `set4` axes into the
repo, extend the arm to 83 then 100 axes, and add `host_substitutions_epi300.json`.
`--gate` solves every axis on the host alone: 84 of 100 live, 16 carry nothing
(9 declared generics kept as controls, plus no MVA pathway, no lipid II and three
disconnected pairs). The full arm would be 14,193 tests and ~280 core-hours of
null. **No result chunk for it exists** - `ecspr.dvc` last moved at `2f5c835a`.

## 2. Squaring the sketch's ECSPr-lipid claim with the r10 null

**Does any shipped run test glucose -> lipid for clone 2?** No, not with a null.

- The r10 arm's only axis is glucose -> {acetyl-CoA, malonyl-CoA, OAA, AMP}. That
  is a precursor set, not a lipid. Clone 2's row in `scored_null{A,D}.parquet`:
  delta +0.0722 on a 1.94038 baseline (+3.7%), z_stratum **0.546 (A) / 0.456 (D)**,
  p_stratum 0.43 / 0.57, q 0.97 / 0.95, **rank 25 of 170**, stratum 37 ORFs. The
  three highest-z inserts are `pool01_GTAACGAC:megahit:k141_148:140-52029`,
  `pool01_ATTGAGCC:spades:NODE_11_...:51-40164` and the clone-1 insert
  `pool14_ATGCCTGT:megahit:k141_67:6979-38390`. Clone 2 is unremarkable.
- The DHAP and phospholipid axes that would test a lipid route exist only as
  declarations: `data/fabfos/curated/ECSPr_axes/biomass_dag_axes_set4_lipid_ext.json`
  adds glucose->DHAP, DHAP->PE (`MNXM115`) and DHAP->PG (`MNXM725992`) precisely
  because "AcCoA -> PE cannot carry" the backbone carbon. 17 substituted axes
  carry current on the host at C16:0 and C18:1 agreeing within 1.3x - but that is
  a host gate, with no insert and no null.
- The one clone-2 lipid-direction number that exists is a **figure**, not a test:
  `fabfos/fig-networks` (J:6a3b72ce, commit `b2c2975`, bake r9) solves
  glucose->DHAP on `gpr_epi300_clone2.parquet` (host GEM 2,290 MNXR + clone 2's
  344 MNXR). Two-terminal conductance **1.788 -> 1.958 (+0.17)**; of 1,424
  collapsed corridors 327 go up and 1,082 down, the largest riser a brand-new
  clone corridor (MNXM66 - MNXM727276, 0 -> 0.127) and the largest faller the
  host's own GAP->DHAP spine (-0.041). DHAP is the glycerol-phosphate backbone
  lipids are built from, so this is the closest thing to the sketch's sentence -
  but it has **no null, no size control and no clone-1 comparison**, and by
  Rayleigh any added evidence raises the number.

**Where the lipid claim actually came from.** capella, project `scadc`, scopes
`metabolic-modelling` and `fig-model`, on the retired 132-clone set and a
pre-bake basis:

- **J:17461aba (2026-06-14)**: C002 (the then-id for the clone 2 lineage) was
  called on cardiolipin at Z 4.24 (null A) -> 2.35 (null D), p_emp 0.010 -> 0.055.
  The entry itself frames this as a *specificity* result, not an enzyme call: C002
  reinforces neither terminal lipid reaction, and its evidence is on the shared
  glycerophospholipid plus central-carbon backbone (serA, glpK, glycolysis, PPP).
  Across all 132 clones x 5 lipid axes the FDR survivors fell 73 -> 5 -> 3 as the
  model improved; PG was eliminated entirely.
- **J:0d3c0e21 (2026-07-15)**, same scope, later: the "signal is in P/S" story was
  retracted - signal is flat across elements and 53% of significant cells are
  carbon. The composite 3PG->PE axis lifts C002 only to the 82nd percentile
  (+2.4% of g_base), while two unrelated PE clones sit 57-80x higher, because
  serine->PE carries ~87% of the route resistance. The entry's own words: this
  **"does NOT support a C002 membrane-lipid story."** It also records that the
  membrane-vs-redox temporal correlation and a p=0.032 day trend were retracted,
  and names the decider as a toluene vs no-toluene control.
- **`projects/scadc/lipidomics/main/ecspr/pg_axis_verdict.py`** retracts the
  phosphorus arm outright: the only phosphate->PG edge in the star graph comes
  from MNXR147494, where phosphate and PG are co-substrates both donating to PGP,
  so zero phosphorus moves across it and the direction is backwards as well. Its
  own summary: the lipidomics arm is independent evidence and untouched, but
  "what dies is ECSPr's corroboration of it."
- `main/ecspr/method/README.md`: "Nothing survives q<0.05 for C001/C002 on
  carbon - expected; rank by effect size."

**So:** the sketch's lipid sentence rests on a 2026-06 result that its own scope
later weakened (3PG->PE) and partly retracted (the P arm), measured on a retired
insert set, a retired basis and a star graph rather than the atom graph. The r10
null does not contradict a *lipid* claim - it never tested one - but nothing in
the current tree supports it either.

**What PROVENANCE.md says about follow-ups** (`.../scadc_fosmids/ecspr/PROVENANCE.md`,
Limits, plus J:162b8687 Next steps):

- The named next measurement is a null matched on **nominated reactions** rather
  than ORF count; the A-vs-D agreement says it is unlikely to change the answer,
  which is why it was not done.
- "A different sink set, a different element, or a phenotype other than carbon
  throughput is a different measurement" and is explicitly **not foreclosed**.
  Carbon only; N, P and S were not run.
- Read `z_stratum`/`p_stratum`, never the pooled `z`/`p_emp` (inserts span 9-81
  ORFs, so a pooled rank is largely a size rank). Empirical p floor 1/1001.
- The glycogen direction gap (MetaNetX glycogen as a fixed-formula molecule) is
  upstream and unfixed; any insert whose result turns on a glycogen reaction
  inherits it.
- `runs/e_coli_epi300/ecspr/` holds two generations at once and grades MIXED: read
  `glucose_probe_r10.parquet`, not the other three files.
- Run `research/fabfos/benchmarks/direction_rescue/scan_results_bake.py` after
  every bake promote. Note r11 has since landed in `bench-fba` and moved every
  conductance arm, so the r10 scadc numbers are one generation behind the newest
  bake.

## 3. ECSPr benchmark scopes - verdict each

Bake pins read from each worktree's `data/fabfos/processed/metabolism_bake.dvc`:
r10 for bench-eydallin / fang / woodruff / fuhrer, r9 for bench-laser / keio /
directionality*, r11 for bench-fba. Several committed reports predate the pin
their worktree now carries.

- **bench-eydallin, 2010 ASKA gain-of-function (glycogen).** 4,102 clones, 86
  hits, two-point glucose->glycogen at fold x2, measured on **r7**
  (`research/fabfos/benchmarks/eydallin/REPORT.md`). Library AUC **0.5362 below
  its own size control 0.5409**; module-struck 0.5092 vs 0.5204. Precision@10 is
  5/10 (p 8e-7) and all five are glycogen-module genes. **Fails its control** -
  the 0.5362 is a guard value, not a result.
- **bench-eydallin, 2007 Keio deletions.** AUC 0.729 (p 9e-5) library-wide, 0.656
  (p 0.012) module-struck, against controls 0.510 / 0.541; on the 23 measurable
  cohort genes AUC 0.850 vs control 0.275, signed rho +0.663 (J:7f301454). r11
  lifts it to AUC 0.917 and sign 78.3% (J:87768cd6). **Works** - the strongest
  single-cohort result. But the anabolic/catabolic ratio is significantly
  *backwards* (module-struck rho -0.679, p 0.004, J:bdc3b8c0), and the deletion and
  doubling axes rank the panel identically (rho +0.97), so the two are one
  measurement.
- **Cross-arm ratio review (J:14887784, r10).** No arm's sign agreement beats its
  own majority-class base rate: eydallin 60.9% vs 73.9% (gem) and 69.7% vs 75.8%
  (de novo). **Direction readout fails across the board.**
- **bench-fang (Fang 2025 ASKA free fatty acid).** FFA arm: AUC 0.529, rho +0.152
  against titer but **+0.69 against reaction count**. LPS inner-core axis: rfaY
  ranks 15/4,102, atom-mapped AUC 0.728 vs size control 0.319 - but under the
  waaQ-substrate control rfaY drops to 701 and waaQ climbs to 9, and with the LPS
  module struck AUC 0.388 vs 0.383 (J:4260d9e8). **Fails**: the axis ranks whatever
  catalyses the last edge into the declared sink. Only 9 of 59 genes change a
  carbon skeleton, so the phenotype's driver is outside what the probe can see.
- **bench-keio.** Three auxotroph deletions (argA, hisG, trpE) plus controls,
  universal leak over 991 metabolites, K=100 matched nulls, on tier-4 atom pairs
  rather than a bake. The required metabolite ranks 4-17 of 991, p 0.030 / 0.079 /
  0.030; argD (deletes nothing) gives p=1. **Pilot, by its own README** - finds the
  pathway, reads the end product weakly, n too small to call validation.
- **bench-fuhrer (Fuhrer 2017 deletion metabolomics, r10).** 3,806 deletions
  against 99 metabolite z-scores. ECSPr beats its size control on **76 of 99**
  (p 4.3e-8), median AUC 0.584 vs 0.492 (J:308355c1). The only deletion arm with a
  measured negative for every gene. **Works at genome scale**, but it cannot
  separate a metabolite from its one-reaction neighbour (within 0.03-0.04) and
  sign beats base rate on 8 of 99, i.e. chance.
- **bench-woodruff (Woodruff 2013 SCALEs ethanol).** Ratio C(pyr->EtOH)/C(pyr->OAA),
  both channels. Best AUC 0.5467 (p 0.15) vs control 0.5347; the only p<0.05 value
  (0.6080) loses to its control (0.6286) and collapses to 0.4338 on the
  atom-mapped subset (J:95f4d34c, J:f97146fc). **Null on all arms**; the top of the
  ranking is chemically sensible (adhE, ppc, maeB) but none is a screen hit. One
  useful by-product: the curated null was shown to be a real null rather than a
  coverage artifact.
- **bench-laser (readout conditioning, r9).** 79.1% of ASKA responses are exactly
  zero and nonzero ones span 15 decades, median 1e-6.43; 25 of the direction
  table's 28.7 decades change no answer, so a three-decade clamp is harmless. The
  direction *fit* fails: the LASER panel resolves ~5 directions and they are
  orthogonal to the labels. Its own control triple is mixed - on r9 the ASKA AUC
  is 0.5375/0.5380 (still below control) and the eydallin signed share falls to
  rho **+0.1366 (p 0.53)** from the quoted +0.395; the glgA route reallocation
  holds (0.390 -> 0.967) but changes no verdict.
- **bench-fba (ECSPr vs flux balance, r11).** One shared conditions table per
  cohort. **Fuhrer is the only arm that answers, and conductance wins**:
  0.664 curated / 0.620 de novo against controls 0.446 / 0.448, with flux balance
  at 0.496 vs 0.466 (chance, indistinguishable from its control). Every other arm
  fails its size control (eydallin 0.559/0.567, fang 0.399/0.454, woodruff
  0.532/0.529) and scadc is a clean negative (J:87768cd6).
- **directionality / directionality-scrape.** Bake infrastructure, not a phenotype
  benchmark. Tier 0 fell 47,266 -> 37,404 (r8) -> 36,151 (r9) with nothing losing a
  vote, and tier 1 went from 87% group-cancellation artifacts to none
  (`research/fabfos/benchmarks/direction_rescue/README.md`). Glycogen elongation
  still abstains at ratio 1.0 because MetaNetX carries glycogen as a fixed formula;
  r10 fixes MNXR145036 but not glgA/glgP's zero-vote abstention. Standing
  structural limit: by Rayleigh monotonicity direction evidence can mute but never
  flip a two-point sign. Remaining lever is the carrier/substitution table - 5,137
  reactions left under a ceiling near 15,460.
- **Earlier fabfos bench-aska.** J:fba912ee "ECSPr tracks reaction count, not the
  titer"; J:d7dd15af the library classifier fails once the glycogen module is
  struck; J:17e037e9 a universal leak never correlates with hop distance, which is
  why point-to-point solves are required.
- **capella pre-bake validation** (project `scadc`, `metabolic-modelling` /
  `fig-model`): edge-local specificity passes (7 of 9 literature deletions plus a
  csc gain-of-function move only their expected edge; isozyme controls silent,
  J:f0bcbb42); X/Y directional specificity AUC 0.83-0.88 (J:c35c90fc); the
  heterologous MMC route moves malonyl-CoA at q~0.007 (J:d54ad941). These show a
  perturbation reaches its own edge - they are not phenotype predictions, and the
  sketch's "ECSPr was first validated on a glycogen screening study" refers to the
  ASKA arm that later failed its size control.

**Net:** supported - ECSPr magnitude carries information beyond reaction count
*under gene deletion* (eydallin 2007 r10/r11, fuhrer 76/99 r10, and beating flux
balance on fuhrer at r11), plus edge-local specificity. Not supported - any
overexpression classifier, and any directional claim. The SCADC fosmid cohort is
an overexpression/addition cohort, which is the regime where the benchmarks are
weakest.

## 4. Manuscript-candidate figures

All 15 rendered candidates sit in one folder,
`/home/tony/agentic_workspace/projects/metasmith/fabfos/figures/data/figures/latest/`
(call it L; identical copies in the `dev`, `manuscript` and `anaerobic-digester`
worktrees), committed 2026-08-25 as `860f9d6d`, recovered from the retired
`fabfos/figure` project. The Trilium note `scadc/results/figures` links all 15 by
that path. **Most were drawn on the legacy 132/199 set.**

Insert recovery and selection
- `L/readqc_vs_assembly_grid.v3.png` - read QC vs assembly metrics. Legacy 132/199.
- `L/1_cluster_quality.v1.png` - clustering metrics vs cluster count, marks the 132 cut. Legacy.
- `L/2_identity_matrix_and_length.v1.png` - identity heatmap plus lengths. Legacy.
- `L/insert_length_violins.v11.png` - lengths by end-mapping tier. Legacy.
- `L/pool_pie_tree.v7.png` - pool lineage tree of pies. Legacy 199, and this is
  the version where one clone drew as six wedges.
- `L/clone_alignment.v6.svg` - recovered inserts vs the long-read clones. Legacy id space.
- `SC/research/fabfos/figures/inserts/{readqc_vs_assembly,cluster_quality,identity_matrix,insert_lengths,pool_pie_tree,clone_alignment,junction_table}.py`
  - the current replacements, on the 170 set. **Not rendered anywhere on altair**
  (no `cache/` in any of the 20 fabfos worktrees); the README says a cold redraw
  takes about a minute, in env `figure-net` plus `blastn` from `fabfos-bio`.

Annotation
- `L/ec_caller_upset_dh10b.v4.png` - lane-justification UpSet over 8 callers, on
  the DH10B chassis, so independent of the insert set.
- `L/figure3.postsplit199.v3.png` - tree-in-centre circos with KEGG/BRITE tracks. Legacy 199.
- `L/ORA.v1.png`, `L/GSEA_Transcription_factors.v1.png` - kofam enrichment vs the
  metagenome. Legacy 199 basis.
- `/home/tony/agentic_workspace/projects/scadc/lipidomics/figures/pbert_embeddings_kegg_clusters.svg`
  - ProteinBERT UMAP coloured by KEGG cluster, rendered 2026-08-10, set not stated.
- capella only: `02_annotate/circos/figure3.v{1,2}` (v2 = 132), `fosmid_summary.v1`
  (123 clones), `lane_justification/ec_caller_upset.v2`, an MMD-vs-nulls panel.
  Label transfer and the annotation-rate UpSet exist only as spec.

ECSPr and networks
- `L/ECSPr_signal_heatmap.v2_CLEAN_199.svg` - fosmid x 79-axis signal heatmap.
  Legacy 199 and the pre-bake negbin scorer; capella's own fig-model calls v2
  "stale, not merely superseded", with sidecars from the wrong lane.
- `L/03_chord_set4.v18.png`, `L/03_chord_set4_gof.v11.png` - LOF/GOF validation
  chords on the set4 axes, host only, pre-bake era.
- `.../fabfos/fig-networks/research/fabfos/figures/metabolic_network/cache/network_glucose_dhap{,_min,_paths_absolute,_paths_direct}.{png,svg,html}`
  plus `edge_flow_histogram.png` - the glucose->DHAP carbon network on EPI300,
  rendered 2026-08-20 on **bake r9**. Edges carry the mass-flow quota and the KCL
  cuts sum to 1.0000 exactly (J:58a5b983); the emergent widest path is
  glucose -> fructose -> F6P -> GAP -> DHAP, and G3P feeds 0.583 of DHAP's inflow.
- same cache, `network_glucose_dhap_paths_absolute_delta.{png,svg,html}` -
  delta-conductance EPI300 vs +clone 2 (`b2c2975`), r9, clone-2 id from the
  183-era table. **This is the figure closest to the sketch's lipid sentence and
  it has no null.**
- `.../fabfos/bench-fba/research/fabfos/figures/metabolic_network/cache/network_glucose_dhap_{denovo_belief,denovo_uniform,paths_absolute,paths_absolute_gem_belief}.*`
  - belief- and uniform-weighted variants, rendered 2026-08-25, probably r10.
- `SC/research/fabfos/figures/concept/*.py` - the I_eff UMAP networks (KEGG scale,
  EPI300 bipartite, union of 183 inserts, EPI300+clone2). **Caches gone** with the
  retired project; the union figure is on the superseded 183 set. Its README also
  records that masking the community solve is not the same measurement as solving
  the slice (0.58 mean agreement).
- **No figure exists on the current r10/r11 SCADC ECSPr result.** That result is
  tables only.

Lipidomics and vesicles (standalone `scadc` project)
- `/home/tony/agentic_workspace/projects/scadc/lipidomics/figures/lipids/*_metaboscape.{png,pdf}`
  (14 files) - class and chain composition, saturation, PCA, OD summary and
  mechanism, heatmap. Rendered 2026-08-10.
- `.../lipidomics/main/vesicle_panels/vesicle_{size_distribution,surface_area,threshold_sweep}.png`
  plus `overlays/`, `bakeoff/` - vesicle segmentation and quantification, 2026-08-14.
- `.../lipidomics/data/scadc/microscopy/vesicle_imaging_May_22_2026/results/vesicle_density_per_od.png`
  - headline vesicle density per OD, inside the DVC chunk.
- `.awm/data/figures/publish/04_lipidomics/01_lipid_per_cell.svg` and
  `05_clone_response/clone_response_storey_volcano_only.svg` (+ `_hits_identified.csv`)
  - the two the Trilium note `scadc/results/lipidomics` links. **Not present on
  altair**: pinned in `lipidomics/data/figures.dvc` (781 files, 718 MB) but the
  bytes are not in this node's DVC cache.

Other
- `L/prokaryotic_metabolism-workflow.drawio.svg`, `L/metasmith_diagram.svg` -
  schematics. drawio app note `scadc/prokaryotic_metabolism/aam` is a link only.
- capella publish tree: `figures-main/.awm/data/figures/publish/{01_resolve,02_annotate,03_model,04_lipidomics}`;
  03_model also holds `ecspr_validation/mmc_null_hist.v4` (WIP), `escpr_nulls/`
  (misspelled), `comparison/`.

Figure-set caveat worth carrying into the manuscript: the vesicle ranking is
threshold-stable only in the +toluene arm (pCC1 > Clone1 > EPI300 > Clone2 across
thresholds 3-40); in -toluene only "EPI300 lowest" survives, and OD600 is
cross-experiment (imaging 2026-05-22 against a lipidomics culture set 6 d
post-challenge) - J:2671f9ce, J:2a2de9a4. Three of eight conditions sit at or
below the measured detection floor.

## 5. What SCADC is, and how the metagenome relates to the fosmids

**ScaDC = Short-Chain Alkane-Degrading Culture.** A methanogenic microbial
community enriched from an **oil sands tailings pond**, shown to degrade C6-C10
alkanes under methanogenic conditions. Total DNA went through 454, Illumina
paired-end and 16S amplicon sequencing (kb `E5XA94JT`, Tan et al. 2013, *Genome*,
doi 10.1139/gen-2013-0069; companion comparative study kb `GXKQVFM6`, ISME J 2015).
NCBI BioProject **PRJNA862638** is recorded in
`/home/tony/agentic_workspace/projects/scadc/main/README.md` as the source of
`data/sequences.fasta`.

**The fosmid library** is large-insert environmental DNA from that culture, cloned
into pCC1FOS (7,930 bp backbone, 29-44 kb insert window from lambda packaging,
~30 genes per insert) and maintained in *E. coli* **EPI300** with
arabinose-inducible copy-up. That host has a curated GEM (`iECDH10B_1368`), which
is what lets an insert's reactions be added to a characterised background.

**The screen** is Kateryna Ievdokymenko's MSc thesis (UBC 2022, kb `65ZSNXQ8`,
`open.library.ubc.ca/collections/24/items/1.0417274`): a fosmid-pool selection
paradigm in EPI300 for tolerance traits. It was developed on nine libraries
against vanillin and seven lignin-derived monoaromatics, then **extended to
hydrocarbon tolerance using toluene in three pools sourced from anaerobic
hydrocarbon-degrading enrichment cultures** - SCADC among them. Recovered traits
were transport and cell-surface modification. Pool growth was unstable, which is
what prompted the time-course experiment that produced the 33 samples here. The
thesis already reports clone succession between early and late exposure phases.
Lab lineage: Strachan et al. 2014 PNAS (lignin biosensor screen, kb `JTB8V3VF`)
shares Ievdokymenko as an author.

**Two sequence layers, two roles.**

1. **The shotgun metagenome** of the SCADC culture - `runs/scadc_metagenome/`,
   1,438,372 ORFs, annotated on the same four lanes. In this study it is **the
   null pool**: every draw that an insert is scored against is N ORFs taken from
   this inventory (uniform, or a contiguous run on one contig). It is also the
   reference for the ORA/GSEA comparison in the sketch. It carries **one**
   `genome_unit` because there is no binning - its real unit would be a MAG - and
   that is exactly why the null has to be drawn on `orf` rather than on
   `genome_unit`.
2. **The fosmid pools** - 33 samples / 35 read sets, host-depleted, assembled with
   both metaSPAdes and megahit, pCC1 aligned against the assembly graph to mark
   junctions, then deduplicated at 99% identity. 170 inserts, 5,388-5,395 ORFs.

So the comparison the whole study turns on is **library vs its own source
community at matched size**: does a window of cloned SCADC DNA that *survived
toluene selection* add more carbon-carrying capacity to EPI300 than a random
same-sized piece of the same metagenome? On the one carbon readout measured, the
answer is no.

Density figures behind that, from PROVENANCE.md: a metagenome ORF nominates 9.7
distinct carbon-universe reactions on average against a fosmid ORF's 8.4, while
the fraction of ORFs reaching the universe at all is the same (95.6% vs 96.0%) -
the inserts are less promiscuous nominators, not less well covered.

**Proposed mechanism in the sketch** (toluene partitions into the membrane; clone
2's lipid release flushes it via extracellular vesicles) has literature support in
the KB - Kobayashi et al. 2000 on *P. putida* IH-2000 releasing phospholipid/LPS
membrane vesicles on toluene addition (kb `PFHSVCZ4` / `83KJ7RZ4`), plus the
*P. putida* efflux and cis-trans isomerase literature. It is a hypothesis the
lipidomics and vesicle imaging speak to directly; ECSPr currently does not.

## 6. Gaps and traps for the manuscript

- **Lane naming**: say UniRef50, not UniRef90, for the 4-lane table.
- **Pool count**: 33 pools, 35 read sets, 30 timepoints-with-sequencing per the
  Trilium results note. "35 pools" appears in several journals and is really 35
  read sets.
- **Insert-set discipline**: 132, 199, 157, 183 and 170 all appear in live
  documents. Every ECSPr, circos, ORA/GSEA and heatmap figure in `latest/` is on a
  retired set.
- **Bake discipline**: no conductance number is comparable across bakes. r10
  changed the direction ratio into a physiological quantity; r11 (in `bench-fba`)
  rebuilt the atom lane and moved every arm again. The scadc result is r10.
- **Clone-2 file naming**: the two Plasmidsaurus filenames invert the clone
  numbers; cite the insert ids, not the file stems.
- The 100-axis set4 arm is **built and gated but never run with a null** - that is
  the single cheapest route to an honest lipid-axis number for clone 2, and the
  staged basis is still on fir at `/scratch/phyberos/scadc_ecspr_r10`.
- `data/fabfos/nostoc/ecspr` holds two bakes at once (results r7, networks r10);
  `runs/eydallin_clones/ecspr` grades MIXED r7..r9. Neither is a scadc problem but
  both will confuse a cross-study table.
- Six scripts still read the retired tier4 path and cannot run
  (`benchmarks/aska/{run_panel,triage}.py`, `benchmarks/keio/run_ko_panel.py`,
  `benchmarks/laser/pilot/run_pilot.py`, `benchmarks/laser/vs_gem/common.py`,
  `tests/fabfos/build_references_tier4_agreement.py`). Repointing them to the bake
  invalidates their published numbers rather than porting them (REFERENCES.md).

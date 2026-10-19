# Engcyc / bench-E4 / Cyanoverse / metasmith-paper context for the FosDB manuscript

Read-only research, 2026-10-18. Note: the awm `search` service failed during this session ("service control WS closed mid-call"), so cross-archive search was replaced by `journal fetch` with a query, plus file reads.

## 1. Engcyc as it stands

**Origin.** Thesis proposal v1.8.3, aim A3 "Developing the Environmental Genome Encyclopedia (Engcyc)" (Google Doc 1QNjjff-…; text copy `/home/tony/trilium_footers/corpus/1QNjjff-nlv3ptvTzMP-cSQF4vJQA6VtpzFgEefgiRWw.txt`, A3 at ~L269-294). A1 = Fabfos and functional screening (EPI300 with and without fosmids, framed as "massively parallel HGT"). A2 = Bounding the Cyanoverse. A3 = Engcyc portal/database built from A1 and A2 data. XGDB means "extended genome database", named after PGDBs. It is a folder of standard-format files with a key-value YAML manifest (EDAM keys) and SQLite secondary indexes. It comes in three modal flavours: (meta)genome, fosmid library and ASV. The proposal requires three analyses: ASV→bin mapping, **a time series on a shared assembly (ScaDC)**, and **simulated HGT** (append a fosmid to a host genome, re-annotate, re-model). Source: journal 51a3a2b9 (engcyc/dev).

**What "Engcyc chapters" means.** I found no document that numbers Engcyc chapters 1-3. The nearest sources are below. Ask Tony which numbering he means.
- Thesis-committee "permission to write" deck notes (`corpus/1tS2kmrgKUqlJLq4pjeRMdBkaLsqZLGoJ.txt`). It plans three activities, each as "1 expected publication + 2 chapters": Metasmith (PLOS paper) + "2 chapters (Engcyc)"; Fabfos, with the **ScaDC** paper + 2 fabfos chapters; Cyanoverse paper + 2 chapters (Metasmith extensibility, scalability, portability). L64 says "an additional thesis chapter (Engcyc) describing the final repertoire of integrated tools and producible data products".
- Progress-update notes (`corpus/1Kw7ZwM7…txt` L628, 9 Oct 2025): the Cyanoverse write-up is "Chapter 3" (Overleaf 68dc84205427ca92d6c2c0d9). L431: an "Engcyc d0" paper doc exists (Google Doc 1iIxf1v4W7…), and the notes ask whether "Engcyc: Is this just the metasmith paper?" (L558).
- The scope briefs for `fabfos/manuscript` and `cyanoverse/manuscript` both say "demonstration cases for a planned 4th engcyc chapter".

**Phase 1 (done): dataset manifest.** It lives in `projects/metasmith/engcyc/dev`, with the schema doc at `research/engcyc/SCHEMAS.md`.
- `data/engcyc/manifest.tsv` is a DVC pin with 72 datasets and 15 columns. The modal is metagenome, genome, fosmid or amplicon. The status is available, archived, missing or candidate.
- `data/engcyc/metadata/<id>.tsv` holds 54 tables. Each copies the dataset's existing metadata, with no added columns.
- Scripts: `build_metadata.py`, `validate_manifest.py` and `export_xlsx.py`. A copy is on the Compute2 SharePoint at Outputs/Engcyc/main.xlsx.
- Journals: 47f65383, c1e0717f, 74600dd8, ab9f9b72, 58570829 (latest, 2026-10-15). The engcyc-portal project is also being cleaned for engcyc.org (journal b102ad50).

**Precedence decisions.**
- 35be6211a0b4023a and c9f4d0c0bd61cb34 (2026-10-15): curate existing metadata only, add no columns, write **no fosmid coercion and no XGDB layout "at this stage"**, and keep amplicons.
- 94ac3448f5e96a19: n_samples counts samples that have sequence data. Fosmid rows count libraries, and a count that would need a guess stays empty.
- Related: 145812240c16e823 (GTDB r232 with GTDB-Tk 2.7.2) and 56cd4ef170129d2a (iPHoP Jun25_rw).

**The schema draft artifact is stale but still the only XGDB/fosmid design.** "Engcyc Schemas", https://claude.ai/artifact/81rm7MyNQuuzEah3YBAfHb (14 Oct). It proposes:
- One XGDB per assembly unit (sample, co-assembly group or fosmid library).
- metasmith's `.xgdb` data library plus an engcyc type namespace and an `xgdb.yml`.
- A per-modal contents matrix with columns for fosmid insert and fosmid ends-only.
- **Fosmid coercion:** screen out pCC1FOS and the E. coli host, treat each insert as a contig with one assembly per pool, skip binning, coverage and GEMs ("one clone is not a genome"), and run the same ORF, annotation, taxonomy and viral steps as a metagenome. A library with ends only gets an ends-only XGDB.
- Simulated HGT is a **link product** between a fosmid XGDB and a genome XGDB (EPI300 or CB2A), kept outside both.
- Fosmid modal columns: library_id, pool_id, vector, host_strain, n_clones, n_plates, ends and full-sequence status and paths, source_sample_id.

Tony deferred all of it, so it is unratified.

**Fosmid rows in the manifest.** The 16 fosdb_* tables join the **FosDB sheet v1.JGI_2025-03-21** with the library inventory on a case-insensitive library_id.
- **scadc_fosmids:** 1 library, 35 pools, 170 inserts. It carries the 4-lane GPR and an ECSPR conductance screen with a null result.
- **scadc_metagenome:** n=34, the metagenome plus 33 enrichment pools. Reads are on sharknado, about 100 GB. "Assembled, 4-lane GPR, GPR table built". This is the proposal's time-series / shared-assembly case.
- **revio_2024_fosmids:** 3 pooled HiFi libraries (lignin hits, ScaDC, Sakinaw), assembled with Flye and GoldRush. They carry host and vector sequence.
- **biofactorial_pilot / biofactorial_mini:** Nanopore, 10 clones plus POS and NEG each, 2026-09-25 and 2026-09-28. Inserts recovered.
- **chassis_epi300:** 4-lane GPR built, model borrowed from DH10B.
- **FosDB v1.JGI sheet marks end sequences for JGI:** hydrocarbon 7 libraries (129,792 clones), Line P 30 (224,256), LTSP 16 of 28 (115,200), Saanich 19 (119,808).
- Other rows:
  - Archived with ends found: beaver, mining FOS62, sponge CENSY, OMZ-unlabelled 23 libraries.
  - Eel River GZfos: ends found, live location not confirmed.
  - Sakinaw GUAG: pools sequenced, not processed.
  - Missing: hogfuel, Lakelse, SUPER.
  - None of the archived libraries has been processed in metasmith.

**Phase 2 (designed, solved, not run).**
- Scope `engcyc/pipeline`, branch `feat/engcyc/pipeline` at c685896b. Stage table: `research/engcyc/pipeline.yml`. Gate page: "Engcyc Pipeline", https://claude.ai/artifact/NSJLGiaGryh5BbiXf7GDxZ, "Waiting for Tony to confirm", solved 2026-10-17 on metasmith 0.25.0.
- It merges the bench-E5 front end, the Spanish Lakes metagenome and virome lanes, and the Cyanoverse annotation layer.
- Six read shapes: short_pe (74 steps), short_se, long_hifi, long_noisy, virome_pe, given_assembly.
- GEMs are CarveMe 1.6.6 + MEMOTE 0.17 on every CheckM2-quality MAG.
- The 4-lane GPR (KOfam, CLEAN, UniRef50, ProteinBERT → MetaNetX 4.5), the six annotators and the viral lane are included.
- Open gate questions U1-U7 cover bin selection, virome assembly, callers, annotation set, Spanish Lakes extras, output layout and the 101 SL samples.
- **No fosmid shape exists in the pipeline yet.** Cyanoverse v2 enters through given_assembly.

## 2. bench-E4 (scope `engine/bench-E4`)

**What it is.** It rebuilds metaGEM's (Zorrilla 2021) published GEMs from metaGEM's own 14,105 protein bins (5 studies) in two lanes. Findings: `research/metasmith_benchmark/findings/E4_REPRODUCTION.md`. DAG artifact: https://claude.ai/artifact/2cYW1MJmNF9SF4b2Cvt3b8, which still shows the old single lane, solved key ZInaf9c7. The step is split at DIAMOND: carveme_annotate_bigg, then carveme_carve_gapfill on CPLEX, then memote_metagem.
- **Reproduction lane:** CarveMe 1.2.2, DIAMOND 0.9.30, CPLEX 22.2, MEMOTE 0.9.13, M8 medium.
  - 14,102 models.
  - Against metaGEM's published GEMs, median reaction Jaccard is 0.840, metabolite 0.902 and gene 0.976.
  - 2.1% of shared reactions have a different gene rule.
- **Modern lane:** E5's CarveMe 1.6.6 on SCIP and MEMOTE 0.17.
  - 14,097 models.
  - Against metaGEM, reaction Jaccard is 0.409 and gene Jaccard 0.706.
- **Full run:** 2026-09-22 to 09-25. The archives are the only copy, on chinook at `fir_metagem/`.
- **Quality:**
  - The published GEMs were written by framed 0.5.2, although metaGEM's environment pins 0.5.1.
  - Once the formula and charge attributes are restored, the reproduction lane matches metaGEM's MEMOTE per-test medians.
  - MEMOTE 0.17 total: metaGEM 0.219, reproduction 0.218, modern 0.833 to 0.858. The modern gain is annotation and SBO terms, not biology.
  - Every model grows on the default medium.
  - Not reached: the EMBL, AGORA and KBase comparisons, pan-metabolism and **SMETANA**.
- **Ablation** (1,408 bins, 9 rungs): the CarveMe 1.6.6 BiGG gene reference and its universe carry 96% of the similarity loss. The solver, DIAMOND and the code reshape the models (300-450 reactions per bin) without moving them toward or away from metaGEM. The noise floor is a median of 2 reactions per bin. Journal 4ec4694f warns the attribution is order-dependent. Figures are in the gallery artifact https://claude.ai/artifact/UzdcVDstDKQhbcWj7AtCWG.
- Journals: 345d1f6b, c8fc77e6, 4ec4694f, e754b021, 222eab96.

**"metaGEM" in this context** means reproducing metaGEM's GEM step only (proteins to CarveMe to MEMOTE). E4 runs no metaGEM QC, assembly or binning. **E4 never tested the fabfos 4-lane GPR mapper**: every rung maps genes through CarveMe's DIAMOND-vs-BiGG (journal 4ec4694f).

**mm_compare, the bridge to fabfos.** It lives in the same scope (`research/mm_compare/`, data `data/mm_compare` with `manifest.tsv` as index). Inventory artifact: "Metabolic Reconstruction Inventory", https://claude.ai/artifact/9hKwAbZv29g3mpsk8uCv84 (v4). Journals: c017ba50, eeec6315 (2026-10-15).
- **Methods side by side, untranslated.** The three are Pathway Tools PGDBs, CarveMe 1.6.6 GEMs and the fabfos 4-lane GPR (MNXR). Tony ruled out a MetaNetX crosswalk.
- **Subjects:**
  - 49 CAMI II toy HMP samples. Ryan's 5,392 gold-genome PGDBs and 49 community PGDBs face E5's 757 MAGs.
  - Six E. coli strains: k12, w3110, bw25113, dh1, dh10b, **epi300**.
- **EPI300 PGDBs by three routes** (precedence b80ea3954922df10, "test all 3"):
  - BioCyc prebuilt.
  - The metasmith `pathologic` transform. It never produced a PGDB before this work and was fixed here.
  - MetaPathways 3.5.1.
  - The Pathway Tools image is licensed. Never share it (precedence 87cfc37f5e2ce30b).
- **Findings relevant to FosDB:**
  - CarveMe and the 4-lane rank strain-pair differences alike (Spearman 0.84). Both put EPI300 nearest DH10B, the 4-lane by a wide margin (62 against 218 or more).
  - The metasmith PGDB puts EPI300 next to DH10B (3 reactions against 17 or more).
  - The 4-lane is a scored candidate set: about 11,200 MNXR per strain against about 2,480 CarveMe reactions. Count comparisons need a score cut.
  - MEMOTE totals are bimodal, set by stoichiometric consistency, and DH10B carries an ATP-generating cycle.
  - 83% of CarveMe model genes carry a 4-lane call.
  - CarveMe recovers 76-78% of curated iML1515 and iECDH10B gene-ruled reactions.
- **Status:** collection is done, and the comparison "test session" is not yet designed. Do not contact Ryan yet.

**How it connects to fabfos ECSPr.**
- **ECSPr** (`docs/ecspr/architecture.md` in fabfos/manuscript) is an atom-resolved conductance instrument. It reads GPR tables (ORF × channel × nominated MNXR on a baked MetaNetX atom-pair universe), conditions tables (an ordered set algebra over GPR rows) and tests tables.
- Two arms read one table: `ground` / `two-point` (conductance) and `ecspr fba` (an LP on the carved frame).
- **The 4-lane GPR is its input.**
  - Lane justification on EPI300: CLEAN, KOfam, UniRef50, ProteinBERT (`research/fabfos/annotation_lanes/README.md`).
  - Host GPR tables for dh10b, k12 and epi300 come from `build_references`. EPI300 "needs no model of its own" and borrows iECDH10B_1368 (fabfos/assembly journal 2a1f15f6).
  - The current branch tip (2d15128f, fce29691, 80d18728) moves the DH10B model onto EPI300's ORFs and finds fhuA is the only difference.
- **SCADC arm** (`fabfos/scadc` scope brief; drivers `research/fabfos/examples/scadc_ecspr_{basis,arm}.py`; output `data/fabfos/runs/scadc_fosmids/ecspr/PROVENANCE.md`):
  - 170 inserts over the EPI300 host on the r10 bake.
  - **Null:** no insert clears its size-matched null on glucose-to-biomass carbon.
  - A later "set4" asks 79 more axes, including the glycerol backbone of the phospholipids.
- **Flux balance as the independent method** (`research/fabfos/vs_flux_balence/README.md`, bench-fba journal 537bc527): FBA does not predict the Eydallin glycogen screen. Its accuracy equals the base rate, and only reduced costs from one LP give rho of about 0.65 (p<0.05) on n=15. ECSPr's ratio metric is the only arm above the base rate.

So the honest chain is this. E4 established and validated the GEM lane (CarveMe, MEMOTE) and its limits. mm_compare put CarveMe, PGDB and 4-lane side by side, including EPI300. fabfos ECSPr runs on the 4-lane GPR plus the borrowed DH10B/EPI300 GEM frame.

## 3. Cyanoverse as an example XGDB

It is the closest thing to an XGDB. It is spread across fir, capella, mira and Globus, not packaged (journal 51a3a2b9).
- **Inputs:** 2,844 public cyanobacteria assemblies (taxid 1117), from isolates to metagenomes.
- **Contig table:** `contig_stats.parquet`, 48.5M contigs, with coverage, Metabuli and geNomad.
- **Per-tool annotation stores** (capella `annotations` scope): InterProScan, Bakta, antiSMASH (539 of 2,844 ingested), DeepEC, BUSCO and PredicTF are done. EggNOG and DeepTFactor are incomplete, and PromoTech is partial.
- **4-lane GPR:** 1,740,652,809 rows over 2,844 per-assembly tables at fir `gpr/split/tables/`. CLEAN is 91.9% of rows. The driver is `aspire/dev/research/fabfos/examples/cyanoverse_gpr.py` (fabfos/cyanoverse journal 6bdcdf58, 2026-08-08).
- **Other products:** 44,419 MAGs, MMseqs2 clusters and ProteinBERT embeddings, plus the NMF guild and archetype analysis (cyanoverse main repo).
- **Gaps:** no upstream reads-to-assembly driver, an incomplete viral lane, no gene or pathway abundance and no PGDB.
- **AB48 single-sample example** (cyanoverse/ab48, task IzMHfSLA; journals de80d4df, fe0130fc):
  - HiFi, 24 dereplicated MAGs, GTDB-Tk r232 and Metabuli.
  - `gpr_table.parquet`: 569,854 rows over 60,316 ORFs.
  - A Globus `community_metagenomics/` tree includes MetaNetX reference tables.
- **Metabolic modelling: none on Cyanoverse.**
  - `pipeline.yml` marks GEMs and MEMOTE as "-" for Cyanoverse.
  - The 4-lane table was built for "downstream conductance analysis" (6bdcdf58), and no Cyanoverse ECSPr run was found.
  - Related but separate: `research/fabfos/examples/nostoc_ecspr*.py` measures a three-member Nostoc/Erythrobacter/Rhizobium community as twelve directed ECSPr networks.
- **Overlap risk:** the `cyanoverse/manuscript` scope brief also calls Cyanoverse "the pilot XGDB entry in the engcyc collection" and calls FabFos/ecspr/scadc the related route. Its working argument is guilds against archetypes (NMF). The two manuscripts each claim "pilot XGDB". Agree the split with Tony.

## 4. The metasmith paper (`engine/manuscript`) and E1-E5

**Storyline.** Metasmith is a type-system workflow generator.
- The user declares data, target and tools. A backward solver derives the pipeline and compiles it to Nextflow, with containers as typed inputs and a lineage-hash cache that survives topology changes.
- The literature brief is at `engine/manuscript/research/metasmith/manuscript/intro_literature_brief.md`. The planned venue is PLOS.
- The live doc is `Metasmith_d1.docx` on OneDrive (B:/OneDrive - UBC/Hallam Lab - Metasmith/d1).
- Figures are `metasmith_figure_1..6`: 1-3 interface, types and solver (methods panels, https://claude.ai/artifact/9mMAcGQqePDUDgXbVaRy8r, plus an overview figure awaiting Tony). 4 reproducibility (https://claude.ai/artifact/1aZn13n98pGvxPke2rJjXw). 5 assembly flexibility (https://claude.ai/artifact/FmcDs8W2M32npbiFEkjGcS). 6 composition, a benchmark module sankey (https://claude.ai/artifact/E8vyzYcxBWoyeT7YjWEAqe).
- Benchmark Results are deferred to "a later session as a single section".
- The latest journal is 6fceeb9d (2026-10-16, incomplete). Methods text is waiting on Tony's review. See also engine/dev 8e3b714d.

**E1-E5** (artifact https://claude.ai/artifact/T466FDoHbeyiZ49DZ5UMmB, a 2026-09-26 draft, plus the scope briefs):
- **E1, parity control.** nf-core/mag 5.5.0 run as itself on 249 CAMI II+III samples.
- **E2, parity.** The same pipeline solved by metasmith. It reproduces E1 within assembler variation. AMBER was dropped from the claim (journals 0e880172, 4ff09a6d).
- **E3, reproduce.** Pratama 2026 groundwater virome vOTUs (72 runs). Closed at 36 of 39 steps and archived to chinook.
- **E4, reproduce.** metaGEM GEMs, as in section 2.
- **E5, optimized.** The full run covered 805 runs over CAMI, Pratama and metaGEM and finished 2026-10-17: 24,087 DAS Tool MAGs, 24,083 CarveMe models with MEMOTE, 13 viral catalogues and 176,202 core-hours (`findings/E5_RUN.md`). A corpus × lane "crossed table" is built for an E5 version of the reproduction figure (journal 2f0f6ebd).

**Avoid overlap.** E4's parity, ablation and MEMOTE results belong to the metasmith paper's reproducibility figure. So does mm_compare, if it becomes a benchmark. FosDB should cite them, not re-claim them. FosDB's own ground is the fosmid modal itself (coercion, pooled libraries, insert recovery) together with EPI300 host modelling, simulated HGT and ECSPr on the 170 SCADC inserts.

## 5. "Fosmid Pilot Figures" (https://claude.ai/artifact/AT4yhHHu1S4YAV4GC3EHtX)

Four Plotly panels with no prose. The data fits **biofactorial_pilot**: Nanopore, 10 clones plus POS and NEG, 2026-09-25. Which scope made it is not in the journals I read.
1. **qtime:** read mean Q against sequencing time (0-72 h) as a density, with a pass/fail throughput strip in bp/h. The pass line is Q9.
2. **qlen:** mean Q against read length (0-100 kb) as a density, with pass/fail marginals.
3. **samples:** per-clone ≥Q9 bp bars with violin and box plots of mean Q and read length.
   - Order: NEG, POS, then C01, D02, B02, E02, A01, H02, N01, O03, D04, J03.
   - C01 has 640k reads and 5.76 Gbp ≥Q9. Clones run from 44k reads (B02, 0.63 Gbp) to 640k. POS has 115 Mbp. NEG has 21 Mbp with a median length of 0.25 kb.
   - Median Q is 16-19. Median lengths are 2-9 kb, and B02's q3 reaches 24.5 kb.
4. **recovery:** a subsampling model against reads per clone (N, log scale 5 to 1M). The figure greys out the region beyond the N it tested.
   - Curves: % insert length recovered, % sequence matched against consensus, and the chance of recovery by a full-length read, by assembly, or by either.
   - At N≈50: 98% length recovered, P(full-length read) 0.97, P(assembly) 0.60.
   - Saturation by N≈100-230: either ≈1.0, assembly plateaus at 0.83, sequence match at 98.4%.
   - Every pilot clone (44k-640k reads) sits far beyond saturation. This suggests far fewer reads per clone, or deeper multiplexing, would suffice.

## Key paths
- `/home/tony/agentic_workspace/projects/metasmith/engcyc/dev/research/engcyc/SCHEMAS.md`, `.../engcyc/dev/data/engcyc/manifest.tsv`
- `/home/tony/agentic_workspace/projects/metasmith/engcyc/pipeline/research/engcyc/pipeline.yml`
- `/home/tony/agentic_workspace/projects/metasmith/engine/bench-E4/research/metasmith_benchmark/findings/E4_REPRODUCTION.md`, `.../engine/bench-E4/research/mm_compare/`
- `/home/tony/agentic_workspace/projects/metasmith/engine/bench-E5/research/metasmith_benchmark/findings/E5_RUN.md`
- `/home/tony/agentic_workspace/projects/metasmith/fabfos/manuscript/docs/ecspr/architecture.md`, `.../research/fabfos/{annotation_lanes,vs_flux_balence}/README.md`, `.../research/fabfos/examples/scadc_ecspr_arm.py`
- `/home/tony/agentic_workspace/projects/metasmith/engine/manuscript/research/{manuscript,metasmith/manuscript}/`
- `/home/tony/trilium_footers/corpus/1tS2kmrgKUqlJLq4pjeRMdBkaLsqZLGoJ.txt` (committee deck, thesis chapter plan)

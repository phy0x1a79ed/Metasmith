# FosDB manuscript — orientation (2026-10-18)

What we have, how the fosmid work squares with SCADC, and the story beats to discuss. The four reports in `gather/` hold the detail and the source of every number; this page is the synthesis.

| Report | Covers |
|---|---|
| `gather/scadc_fosmids.md` | insert recovery, selection, annotation, every ECSPr run, benchmark verdicts, figure inventory |
| `gather/lipidomics.md` | LC-MS/MS and vesicle imaging results, where they were reported |
| `gather/fosdb_history.md` | FosDB origin, collection tables, sharknado, prior writing, Trilium |
| `gather/engcyc_e4.md` | Engcyc phase state, bench-E4, Cyanoverse, the metasmith paper |
| `gather/lipidomics_od_report_2026-07-18.html` | the lipidomics report page, recovered from capella |

## What FosDB is

FosDB is not an old database. The name first appears at a Pathway & Compute meeting on 2023-01-27, "Make work-plan for 'FosDB'". That entry lists what FosDB should do: annotate fosmids, map pooled fosmids back to wells by end sequences, map fosmids to bins of the source metagenome, estimate unique fosmids per pool, track IDs, and model metabolic potential in the E. coli host. What exists is a set of tables, now in `engcyc/dev` under `data/engcyc/sources/fosdb/`:

- `FosDB Manifest.xlsx`, sheet `v1.JGI_2025-03-21`: 161 rows, 119 libraries, sharknado paths, end and full sequences sent to JGI.
- `fosmid_library_inventory.xlsx`: 93 Line P and Saanich libraries with cruise, station, date and depth.
- Phoebe's annex: the whole Hallam collection, 1,896 plates and 711,414 clones.
- `Hydrocarbon library raw data.xlsx`: every ScaDC pool FASTQ path on sharknado.

Sharknado is mounted read-only on worker-01 at `/mnt/sharknado_backup/Shamwow_Home/`. Admin ssh there is gated, so a sharknado read needs a window Tony opens.

## The framing documents

- Thesis proposal v1.8.3 (`1QNjjff…`, text in `~/trilium_footers/corpus/`). A1 is Fabfos and functional screening on ScaDC. A3 is Engcyc and defines the XGDB: a folder of standard files, a YAML key-value manifest with EDAM keys, and SQLite indexes. XGDBs come in three modal flavours: (meta)genome, fosmid library and ASV. A3 names three analyses: ASVs onto bins, a time series over one shared assembly (ScaDC), and simulated HGT (a fosmid appended to a host, re-annotated, modelled). Table 3.1 lists 12 fosmid libraries plus three chassis (AB48, CB2A, EPI300).
- The A1 expected publications: the toluene pool-selection paper (Kat first author, "95%"), FabFos (90%), the EPI300 genome (80%), and "Metabolic network expansion in E. coli based on massively parallel HGT" (25%). The last is the closest ancestor of this manuscript.
- The toluene manuscript drafts v8 and v10 (`1N3XoW…`, `1dPYyN…`): Ievdokymenko, Liu, McLaughlin, (Ho), Hallam. Both are built on the retired 132-NRC set.
- The committee talk (`1tS2km…`): Metasmith gets one paper plus two Engcyc chapters. No document numbers the chapters. Tony's "4th Engcyc chapter" needs his numbering.
- Trilium notes in the frozen `notes` search source: `scadc/sketch` (b8e1a447) is the newest story outline; also `scadc/intro/01`, `scadc/outline`, `scadc/results/*`.

## Isolating the fosmid work from SCADC

SCADC is the ScaDC study, a Short-Chain Alkane-Degrading Culture from an oil sands tailings pond. It has two sequence layers:

1. **The fosmid pools.** 33 pools (35 read sets) sampled from a 77-day toluene selection of the ScaDC library in EPI300. They resolve to **170 inserts**, the canonical set in `runs/scadc_fosmids/`. The sketch's junction counts hold: 107 inserts with two junctions, 47 with one, 16 with none. Clone 2 dominates 16 read sets and every vitamin-arm pool from day 19. Clone 1 wins only the pool03 branch of the vitamin-free arm.
2. **The shotgun metagenome** of the culture (`runs/scadc_metagenome/`, 1.44 M ORFs, the same four lanes). It is the null pool and the ORA/GSEA background.

The fosmid work is therefore a library measured against its own source community at matched size. As an XGDB this is a fosmid-modal entry (170 inserts) linked to a metagenome-modal entry (the source) and to a chassis entry (EPI300). Those three entries are the A3 time-series and simulated-HGT cases.

## Where each pillar of the sketch stands

| Sketch claim | Status |
|---|---|
| Inserts resolved, pools converge to clones 1 and 2, long reads confirm | **Holds** on the 170 set. "> 96.4% of reads" is 96.2% at the worst pool, and that figure counts the pCC1 backbone; inserts alone take 79–85%. The Plasmidsaurus filenames swap the clone numbers. |
| 4-lane annotation (KofamScan, UniRef90, CLEAN, ProteinBERT) | **Holds, with a correction:** every shipped table uses UniRef50. ORA, GSEA and the circos are drawn on the retired 199 set and need a redraw on the 170. |
| ECSPr: clone 2 raises carbon conductance towards lipids | **Unsupported.** On r10, 0 of 170 inserts clear the size-matched null on glucose → biomass hubs, and clone 2 ranks 25/170 (z 0.55). The lipid claim traces to June work on the retired 132 set, which that scope later retracted. The 100-axis set4 arm, lipid axes included, is built and gated (84 of 100 axes live) but has never run with a null: ~280 core-hours on fir. |
| ECSPr validated on a glycogen screen | **No.** The eydallin ASKA arm falls below its own size control. ECSPr does work under gene deletion (Keio LOF AUC 0.73–0.92; Fuhrer 76/99, where it beats FBA) and for edge-local specificity. It fails for overexpression and for direction, and SCADC is an addition cohort. |
| Lipidomics: clone 2 overproduces lipids and releases them under toluene | **Real but reframed.** Toluene raises total lipid per OD about 2.5× in EPI300 and the empty vector and about 1.1× in both clones. 29 hits at Storey q < 0.05; the 7 Clone2 supernatant up-hits under toluene are mostly phospholipids (PS, PE, PG family). No class enrichment survives correction. Clone 2 chains run about 2.5 C longer and more unsaturated, and Clone 1 chains shorter. |
| Clone 2 flushes toluene via extracellular vesicles | **Cut against.** Clone 2 under toluene sheds the least vesicle membrane per OD (20.6, below the blank floor), and pCC1 sheds the most (366). The lipidomics readme's own wording is "pCC1 barely grew and Clone2 did." |

## Metabolic modelling route

- bench-E4 rebuilt metaGEM's GEMs with CarveMe. The reproduction lane matches (reaction Jaccard 0.84); the modern lane does not (0.41), and 96% of that loss traces to CarveMe 1.6.6's reference and universe. E4 belongs to the metasmith paper; FosDB cites it rather than re-claiming it.
- `mm_compare` sets PGDB, CarveMe and the 4-lane GPR side by side on six E. coli strains, EPI300 among them. CarveMe and the 4-lane rank strain differences alike (Spearman 0.84). The comparison test itself is not designed yet.
- ECSPr reads the 4-lane GPR in the MetaNetX universe. The host is EPI300 on DH10B's GEM; fhuA is the only difference. The FBA arm (bench-fba, r11) runs on the same construction and is also a clean negative on SCADC.
- Cyanoverse has the annotation layer (4-lane, 1.74 B rows, 44,419 MAGs) and no metabolic models.

## Risks to act on

- **Lipidomics results exist only on capella, partly unpinned.** The 2026-07-18 artifact (#856) no longer opens; its source is copied into `gather/`. The publish tree `04_lipidomics/` holds `data/figures` modified and 12 uncommitted changes. That includes the Storey volcano SVG in the Trilium note, the hits CSV, the identification methods, and the untracked script that draws them.
- **Two manuscripts claim "pilot XGDB".** `cyanoverse/manuscript` calls Cyanoverse the pilot XGDB entry too.
- **No figure exists on the current r10/r11 SCADC result.** Every ECSPr, circos and ORA figure in `fabfos/figures/data/figures/latest/` sits on a retired insert set or bake. The 170-set recovery figure scripts exist and have not been rendered (about a minute each).

## Candidate story beats (for discussion, not settled)

1. **Parts catalogue.** A fosmid library is a catalogue of massively parallel HGT events. The Hallam collection holds 711,414 clones, and its record lives in plates and spreadsheets in no model-ready form.
2. **FosDB as the fosmid-modal XGDB.** One manifest over inserts, junctions, pool abundance, the end-sequence well map, annotation lanes and GPR. metasmith builds it from raw reads, and it links to a source-metagenome XGDB and a chassis XGDB.
3. **ScaDC pilot, recovery.** The time series resolves to 170 inserts, and selection converges on two clones in two arms.
4. **Functional annotation.** The 4-lane ensemble feeds the MetaNetX universe. Show the annotation rate across fosmids, metagenome and EPI300, and whether fosmid ORFs are a random subsample of the source (MMD). Both need a redraw on the 170 set.
5. **Simulated HGT.** Host plus insert, against size-matched draws from the source metagenome, under ECSPr and FBA. Both come out negative on carbon throughput: selection did not pick for central-carbon capacity. Report it with the benchmark map of where the method answers (deletion) and where it does not (addition).
6. **Phenotype.** The clones hold their growth and keep lipid per OD flat, while the background's membrane lipid per OD climbs. Clone 2 lengthens and unsaturates its chains. This reads as membrane remodelling, not vesicle flushing. The open measurement is whether the set4 lipid axes see clone 2 under a null.
7. **Scale-out.** The 72 libraries with end sequences at JGI, the Revio 2024 pools, and the Biofactorial Nanopore pilot, which recovers an insert at about 100 reads per clone. Together they make FosDB the Engcyc collection's fosmid entry.

The open fork is between a resource paper (beats 1–2 and 7, with ScaDC as the worked example) and the biology paper that Kat's toluene drafts already carry (beats 3–6).

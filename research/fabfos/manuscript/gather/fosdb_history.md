# FosDB history and prior writing: research report (read-only)

## 1. The original FosDB

### Bottom line
- I found no standalone "original FosDB" database, web app or schema. What exists is a set of Hallam lab spreadsheets and sharknado paths that Tony and Mahan pulled together in 2023-2025 to inventory the lab's fosmid collection. The oldest use of the name is the Pathway & Compute meeting on **Jan 27 2023**: "Make work-plan for 'FosDB' (all metagenomes and fosmids processed for draft manuscript in Feb.)", with "Objective/Purpose of FosDB", "Features for FosDB", "Get data from sharknado" (corpus `1U6mn4…txt` L2184-2226).
- That meeting's list of useful FosDB functions is a good spec for the manuscript: start from raw reads; annotate fosmids; measure diversity between fosmids; map pooled-assembly fosmids back to wells using end sequences; map fosmids back to bins of the source metagenome; estimate the number of unique fosmids per pool as standard QC; track IDs; and model "metabolic potential" of the library together with the E. coli host.
- Other mentions: progress updates (corpus `1Kw7Zw…txt`):
  - 04 Jun 2024: "large collection of biological parts in the form of fosmid libraries, but no established search procedure or index."
  - 16 Jul 2024: Tony was helping Mahan gather the first fosmid libraries "for fosDB, fabfos, and the proteorhodopsin screen". The suggestion was to demonstrate Fabfos on the fosDB collection, "mainly lineP and napdc".
  - 13 Aug 2024: Mahan mapped 681 of 1,036 Line P fosmids (65%) with Fabfos. "Engcyc… linking in fabfos, fosDB, and cyanoverse… The beaver outputs and fosDB can be used as pilots."
  - 26 Jun 2024: a "projects" archive on Globus started with "parts of fosDB".
- Lab history behind sharknado (meeting of Oct 18, about 2022, L1734): the lab started in 2006. After the CVM hire fell through, the lab bought an Apple Xeon server, its drives failed, and the lab "built sharknado". Shangrila (Xeon) was later replaced with shamwow. Paths read `/mnt/nfs/sharknado/LimsData/…`, and the archive is laid out as environment/data_type/external_facility.

### Where the FosDB tables live (local, read-only DVC pins)
`/home/tony/agentic_workspace/projects/metasmith/engcyc/dev/data/engcyc/sources/fosdb/`:
- `FosDB Manifest.xlsx` (local copy of Google Sheet 19B-qfu0aoeGUYxGCca5RlfIU-IzgoktkmRDMcxxlRLg, mtime 2026-02-27). It has 4 sheets:
  - `shamwow_keyword_scan.1`: 123 libraries. Columns: source, centre (GSC 42, JGI 41, PSSC 5, blank 35), library_id, ends path, full_sequences path, sample_name, no_plates, no_clones, end_sequenced, pool_status, no_tubes, notes. About 740k clones summed.
  - `consolidated_sharknado_paths`: 250 rows (23 "ends", 15 "full", the rest untyped). Paths fall under Hydrocarbon/{RawData/Genome_Sciences_Centre/Saenger_fosmid_ends, ProcessedData/…/Illumina_full_fosmids/Hydrocarbon_fosmid_assemblies, External_data}, LTSP/WilliamsLake/<lib>, OMZs/Saanich_and_LineP/{ProcessedData, Accessioned/LineP_Saanich_Fosmid_ends/CLEANED}, MiningBioReactor/RawData/Genome_Sciences_Centre/Illumina_full_fosmids, and Sponge/{Processed Saenger ends CenEnds_clean_ez.fasta, RawData GSC Illumina_full_fosmids}.
  - `v1`: 161 rows. Columns: source, library_id, should_have_ends, should_have_full_sequence, found_ends, found_full_sequence, sharknado_ends, sharknado_full_sequence.
  - **`v1.JGI_2025-03-21`**: the same 161 rows (**119 with a library_id**, the rest blank) plus two added columns, **"Ends to JGI"** (73 yes) and **"Full seq to JGI"** (5 yes, plus LTSP NO001 = "INX119-vector-trimmed.fa from GSC" and Saanich FGYA = "JGI Assemblies: 38484-38494", 11 IDs). The other counts are should_have_ends 71, should_have_full 46, found_ends 104 and found_full 12. My reading is that this records what was sent to JGI on 2025-03-21. The sheet does not say so.
  - Per source (n libraries / ends to JGI / full to JGI / found ends / found full):
    - Hydrocarbon (CG23A, CO182, CO183, NapDC, TolDC, ScaDC, PWCG7, TailM): 8 / 8 / 5 / 8 / 6
    - LineP: 30 / 30 / 0 / 30 / 0. These are 12010-41300 (P12/P4, Feb 2010) and GOxx/GTZx/GUAx (Jun and Aug 2009, P4/P12/P26, 10-2000 m).
    - Saanich (FGYx, FPPx, FZGx; S3, 2006-07, 10-215 m): 19 / 19 / 0 / 19 / 0
    - WilliamsLakeLTSP (NO, NA, NB, NR, CO, CA, CB, SCR soils): 26 / 16 / 0 / 16 / 0
    - "?": 25 (ALTSP and ELTSP, plus 23 named a/j{4,12,26}_{depth} that look like Line P station-depth samples): 0 / 0 / 25 / 0
    - Beaver (BEAVR, B2Cecum, B2PC, B2Rec), Mining FOS62, Sponge CENSY: ends and full sequences found, nothing sent to JGI
    - Eel River GZfos, Sakinaw GUAG, SUPER, HP20, LAKELSE: nothing found
- `FosDB Manifest.BU.xlsx` (2025-03-24 backup, 3 sheets, without consolidated_sharknado_paths).
- `fosmid_library_inventory.xlsx`, sheet `libraries`, 93 rows. Columns: Project, library_id, status (Complete/In_progress), no_plates, no_clones, no_tubes, notes, freezer location, sample source (cruise/station, e.g. "LineP-J09 St P26", "SI005 St S3"), environmental type ("Open Ocean OMZ", "Seasonally Anoxic Fjord"), Date Collected, lat, lon, depth. Many rows other than LineP and Saanich have no metadata ("hydrocarbon?", "Williams lake?").
- `Hallam Fosmid LIbraries (from Phoebe).pdf`: **Annex 2, "Biological Material"**, pages 16-18 of a DocuSign agreement (envelope 894C22FE…), listing library_id, plates, clones, source and format. **Total 1,896 plates, 711,414 clones.** It looks like an MTA or transfer annex for the whole collection. Ask Phoebe or Steven what the agreement was.
- `Hydrocarbon library raw data.xlsx` (91 rows: library, description, sharknado path). Examples are the ScaDC metagenome reads, ScaDC ends "40 runs, 20 plates" (`…Saenger_fosmid_ends/SCADC/SCADC_Dec20_2011`) and every ScaDC toluene pool FASTQ under `LimsData/Kats_temp/ScaDC_toluene_pools/52647.2.412368.<barcode>…` with pool, day, vit and parent lineage.
- `gzfos_ends.aka_AHHF.fasta` (GZfos Eel River ends, 6,427 seqs) and `Mapping for Rhea.xlsx`.

### How the engcyc scope uses it
- Built by `research/engcyc/scripts/build_metadata.py` (L137-181). `fosmids()` reads sheet `v1.JGI_2025-03-21` and joins it to the inventory on a case-insensitive library_id. B2Rec/B2Rectum and BEAVR/BEAVER do not match.
- `data/engcyc/manifest.tsv` has 13 `fosdb_*` rows: beaver, eel_river, hogfuel, hydrocarbon, lakelse, linep, ltsp, mining, omz_unlabelled, saanich, sakinaw, sponge, super. It also has `scadc_fosmids`, `revio_2024_fosmids` and the biofactorial pilot/mini rows. The per-dataset tables are in `data/engcyc/metadata/fosdb_*.tsv`.
- Clone counts in the manifest notes: LineP 224,256; Hydrocarbon 129,792; Saanich 119,808; LTSP 115,200; Beaver 46,080; FOS62 36,864 (3 plate sets); Lakelse 10,368; Sakinaw 7,680; HP20 6,528; GZfos 3,552; SUPER 3,072; CENSY 2,016.
- Sizes measured on sharknado: fosdb hydrocarbon 18 GB, LTSP 22 GB, mining 34 GB. The Saanich, Line P and omz_unlabelled rows share one Sanger-ends folder, so their sizes are blank.
- The proposal's Table 3.1 fosmid set covers 11 of 12 libraries with no sequence location except ScaDC (journal 51a3a2b9).
- Other copies: chinook Globus `/Fosmids/Nucleotide/` holds the beaver data. chinook `/Fosmids/sharknado_archive` holds the CENSY ends and a `pathlist.txt` from an archive run that stopped after one file. There is also a **sharknado index**, an SQLite db of every file on sharknado with a search script and container, on chinook Globus `/Resources/sharknado_index/` (meeting of 07 Feb 2025). It is not found on altair.

### Sharknado access: not attempted
- Journal c1e0717f (2026-10-15): the Sharknado_Backup volume (300 TB) is mounted read-only on Arbutus worker-01 (192.168.100.95) at `/mnt/sharknado_backup`. `sharknado:/LimsData/<X>` maps to `/mnt/sharknado_backup/Shamwow_Home/<X>`. The root-level `/ENGCYC` folder is missing from the backup. All 48 LimsData paths that the manifest needs exist.
- **Since journal f5589474, admin ssh to worker-01 is gated by Tony's unlock window** (`~/.ssh/awm-admin-unlock worker-01 <min> "<reason>"`, run only by Tony). The login is ubuntu with `~/.ssh/ubc/chamois`, and the window must name the IP. The memory note `sharknado-on-worker-01.md` forbids routing around the gate. I did not try to connect.
- For more FosDB content on sharknado (e.g. `Fosmid_pools`, `Kats_temp/`, `Hallam_Databases`), ask Tony for a window via `operations(request_human, kind="blocked")`, or query the sharknado index on chinook.

## 2. Corpus documents (`/home/tony/trilium_footers/corpus/`)

| id (prefix) | title, dates | relevance |
|---|---|---|
| 1QNjjff | thesis proposal v1.8.3 (2024-12 to 2025-10) | Core framing: aims A1-A3, XGDB, Table 3.1. Detail below. |
| 1kt35P | from_thesis (2025-01-15) | Earlier A1 draft ("From d1.7"). Same figures 1.1-1.12. Its numbers differ from v1.8.3: 1,246 fosmid functions, 826 of them reactions, and 1,474 EPI300 reactions giving 1,687 in total (v1.8.3: 611 NRC + 1,096 EPI300 reactions, 457 shared). It frames growth-vs-tolerance as "reward hacking" (Eq 2.2). Host removal uses K-12 only. |
| 1N3XoW | ScaDC_manuscript_v8 (2024-01 to 2026-05) | Toluene pool-selection paper (details below). |
| 1dPYyN | ScaDC_manuscript_v10 (2026-05-14) | Next version of the same paper. Differences below. |
| 1tS2km | transcript.docx (2026-05-04) | Committee talk asking permission to write. It reframes the thesis as Metasmith, Fabfos and Cyanoverse (below). |
| 1aqmCb | "all" (2026-06) | The newest ScaDC/ECSPr story: fosmid as ~30-gene "software chunk"; 4 annotation lanes (kofamscan, DIAMOND/UniRef50, deepEC, ProteinBERT label transfer; ESM-C tried) into a MetaNetX GPR truth table; iECDH10B_1368 as the EPI300 GEM, checked to keep the leu/ara deletions; 4 null models (N=1000, M=27/34/48) with KL divergence; ECSPr effective conductance on atom-mapped bipartite graphs; CarveMe named as the GEM baseline. **The most relevant text for the functional annotation and metabolic modelling part of a FosDB paper.** |
| 1iIxf1 | Engcyc d0 (2025-11) | Engcyc chapter draft: data hierarchy (Hahn tiers), databases (tables, relational, graph, KV, ontologies, embeddings), interfaces, compute environment, grid/cloud. Background prose for an XGDB section. |
| 1zg2xt | Metasmith (2026-07) | Metasmith abstract drafts: type system plus AI planner compiles Nextflow; the catalogue includes assembly, annotation, binning, ASV and GEM construction. Gives the "metasmith as driver" framing. |
| 1k69oT | thesis proposal d0 (2022-10 to 2025-04) | Early notes on assembly theory, combining genetic systems, Conway's law, "Limes", reference-annotation bias. Little to reuse. |
| 1Kw7Zw | Tony progress updates (2022-09 to 2026-06) | Meeting log with Steven: FosDB/Mahan/Line P (2024), Engcyc vision, "Chapter 3" Overleaf (cyanoverse, Oct 2025), 4-stage toluene model (Mar 2024), XGDB as metasmith input. |
| 1U6mn4 | Pathway & Compute Meetings (2022-01 to 2026-02) | Lab compute meetings: the Jan 2023 FosDB work-plan, sharknado history, the sharknado index (Feb 2025), the FosDB Manifest link and Engcyc curation targets (Jan 2025), the projects archive (Jun 2024). |
| 1uEQkM | Thesis_Proposal_RJM_211007 (Ryan McLaughlin) | SABer proposal: A1 synthetic SAG catalogue, A2 SABer xPGs, A3 Saanich Inlet multi-omic proteobacterial pangenome (376 SAGs). Useful for Saanich context and XGDB modality precedent, not for fosmids. |
| 1YxpX5 | Nature Pavlopoulos et al. (2022) | Copy of the functional dark matter paper (Pavlopoulos 2023). A citation for the annotation gap. |
| 1eSDg9 | Cyanoverse poster text panels (2026-03) | Cyanoverse abstract. Engcyc sibling dataset only. |
| 1DTe8l | 2025.9.23 slides | Talk outline "Gene expression, subsystems, compositionality": prokaryotic diversity, central dogma, subsystems as components, levels. Background framing only. |

### Thesis proposal v1.8.3 in detail
- **Thesis title:** *Exploring the Metabolic Interoperability of Microbial Operating Systems*.
- **Hypothesis:** pathways can be extended through HGT within single cells or across multiple operating systems (syntrophy, symbiosis).
- **Aims:**
  - A1 Fabfos and Functional Screening: model EPI300 with and without fosmids under selection.
  - A2 Bounding the Cyanoverse.
  - A3 Developing the Environmental Genome Encyclopedia (Engcyc): a FAIR database and portal built from A1 and A2 data, at https://engcyc.org.
- **The proposal has no chapters.** It is organised as "three research and development activities". Figures are numbered 1.x, 2.x and 3.x.
- **A1 (L59-162):**
  - Background: fosmids as massively parallel HGT. pCC1 (EU140751.1) with oriV copy control. About 30-45 ORFs per insert.
  - Kat's pool selection: NapDC, ScaDC and TolDC libraries of about 22k clones each, about 7,500 clones end-sequenced. Selection at 0.1% toluene. Only ScaDC MM+V was stable. A 77-day branching lineage was sampled on days 6, 11, 19, 23, 33 and 42, giving 33 snapshots, sequenced on NovaSeq at JGI.
  - Analysis history: MINTIA and SHIMS2 were dropped (Perl, Consed). FabFos was refactored (Snakemake, conda, Docker). The SPAdes multi-assembly gave 132 NRCs over 30 kb, covering >93.5% of reads. Lineages L1-L4. Kofam, Pfam, SCOP, MetaCyc, SwissProt, UniRef90 and LCAstar annotations. 8 functional clusters from 66-feature KEGG/BRITE vectors. Reaction network: 611 NRC vs 1,096 EPI300 reactions, UMAP of Jaccard distances. NRC001 (pfp, gmd, moaEDCA) and NRC002 (dhaLK, ribB, eltD, lyxK, ulaE, tkt) suggest flux through the PPP and glycolysis into glycerolipids, i.e. OMV flushing. 5 phage NRCs. ProteinBERT label transfer onto NRC001.
  - Planned papers: toluene pool selection (95%), FabFos (90%), EPI300 genome (80%), "Metabolic network expansion in E. coli based on massively parallel HGT" (25%).
- **A3 (L269-349):**
  - Definition: XGDB = **extended genome database**, modelled on MetaPathways PGDBs, built to supply COMETS community modelling.
  - Layout: one folder of standard-format files plus a YAML manifest. Key-value, DynamoDB-style. EDAM ontology keys. Properties can be omitted.
  - **Modal flavours:** (meta)genome (an isolate is a metagenome with one member), fosmid library ("catalogue of biological parts"), and ASV. New omics modals only need new file sets.
  - Import: reentrant workflows from raw reads (Nextflow, Fig 3.5). Queries use SQLite secondary indexes on genes, annotations, bins/ASVs and taxonomy. Interfaces are layered (files, then D3/Plotly GUI, then optional portal; Fig 3.6).
  - **Three analyses (Fig 3.3, 3.7):**
    1. Community modelling: map ASVs onto metagenomic bins from the same sample.
    2. Time series with a shared assembly: ScaDC snapshots share sequences and differ only in distribution, so deduplication is stricter.
    3. **Simulated HGT:** append a fosmid sequence to the host genome, rerun annotation, and model the metabolic change.
  - Objectives: build Engcyc; build upstream and downstream methods; demonstrate HGT and community-dynamics modelling.
  - Papers: MetaPathways v3.5 (submitted), Nextflow multi-omic modules (60%), Engcyc (30%).
- **Table 3.1** (L316-335) has 15 datasets, 12 of them fosmid libraries "organized by Dr. Kateryna Ievdokymenko":

  | Dataset | Description | Modals |
  |---|---|---|
  | ScaDC | oil-sands tailings, short-chain alkane culture, time series | G + F |
  | NapDC | oil-sands tailings, naphtha culture | G + F |
  | TolDC | gas-contaminated aquifer, toluene culture | G + F |
  | GUAG | Sakinaw Lake | G + F |
  | BeaverCecum | beaver gut | G + F + ASV |
  | BeaverColon | beaver gut | G + F + ASV |
  | Fos62 | mining bioreactor | F |
  | HogFuel | wood waste | F |
  | Lakelse | hot spring sediment | G + F |
  | NO_soil | natural site, organic horizon | G + F |
  | NA_soil | natural site, AE horizon | G + F |
  | CO_soil | clearcut site, organic horizon | G + F |

  The other 3 rows are chassis genomes: Cyanoverse (2,237 genomes including AB48), CB2A and EPI300. The 9 non-hydrocarbon libraries are "a palette of fosmid libraries used to screen for monoaromatic tolerance". **Saanich and Line P are not in Table 3.1.**
- **Annotation and modelling in the proposal:** CarveMe and COBRA/SBML appear once (L274). COMETS is the community target. metaGEM and ECSPr do not appear. Those live in the 2026 "all" doc and the scadc notes.

### Chapter structure (what exists)
- **There is no explicit "Chapter 1-4" list anywhere in the corpus or in Trilium.**
- Clues:
  - 26 Mar 2024 progress update: theme "Modelling the interoperability of biological systems". Three activities: metabolic effect of fosmids in E. coli; cyanobacteria and co-occurring microbes; a "data metabolism" for automated reproducible analysis.
  - Oct 2025: an Overleaf thesis template (project 68dc84205427ca92d6c2c0d9) whose **"Chapter 3" = Cyanoverse** (figs 3.3, 3.4).
  - 2026-05-04 committee talk: activities are now 1 Metasmith, 2 Fabfos (Metasmith applied to a small fosmid set), 3 Cyanoverse (Metasmith on metagenomics). Its publication units: Metasmith = "1 expected publication (Metasmith) and 2 chapters (**Engcyc**)", with "an additional thesis chapter (Engcyc) describing the final repertoire of integrated tools and producible data products". Fabfos = 1 pub (ScaDC) + 2 chapters. Cyanoverse = 1 pub + 2 chapters (Metasmith extensibility, scalability, portability). The closing slide "Layout of thesis chapters + Gantt" has no text in the transcript.
  - Notes Journal/2026-07-07: "My thesis is composed of three components: SCADC, Cyanoverse, and Metasmith."
  - The Trilium Thesis book (UhUS6uwo38DB) has Background, Fabfos, Metasmith, Metasmith-scratch (with an Engcyc child) and Cyanoverse.
- **My inference, not stated anywhere:** Ch1 intro/background, Ch2 Fabfos/ScaDC, Ch3 Cyanoverse (as in the Overleaf), and Ch4 Engcyc as the standalone data-product chapter the May 2026 talk promised. That fits Tony's "4th engcyc chapter". The Overleaf project is the one place that might settle it.

### Toluene manuscript drafts (v8 = 1N3XoW, v10 = 1dPYyN)
- **Title:** *Time-resolved pooled selection of a fosmid library for toluene tolerance traits in Escherichia coli*.
- **Story:**
  - Solvent tolerance is a multi-gene industrial trait. The paper builds and tests a fosmid pool-selection paradigm in EPI300.
  - The baseline MIC is 0.1% toluene: the control grows up to 0.05%, the ScaDC pool grows at 0.1%.
  - The ScaDC library (23,040 clones, 60 plates, Mildred Lake MFT short-chain alkane enrichment) was pooled into aliquots of about 8×10^7 cells.
  - Growth was unstable. The paper tests inoculum density, vitamins (MM+V) and recovery phases.
  - A 14-passage, 77-day experiment produced 33 sequenced pools, truncated at day 42.
  - 460 contigs formed 161 clusters, giving 132 NRCs that cover >99% of reads.
  - Clone diversity collapsed after about 3 passages.
  - The paper compares LCA* taxonomy and Kofam BRITE profiles against the metagenome (1.1 Gb, 153 bins) and against 6,710 end sequences (1/3 of the library). GSEA finds carbohydrate metabolism and secondary metabolite biosynthesis enriched.
  - Recovered genes: fatty acid, glycolipid, glycerophospholipid, LPS and isoprenoid biosynthesis, efflux and transporters, antioxidants, chaperones. These give a conceptual tolerance model.
  - The discussion is unfinished: notes on LoRA and black-box analogies, a missing no-toluene control, possible fosmid loss. The conclusion says "123 representative candidates", which conflicts with 132.
- **Figures (same in both versions):**
  1. Growth/toxicity panels A-E.
  2. Pie charts of clone abundance across the 33 pools.
  3. Phylum distributions (pools vs NRC vs ends vs metagenome).
  4. Functional distribution by BRITE level 2, plus GSEA.
  5. Gene content of NRCs at ≥50% abundance in any pool, with identity to host genes.

  Supplementary: Fig S1 (long-term passaging) and Tables S1-S7 (OD values, pool composition, ORF annotations, GFF3, BRITE mapping, LCA* taxonomy).
- **v8 → v10 changes:**
  - Joe C.H. Ho added as an author.
  - Citations converted to live Zotero links.
  - SCADC renamed ScaDC.
  - A new Methods section placed **before** Results. It covers the EPI300 genotype, the toxicity test, Echo 525 / MultiFlo pooling, JGI NovaSeq, BBDuk, SPAdes, multi-assembly clustering (MEGAHIT 478 contigs in 175 clusters vs metaSPAdes 460 in 161; metaSPAdes chosen), the minimap2/bedtools abundance method, the ScaDC metagenome SRR636559 (MEGAHIT then MetaWRAP, 153 MQ bins = 58.9% of reads), 7,043 end-sequence pairs (Lucy QC, GSC Sanger), and MetaPathways v3.5 / InterProScan / HMMER / LCA* / GSEA.
  - An outline block opens Results: "find MIT…, explore tolerance phenotypes, full timeseries".
  - The "new beyond this point" marker is removed.
  - The old Methods section is still at the end, so v10 has duplicate Methods.
  - Abstract, Results text, figures and Discussion are essentially unchanged.
- **The newer story, past both drafts (notes `scadc/sketch`, `scadc/outline`, `scadc/results/01`):**
  - The pCC1 junction method gives 170 inserts: 107 with 2 junctions, 47 with 1, 16 with none. They cover >96.4% of reads.
  - Clones 1 and 2 dominate. Both were isolated and long-read confirmed.
  - 4-lane annotation, ORA/GSEA (transcription factors enriched).
  - ECSPr predicts clone 2 raises carbon conductance toward lipids.
  - Lipidomics: clone 2 releases lipids under toluene, read as EV flushing. Clone 1 "remains a bit of a mystery".

## 3. Trilium (local vault; capella peer has no trilium)
- **Thesis** UhUS6uwo38DB (book). It has no outline text. Children:
  - **Fabfos** sdfr8KqVO1tw: footer quotes the talk's hypothesis and "fosmid = software chunk". Its children:
    - **Functional annotation** pwoC6BA8uxty ("DRAM, interproScan", 3 children; also cloned under Engcyc's child lTDRcaVIaKRa)
    - **ECSPr** UjsSw3ez9K5D (3 children; quotes from "all")
    - **SCADC** PFct1YUFNx5U ("short chain alkane degrading culture, pooled screen for toluene"), with children Recovering inserts oQVoBLqtU0II, Pool dynamics 0QFgoeq2S9kQ and Clone 2 strategy DLZNiJ9M13kr
  - **Metasmith** Sw33Cr03qLks: introduction uibiDBfqNolP, methods FaYHh3L03pev, results S1UaEEDCI92j (7 children), Discussion uVjbFFOoacKZ.
  - **Metasmith - scratch** 7ZjhwBWyeVuy, whose children include **Engcyc** pny12Z2ZozAa ("Engcyc is the intended library…"; quotes Engcyc d0 and the talk's "additional thesis chapter (Engcyc)"). Its children are lTDRcaVIaKRa and zP2cNyUklwlv (→ "Literature scape" FGlZYUfiQBil). Other scratch children: Type system, Compute niche reproducibility, Agentic systems, User Experience.
  - **Background** ANbgEM8kjDP9: Workflows & Compute, The information hierarchy, Microbial metabolism, Niches & Guilds, Metagenomics.
  - **Cyanoverse** roWQsa7IJp0y: Niches & Guilds, Ecological zoom (with the "DB glyph" canvas GuAHcXqsssUW, the only XGDB hit), Public data, Workflow, Cyanogroup presentation.
- Other relevant notes:
  - "arbutus admin & engcyc - deconstruct this" 9Jn9F3AQW0bB: Engcyc vision; run all data through metasmith; collect a table of datasets.
  - "Engcyc initial pipeline: tools, versions and output layout" KPyD19cbzVQm (agent card, 2026-10-17)
  - "engcyc manifest: push to capella and close the gaps" abeldlvfCi12
  - "Plan: bring engcyc.org back online on showtime" Owm2DsopdNvk / P1JnXTw3HYzU
  - "Fosmid library recovery" U5ytxtJPR3ix (Tom at Bio!, nanopore at 1.5k per pool with barcodes)
  - "Bio! fosmid 384 recovery" QDIi8vmTKLeS
  - Zotero notes for Ievdokymenko 2022 (tTd7ud7TuN7u, C9GxildlTRqf), Ievdokymenko 2015 (a586RxMtGQB8), FabFos (ZV02nWzW2riu), metaGEM (zJhnkTx2JeuR)
  - cKiATociDjzZ "fosdb-manuscript" is just this session's board card.
- **The scadc/\* notes are not in Trilium.** They are in the frozen `notes` source of the awm `search` archive (22 docs, origin altair; the files are not on altair's disk). Read them with `search get source=notes`:
  - scadc/sketch b8e1a447: full paper skeleton (above)
  - scadc/sketch/01_resolve_inserts fc6aec20
  - scadc/intro/01 2abfb8fb: full intro on dark matter, fosmids as a niche for gene programs, the GEM scale problem, intermediate-scale models, ECSPr. Includes a verified citation list of about 45 refs with PDFs at `../literature/pdfs/`.
  - scadc/outline 8660c862: figure plan
  - scadc/results/01 63773f94: insert recovery methods prose
  - scadc/results/lipidomics ccaf9871: points at `projects/scadc/lipidomics/.awm/data/figures/publish/04_lipidomics/…`
  - scadc/results/figures 3a350675: ECSPr heatmap SVGs
  - scadc/microscopy 449c50c8: "only 2 replicates, but there does seem to be a vesicle signal"
  - Journal/2026-07-07 (25619ddf), 07-09 and stt/07-09: thesis = SCADC + Cyanoverse + Metasmith; the 3-part ScaDC results.

## 4. Ievdokymenko 2022 thesis (doi:10.14288/1.0417274)
- **There is no local PDF on altair.** I searched the whole filesystem. scadc/intro/01 cites `../literature/pdfs/ievdokymenko_2022_functional_metagenomic_monoaromatic_tolerance_thesis.pdf` (fetched 2026-07-02), but that tree is not on this node and may be on capella. The kb has only the abstract (Zotero 65ZSNXQ8 / JKIDSXBF). The thesis is open access at https://open.library.ubc.ca/collections/24/items/1.0417274.
- **Abstract:** an EPI300 fosmid-pool selection paradigm covering design, pooled sequencing, assembly and annotation.
  - (i) **Nine fosmid libraries** were screened on inhibitory vanillin. They recovered conversion and tolerance traits: stress responses, transporters, cell-surface modification.
  - (ii) A larger screen on **seven lignin-derived monoaromatics** recovered the same clones across compounds, which points to non-specific tolerance. Growth on monoaromatics as sole carbon sources failed.
  - (iii) A toluene screen of **three hydrocarbon-enrichment pools** (NapDC, ScaDC, TolDC) recovered transport and cell-surface traits. Unstable growth led to the time-course experiment. Pool sequencing showed clone succession between early and later exposure phases.
- The nine libraries are probably the "palette… used to screen for monoaromatic tolerance" in proposal Table 3.1. The thesis's library list would confirm which nine.
- Caveat: scadc/intro/01 cites this as a "[Master's thesis]", but the proposal calls it her PhD thesis. Check the degree before citing.

## Gaps and next steps
- Sharknado reads need Tony's worker-01 unlock window. A cheaper route is the sharknado SQLite index on chinook Globus `/Resources/sharknado_index/`.
- The meaning of "v1.JGI_2025-03-21" ("sent to JGI on that date") is my inference. So is the purpose of the Annex 2 agreement. Ask Phoebe or Steven.
- Thesis chapter numbering: check Overleaf 68dc84205427ca92d6c2c0d9.
- Get the Ievdokymenko PDF from UBC Open Collections, or from capella's literature/pdfs if it is there.

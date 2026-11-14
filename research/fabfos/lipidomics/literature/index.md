# Lipidomics / metabolomics SOTA — corpus index

33 papers grounding the discussion of state-of-the-art untargeted lipidomics / metabolomics, with a focus on whether per-feature MS2 library annotation can be sidestepped via clustering + class prediction + cluster-level differential. Grouped by analytical bucket. See [`README.md`](README.md) for scope, search strategy, and build status; see [`../../../.awm/data/ai/lipidomics_sota_review.md`](../../../.awm/data/ai/lipidomics_sota_review.md) for the synthesis briefing.

Source tag in the rightmost column: **DR** = surfaced + verified by the deep-research workflow `wf_3f09963d-bac`; **manual** = foundational primary added by hand to cover buckets the search underweighted.

---

## Reviews / position papers (3)

| Citation | Year | Journal | DOI | Why included | Src |
|---|---|---|---|---|---|
| El Abiead et al. | 2025 | JACS Au (PMC12728610) | [10.1021/jacsau.5c00756](https://doi.org/10.1021/jacsau.5c00756) | Dorrestein-camp redefinition of "dark metabolome" as detected-but-unannotated; pushes back on Siuzdak/METLIN artifact framing. Quantitative annotation gap figures (52–87%) | DR |
| Chi, Mitchell, Li | 2025 | bioRxiv | [10.1101/2025.02.04.636472](https://doi.org/10.1101/2025.02.04.636472) | Li-camp position: per-feature ID is the unsolved bottleneck, not ion-grouping; explicit framing the briefing engages | DR |
| Li et al. (khipu) | 2023 | Anal Chem | [10.1021/acs.analchem.2c05810](https://doi.org/10.1021/acs.analchem.2c05810) | khipu MS1-only de novo compound grouping; the compound-level alternative to per-feature paradigm | DR |

## Molecular networking + clustering lineage (7)

| Citation | Year | Journal | DOI | Why included | Src |
|---|---|---|---|---|---|
| Wang et al. (GNPS) | 2016 | Nat Biotechnol | [10.1038/nbt.3597](https://doi.org/10.1038/nbt.3597) | GNPS classical molecular networking foundation | manual |
| Nothias et al. (FBMN) | 2020 | Nat Methods (PMC7885687) | [10.1038/s41592-020-0933-6](https://doi.org/10.1038/s41592-020-0933-6) | FBMN canonical; confirms timsTOF Pro PASEF support via MetaboScape/MS-DIAL/Progenesis upstream | DR |
| Schmid et al. (IIMN) | 2021 | Nat Commun (PMC8219731) | [10.1038/s41467-021-23953-9](https://doi.org/10.1038/s41467-021-23953-9) | MS1 peak-shape edges allow MS2-less features to join clusters; closest existing mechanism for the user's hypothesis | DR |
| Ernst et al. (MolNetEnhancer) | 2019 | Metabolites (PMC6680503) | [10.3390/metabo9070144](https://doi.org/10.3390/metabo9070144) | Family-level chemical class assignment; flag: score = consistency, NOT identity confidence | DR |
| Aksenov et al. (MCN) | 2024 | bioRxiv (PMC11312580) | [10.1101/2024.08.02.606356](https://doi.org/10.1101/2024.08.02.606356) | Louvain clustering on full-connectivity networks; 43→95% global GNPS connectivity. Author-confirmed: not cluster-level differential | DR |
| Huber et al. (Spec2Vec) | 2021 | PLOS Comp Biol | [10.1371/journal.pcbi.1008724](https://doi.org/10.1371/journal.pcbi.1008724) | Alternative similarity to cosine; potential matchms supplement in the existing pipeline | manual |
| Huber et al. (MS2DeepScore) | 2021 | J Cheminform | [10.1186/s13321-021-00558-4](https://doi.org/10.1186/s13321-021-00558-4) | DL similarity complementary to Spec2Vec | manual |

## Annotation / class prediction (10)

| Citation | Year | Journal | DOI | Why included | Src |
|---|---|---|---|---|---|
| van der Hooft et al. (MS2LDA) | 2016 | PNAS | [10.1073/pnas.1608041113](https://doi.org/10.1073/pnas.1608041113) | Mass2Motifs — MS2-substructure clustering foundational | manual |
| Dührkop et al. (CSI:FingerID) | 2015 | PNAS | [10.1073/pnas.1509788112](https://doi.org/10.1073/pnas.1509788112) | Structural ID via predicted molecular fingerprints | manual |
| Dührkop et al. (SIRIUS 4) | 2019 | Nat Methods | [10.1038/s41592-019-0344-8](https://doi.org/10.1038/s41592-019-0344-8) | SIRIUS pipeline foundational; molecular-formula ID from MS/MS isotope patterns | manual |
| Ludwig et al. (ZODIAC) | 2020 | Nat Mach Intell | [10.1038/s42256-020-00234-6](https://doi.org/10.1038/s42256-020-00234-6) | Gibbs-sampling refinement of SIRIUS formula scores across a dataset | manual |
| Dührkop et al. (CANOPUS) | 2020 | Nat Biotechnol | [10.1038/s41587-020-0740-8](https://doi.org/10.1038/s41587-020-0740-8) | Class prediction without structural reference; ~50% null on lipid spectra per MS2Lipid follow-up | DR |
| Goldman et al. (MIST) | 2023 | Nat Mach Intell | [10.1038/s42256-023-00708-3](https://doi.org/10.1038/s42256-023-00708-3) | Transformer for spectrum-to-structure; orthogonal DL alternative | manual |
| Higashi et al. (MS2Lipid) | 2024 | Metabolites (PMC11596251) | [10.3390/metabo14110602](https://doi.org/10.3390/metabo14110602) | XGBoost 97-subclass lipid classifier; orthogonal class-level annotation; NOT validated on timsTOF or bacterial subclasses | DR |
| Djoumbou Feunang et al. (ClassyFire) | 2016 | J Cheminform | [10.1186/s13321-016-0174-y](https://doi.org/10.1186/s13321-016-0174-y) | Chemical taxonomy underlying MolNetEnhancer / CANOPUS / NPClassifier | manual |
| Kim et al. (NPClassifier) | 2021 | J Nat Prod | [10.1021/acs.jnatprod.1c00399](https://doi.org/10.1021/acs.jnatprod.1c00399) | Deep-learning NP taxonomy; per-feature class predictor used inside MolNetEnhancer | manual |
| Kind et al. (LipidBlast) | 2013 | Nat Methods | [10.1038/nmeth.2551](https://doi.org/10.1038/nmeth.2551) | LipidBlast original — 26 classes, eukaryote-skewed; VS69 successor is what MS-DIAL ships | DR |

## Ion mobility / timsTOF / lipidomics workflows (8)

| Citation | Year | Journal | DOI | Why included | Src |
|---|---|---|---|---|---|
| Meier et al. (PASEF) | 2018 | Mol Cell Proteomics | [10.1074/mcp.TIR118.000900](https://doi.org/10.1074/mcp.TIR118.000900) | PASEF foundational; underlies SCADC acquisition mode | manual |
| Meier et al. (dia-PASEF) | 2020 | Nat Methods (PMC6965134) | [10.1038/s41592-020-0834-8](https://doi.org/10.1038/s41592-020-0834-8) | dia-PASEF reference; complement to DDA-PASEF | DR |
| Vasilopoulou et al. | 2020 | Nat Commun | [10.1038/s41467-020-14044-2](https://doi.org/10.1038/s41467-020-14044-2) | timsTOF lipidomics benchmark dataset (NIST SRM-1950) reused by Ross 2023 | manual |
| Ross et al. (MS-DIAL TIMS-PASEF benchmark) | 2023 | Molecules (PMC10142755) | [10.3390/molecules28083483](https://doi.org/10.3390/molecules28083483) | THE closest published validation for the SCADC pipeline; 440 lipid IDs vs Skyline 256 on Vasilopoulou data | DR |
| Zhou et al. (AllCCS) | 2020 | Nat Commun | [10.1038/s41467-020-18171-8](https://doi.org/10.1038/s41467-020-18171-8) | CCS prediction; orthogonal IM-based confidence layer | manual |
| Ross et al. (CCSbase) | 2020 | Anal Chem | [10.1021/acs.analchem.0c00427](https://doi.org/10.1021/acs.analchem.0c00427) | Reference CCS database; complement to AllCCS | manual |
| Liebisch et al. (LIPID MAPS shorthand) | 2020 | J Lipid Res | [10.1194/jlr.S120001025](https://doi.org/10.1194/jlr.S120001025) | LIPID MAPS nomenclature; the taxonomy MS2Lipid's 97-subclass system borrows from | manual |
| Sohlenkamp & Geiger | 2016 | FEMS Microbiol Rev | [10.1093/femsre/fuv008](https://doi.org/10.1093/femsre/fuv008) | Canonical bacterial PE/PG/CL biosynthesis + composition reference; SCADC domain anchor | manual |

## Cluster-level statistics + componentization (5)

| Citation | Year | Journal | DOI | Why included | Src |
|---|---|---|---|---|---|
| Barupal & Fiehn (ChemRICH) | 2017 | Sci Rep | [10.1038/s41598-017-15231-w](https://doi.org/10.1038/s41598-017-15231-w) | Cluster-level enrichment via chemical similarity; classifies >90% of identified metabolites — but operates on IDs, not unknowns (refuted at strong form) | DR |
| Li et al. (mummichog) | 2013 | PLOS Comp Biol | [10.1371/journal.pcbi.1003123](https://doi.org/10.1371/journal.pcbi.1003123) | m/z-only pathway activity; sidesteps per-feature ID for KEGG-mappable compounds | manual |
| Pang et al. (MetaboAnalyst 6.0) | 2024 | Nucleic Acids Res | [10.1093/nar/gkae253](https://doi.org/10.1093/nar/gkae253) | Current canonical stats platform; pathway / enrichment assumes per-feature IDs | manual |
| Kuhn et al. (CAMERA) | 2012 | Anal Chem | [10.1021/ac202450g](https://doi.org/10.1021/ac202450g) | Classical adduct/isotope ion-grouping in XCMS | manual |
| Broeckling et al. (RAMClustR) | 2014 | Anal Chem | [10.1021/ac501530d](https://doi.org/10.1021/ac501530d) | RT-correlation feature clustering / componentization | manual |

---

**Summary:** 33 entries · 13 DR-verified · 20 manual foundational · 0 PDFs on disk (deferred — see README "Build status").

**Adversarially verified findings** behind the corpus (vote `for-against`): see briefing §3 + §3.5. Three claims killed: FBMN does not itself propagate annotations along edges (0–3); ChemRICH does not classify all unknowns (1–2); CANOPUS does not deterministically predict 2,497 classes (1–2). The corpus entries reflect each tool's *actual* scope per the refuted versions.

**Known coverage gaps:**
- No published benchmark of MSDIAL-LipidBlast VS69 on bacterial PE/PG/CL/hopanoid/BHP classes.
- No published evaluation of `--combineIonMobilitySpectra` information loss.
- No published evaluation of MS2Lipid on timsTOF DDA-PASEF or bacterial subclasses.
- bioRxiv 2025–2026 DDA-PASEF lipidomics sweep not completed (acknowledged in briefing §6).

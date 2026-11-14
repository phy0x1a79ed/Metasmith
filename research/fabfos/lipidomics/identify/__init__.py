"""Identification lane for the clone-response lipid hits.

The facility's MetaboScape pass named 182/3095 features, searching Bruker
MetaboBASE, NIST23, an HMDB target list and the MS-DIAL LipidBlast VS69 atlas.
Two in-house re-runs against that same atlas returned nothing. This package
therefore does not re-search those libraries; it uses the evidence the facility
table already carries but never exposed (deconvoluted neutral mass, adduct, CCS,
MS/MS-acquired flag) plus the raw runs, against sources the facility did not use.

Two lanes share this code. The IDENTIFICATION lane asks what 29 specific features
are. The CLASSIFICATION lane asks a coarser question -- phospholipid or not, which
headgroup, what shape -- of all 2180, because an enrichment test needs a null and
7% class coverage cannot supply one. They write to separate files throughout;
`extract_spectra` and `headgroup` take a `lane` argument for exactly that reason.

Identification lane:
  build_manifest  -- the 29 hit features + every column the loader discards   (T1)
  massdb          -- offline neutral-mass search against the RefMet dump      (T1)
  formula         -- CHNOPS formula enumeration under lipid constraints       (T2)
  webapi          -- cached clients for LIPID MAPS / RefMet / FASST / MassBank(T2,T3)
  extract_spectra -- MS2 consensus per feature, pulled from the mzML          (T3)
  grade           -- merge, MSI confidence, publish                           (T4)

Classification lane:
  full_manifest        -- all 2180 analysed features, same columns
  extract_spectra --full
  headgroup            -- mass-balance backbone call + shape, three-state
  headgroup_validate   -- confusion matrix vs the held-out facility labels
  headgroup_enrichment -- the statistics, indeterminates bounded not dropped
  cl_bound             -- what cardiolipin would look like, and how absent it is

Environments are split deliberately: everything here runs under `p312` except
`extract_spectra` and `cl_bound`, which need pyteomics and run under `lipidomics`.
"""

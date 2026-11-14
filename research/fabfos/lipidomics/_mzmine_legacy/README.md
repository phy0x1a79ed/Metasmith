# MZmine 4 pipeline (legacy — do not run)

The lipidomics pipeline used to peak-pick / annotate / align with MZmine 4 via
the files here:

- `pipeline_{pos,neg}.mzbatch` — generated batches
- `build_mzbatch.py` — surgical editor from the references below
- `reference_lc_tims.mzbatch` — MZmine 4.8 LC+TIMS integration-test batch
- `reference_lipid_annotation.mzbatch` — published cassava-fermentation lipidomics LipidAnnotation block
- `run_mzmine.sh` — the headless driver

Why deprecated: MZmine 4 hard-requires an `.mzuser` login (free, but
interactive) for every batch run, which violates the autonomy requirement.
The active pipeline is the MS-DIAL one in `../` (see `../../README.md`).

Why kept: the bacterial-relevant `LIPID_CLASSES` list and the cross-version
mass / RT / mobility tolerances captured here remain a useful audit trail
when re-tuning the MS-DIAL parameters.

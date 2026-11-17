# SCADC lipidomics

## Purpose & Contents

Research code for the SCADC lipidomics and vesicle imaging arm. It holds the analysis scripts, the vesicle panel generators and the open discussion. Outputs live in DVC, not git. It is research only. Nothing here is a metasmith module yet.

## Origin

This lane moved from the archived `scadc/lipidomics` scope, branch `feat/lipidomics` at `6f28eb2`. Git history stays in that repo. Read its journals with `search` for the reasoning behind each script.

## Layout

- Raw and processed MS data: `data/fabfos/runs/scadc_lipidomics/` (DVC). `msms/` holds the timsTOF `.d` runs. `facility/` holds the MetaboScape table. `processed/` holds every derived table.
- Imaging data: `data/fabfos/runs/scadc_microscopy/` (DVC).
- Vesicle measurement tables: `data/fabfos/runs/scadc_vesicle_results/` (DVC). `vesicle_common.RESULTS` names it.
- Rendered lipidomics figures: `data/fabfos/runs/scadc_lipidomics_figures/` (DVC).
- Per-injection MZmine ion reads: `data/fabfos/runs/scadc_mzmine_parquet_v1/` (DVC). `mzmine/README.md` covers how they are made.
- Feature tables, one per observation (pel+, pel−, sup+, sup−): `data/fabfos/runs/scadc_feature_tables_v1/` (DVC). Rebuild them and the ordination page with `mamba run -n python_for_data_science python -m align <page.html>` from this directory. `checks.json` there holds every check the page shows. Each stage also runs alone from the saved tables, so redo only what changed: `python -m align.ordinate` (CLR PCA), `python -m align.mi` (pairwise MI and its bootstrap, the slowest step, about a minute on nibi), `python -m align.page <page.html>` (layout only).
- **CAUTION:** the raw files spell two strains differently. `Epi300` and `ESi300` are EPI300. `EpCC1` and `ESCC1` are PCC1. `align/load.py` applies this rename once at import and refuses an unmapped label. Every table under `scadc_feature_tables_v1/` uses the corrected names. `strain_recorded` keeps the spelling from the file.
- `metadata.csv` and `od_values.csv` stay in git. They are hand-curated inputs, not outputs.
- **CAUTION:** a DVC-pinned file is a read-only hardlink. Write a new file and rename it over the old one, as `align/load.save` does. Never write into the pinned file. Then run `dvc add` on the chunk and commit the pin.
- **CAUTION:** in every ordination, PC1 partly tracks sample loading. Within conditions it correlates with log size factor (r up to 0.5), and loading also differs between conditions, so part of the condition separation may be loading rather than composition. OD normalisation is being handled in a separate thread.
- Envs: `envs/fabfos/lipidomics.yml`, `imaging.yml`, `ms2lipid.yml`.
- `discussion/` is the dfs-interview folder for the Armando presentation. Run its `stack.py` against that path.
- `lipidio.py` owns the data paths. Take paths from its constants.

## Known gaps

- **CAUTION:** scripts that publish figures still write to `.awm/data/figures/publish/`, a path that does not exist in this repo. Pick a publish root before rerunning them.
- The MS-DIAL and MZmine pipelines here (`run_msdial.sh`, `_mzmine_legacy/`) are retired. The `align/` feature tables replace the facility MetaboScape table. The older `diff_*`, `composition*` and `od_*` scripts still read MetaboScape.
- The vesicle renders were gitignored in the old scope and were not carried over. Rerun the generators in `vesicle_panels/`.

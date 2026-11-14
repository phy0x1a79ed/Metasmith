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
- `metadata.csv` and `od_values.csv` stay in git. They are hand-curated inputs, not outputs.
- **CAUTION:** a DVC-pinned file is a read-only hardlink. Unlink it before a generator rewrites it. Then run `dvc add` on the chunk and commit the pin.
- Envs: `envs/fabfos/lipidomics.yml`, `imaging.yml`, `ms2lipid.yml`.
- `discussion/` is the dfs-interview folder for the Armando presentation. Run its `stack.py` against that path.
- `lipidio.py` owns the data paths. Take paths from its constants.

## Known gaps

- **CAUTION:** scripts that publish figures still write to `.awm/data/figures/publish/`, a path that does not exist in this repo. Pick a publish root before rerunning them.
- The MS-DIAL and MZmine pipelines here (`run_msdial.sh`, `_mzmine_legacy/`) are retired. The facility MetaboScape table is the working dataset until our own MZmine 4 ion tables land.
- The vesicle renders were gitignored in the old scope and were not carried over. Rerun the generators in `vesicle_panels/`.

<!-- excerpt of findings/E1_E2_REPRODUCTION.md, copied by measure.py -->
## nf-core processes against metasmith steps

| arm | e2_transform | nfcore_processes | completed_tasks (E1 / E2) |
|---|---|---|---|
| short | bowtie2_binning_bam | BOWTIE2_ASSEMBLY_ALIGN + BOWTIE2_ASSEMBLY_BUILD | 506 / 442 |
| short | checkm2 | CHECKM2_PREDICT | 1039 / 146 |
| short | comebin | COMEBIN | 208 / 208 |
| short | das_tool | DASTOOL | 208 / 420 |
| short | fastp | FASTP | 208 / 208 |
| short | fastqc_raw | FASTQC_RAW | 208 / 208 |
| short | fastqc_trimmed | FASTQC_TRIMMED | 208 / 208 |
| short | megahit | MEGAHIT | 208 / 208 |
| short | metabat2 | JGISUMMARIZEBAMCONTIGDEPTHS + METABAT2 | 419 / 420 |
| short | semibin2 | SEMIBIN_SINGLEEASYBIN | 215 / 208 |
| short | amber | (scoring, outside nf-core/mag) | 0 / 609 |
| short | gold_standard | (scoring, outside nf-core/mag) | 0 / 417 |
| short | (no transform) | BIN_SUMMARY + CONCAT_CHECKM2_TSV + FASTATOCONTIG2BIN + GUNZIP + MAG_DEPTHS + MAG_DEPTHS_SUMMARY + MULTIQC + PRODIGAL + QUAST + RENAME_POSTDASTOOL + RENAME_PREDASTOOL + SEQKIT_STATS + SPLIT_FASTA | 3537 / 0 |
| long | checkm2 | CHECKM2_PREDICT | 164 / 30 |
| long | chopper | CHOPPER | 41 / 82 |
| long | comebin | COMEBIN | 41 / 41 |
| long | das_tool | DASTOOL | 41 / 42 |
| long | flye | FLYE | 41 / 41 |
| long | metabat2 | JGISUMMARIZEBAMCONTIGDEPTHS + METABAT2 + METABAT2_B19_RERUN | 123 / 44 |
| long | minimap2_binning_bam | MINIMAP2_ASSEMBLY_ALIGN + MINIMAP2_ASSEMBLY_INDEX | 82 / 82 |
| long | porechop_abi | PORECHOP_ABI | 41 / 82 |
| long | semibin2 | SEMIBIN_SINGLEEASYBIN | 41 / 41 |
| long | amber | (scoring, outside nf-core/mag) | 0 / 123 |
| long | gold_standard | (scoring, outside nf-core/mag) | 0 / 82 |
| long | (no transform) | B19_MERGE_BOOKKEEPING + B19_ROWS_BOOKKEEPING + BIN_SUMMARY + CONCAT_CHECKM2_TSV + CONCAT_QUAST_SUMMARY + FASTATOCONTIG2BIN + GUNZIP + MAG_DEPTHS + MAG_DEPTHS_SUMMARY + MULTIQC + NANOPLOT_FILTERED + NANOPLOT_RAW + PRODIGAL + QUAST + QUAST_BINS + RENAME_POSTDASTOOL + RENAME_PREDASTOOL + SEQKIT_STATS + SPLIT_FASTA | 827 / 0 |

The map is per step, not per process. nf-core runs 12 tool-bearing processes on the short arm and 11 on the long arm. E2 runs the same tool calls as 10 and 9 transforms, because three transforms each hold two nf-core processes:

- `bowtie2_binning_bam` holds `BOWTIE2_ASSEMBLY_BUILD` and `BOWTIE2_ASSEMBLY_ALIGN`.
- `minimap2_binning_bam` holds `MINIMAP2_ASSEMBLY_INDEX` and `MINIMAP2_ASSEMBLY_ALIGN`.
- `metabat2` holds `JGISUMMARIZEBAMCONTIGDEPTHS` and `METABAT2`.

`METABAT2_B19_RERUN` is E1's hand rerun, not an nf-core process. The `(no transform)` row lists nf-core's bookkeeping, format-conversion and report processes. E2 does the conversions its tools need inside the transform and runs no report steps. `amber` and `gold_standard` were E2's scoring steps, which nf-core does not ship.


# PSORTm pilot

Measures what the psortm lane costs and how it calls envelopes, before it ran on real MAGs.
The scripts run the lane's own `resources/lib/psortm/psortm_prep.py` and `psortm.sh` in the
pinned image (`resources/env/psortm.env`), with the network off.

    bash fetch_genomes.sh <genomes_dir>    # 12 RefSeq proteomes
    bash run_pilot.sh <psortm.sif> <genomes_dir> <work_dir> [jobs=12] [chunk=1000]

`make_inputs.py` stages each proteome as one MAG with Prodigal-style ORF ids and a GTDB r232
lineage, `run_psortm.sh` times one chunk, and `summarise.py` writes the tables below.

## Results (altair, 2026-11-27)

47,611 proteins in 52 chunks of 1,000, 12 at a time, on a 16-core host that other jobs held at
a load of 23 to 30. Rates are proteins over user plus system CPU time, so the contention costs
some cache but no queueing.

| genome | true envelope | PSORTm envelope | ORFs | proteins / core-hour | peak RSS (MB) | Unknown % |
|---|---|---|---:|---:|---:|---:|
| E. coli K-12 | diderm | neg | 4,300 | 4,845 | 167 | 22.6 |
| P. aeruginosa PAO1 | diderm | neg | 5,572 | 5,022 | 181 | 21.7 |
| B. thetaiotaomicron | diderm | neg | 4,645 | 4,581 | 170 | 30.5 |
| B. subtilis 168 | monoderm | pos | 4,237 | 6,051 | 114 | 17.6 |
| S. coelicolor | monoderm | pos | 7,872 | 5,841 | 130 | 21.9 |
| V. parvula | diderm Firmicute (LPS outer membrane) | pos (wrong) | 1,837 | 4,895 | 107 | 15.1 |
| D. radiodurans | diderm, Gram-positive stain | neg | 3,134 | 4,901 | 164 | 35.3 |
| M. tuberculosis | mycomembrane | pos | 3,906 | 5,406 | 111 | 19.5 |
| C. glutamicum | mycomembrane | pos | 2,941 | 5,704 | 104 | 17.5 |
| M. pneumoniae | no wall, no outer membrane | adv_neg | 672 | 5,294 | 100 | 32.0 |
| M. acetivorans | archaeon | archaea | 4,627 | 5,868 | 120 | 15.7 |
| H. volcanii | archaeon | archaea | 3,868 | 5,768 | 107 | 13.0 |

All genomes: 8.9 core-hours, 5,351 proteins per core-hour. A 1,000-protein chunk took 10 to
15 minutes of wall time, about 10 s of it copying the taxonomy indexes out of the image.

Unknown by envelope: Gram-negative 22 to 31%, Gram-positive 18 to 22%, archaea 13 to 16%. The
two atypical envelopes are the highest: D. radiodurans 35%, M. pneumoniae 32%.

## What it means for the lane

- **The envelope is a phylum lookup.** PSORTm 1.0.2 resolves the taxon name to an NCBI 2017
  phylum and reads a 27-row table. The Omp85 marker in the paper is not in the shipped code. The
  table has no diderm Firmicute row, so V. parvula runs as Gram-positive: its proteins can never
  be called outer membrane or periplasmic. Its `Deinococcales` row is never reached, so
  Deinococcota run as Gram-negative. PSORTb has no mycomembrane model, so Mycobacteriales run as
  Gram-positive.
- **A GTDB name must be translated.** GTDB phyla (Pseudomonadota, Bacillota_C) are not in the
  2017 taxonomy, and GTDB files the Mollicutes under Bacilli. `psortm_prep.py` maps the GTDB
  lineage to the NCBI-era phylum PSORTm resolves. Without the Mollicutes row M. pneumoniae runs
  as Gram-positive. A phylum outside the table (Patescibacteriota, Gemmatimonadota) is passed
  through, and PSORTm runs none of its proteins.
- **Sizing.** One core, about 5,000 proteins an hour, under 200 MB. The lane chunks at 5,000
  ORFs with 2 GB and 4 hours. A sample with 500,000 ORFs on quality MAGs is about 100 core-hours.

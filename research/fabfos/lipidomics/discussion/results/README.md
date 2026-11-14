# results

## Purpose & Contents

The result of the results topic: what the existing lipidomics results show, and which of them the Armando deck carries. Survey findings sit under Survey until the user confirms the cut.

## Survey

### Design

- Four cultures: EPI300 (no vector), EpCC1 (empty pCC1 vector), Clone1, Clone2. Each culture is grown ±0.1% toluene, n=3, for 6 days in M9-glucose.
- Each culture yields a pellet (P) and a supernatant (S) fraction. EPI300 fractions carry the labels `Epi300` (P) and `ESi300` (S). EpCC1 fractions carry `EpCC1` (P) and `ESCC1` (S).
- OD600 at harvest is in `research/fabfos/lipidomics/od_values.csv`. Toluene drops EPI300 OD about 3x and EpCC1 OD about 5x. Clone OD barely moves.

### What toluene does (existing results)

- Raw or median-normalized, toluene changes almost nothing.
- Per OD, toluene raises total lipid 2.5–2.6x in EPI300 and EpCC1 pellets, and 3.3–6.2x in their supernatants. Clone1 and Clone2 stay at 1.0–1.2x (`data/fabfos/runs/scadc_lipidomics/processed/metaboscape/od/od_total_lipid.csv`).
- Much of that rise is a shrinking OD denominator. Raw lipid signal barely moves while OD falls.
- The headgroup mix stays conserved under toluene. Nothing survives FDR.
- Chain architecture diverges by clone, even without toluene. Clone2 runs longer and more unsaturated. Clone1 runs shorter and more saturated. The empty-vector controls show the textbook saturate-under-toluene move. The clones do not.
- Quinones run lower in both clones than in the parent. Armando's "quinones decrease under toluene" is a biomass effect: per OD, they rise.
- Caveats: about 7% of features are annotated. PC calls are likely misannotations. n=3. On the canonical clone-vs-pCC1 grid nothing survives Holm. The OD rep index is assumed to match the lipidomics rep index.

### Sample identity check

`research/fabfos/lipidomics/sample_identity.py` correlates each sample to each group's mean, leaving the sample out. It uses features present in at least 90% of a fraction's samples, log2 and median-normalized.

- Culture **EpCC1 ctrl rep 2** matches EPI300 ctrl, not EpCC1 ctrl, in both fractions:
  - Pellet `EpCC1_ctrl_P_2`: r=0.55 to Epi300 ctrl, r=0.30 to its own group.
  - Supernatant `ESCC1_ctrl_S_2`: r=0.60 to ESi300 ctrl, r=-0.25 to its own group.
- The two fractions come from one culture but were extracted and run separately. Two independent readouts agree, so the mislabel sits at the culture or tube level, not at the injection.
- The other pCC1-carrying supernatants (ESCC1 ctrl reps 1 and 3) resemble Clone2, which also carries pCC1. Rep 2 lacks that shared vector signature.
- The other off-group calls are weak (best-match margins under 0.15) and run within clone/tolerance neighbourhoods. They are not swap candidates.

### Blind clustering

`research/fabfos/lipidomics/sample_clustering.py` uses the same feature subset: 2180 QC-passed MetaboScape features, cut to those present in at least 90% of a fraction's samples (614 pellet, 424 supernatant). Average-linkage correlation clustering, with labels applied afterwards:

- Supernatant k=3 splits by strain: Clone2 + pCC1 carriers, EPI300 + `ESCC1_ctrl_S_2`, Clone1. Toluene does not drive the top split.
- Pellet is noisier. One cluster is Epi300 ctrl + `EpCC1_ctrl_P_2`. Toluene-stressed EpCC1 groups with Clone1.

### Prior journals

No prior journal flagged a swap. Prior work never checked sample identity. It treated the OD rep pairing as the open labelling risk. Every clone-vs-pCC1 and EpCC1-toluene contrast so far carries an EPI300 culture in its EpCC1 ctrl group.

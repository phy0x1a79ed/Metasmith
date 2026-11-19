# Intro and Discussion outline (2026-11-19, in progress)

Shared spine: the intent → planning → execution gap (Fig. 1), and the four paradigms (dataflow, build, service, declarative). Metasmith sits in the declarative class. The Intro poses the problem and the lineage, with no verdicts on Metasmith. The Discussion places Metasmith, with verdicts, on the same layers. Discussion structure from the sister session (`STACK-discussion.md` on feat/engine/manuscript-b).

## Themes

T1 dataflow and build roots · T2 service paradigm, Taverna, decay, FAIR · T3 the gap · T4 four paradigms · T5 types (EDAM coarse, BioMoby/SADI, CWL) · T6 query model (System R, SADI/SPARQL, Make) · T7 planners and solvers · T8 LLM agents (Biomni, AutoBA, BixBench) · T9 tree search (AlphaZero, Segler) · T10 why declarative systems failed, and Metasmith's answers · T11 accessibility–expressiveness trade-off · T12 Loach, partition B, comparison set · T13 additive to Nextflow, convergence · T14 limitations · T15 compute market · T16 results recap

## Intro

- P1 roots: dataflow, build (Make) [T1]
- P2 services: grid, Taverna, decay, FAIR (11–14 + Loach) [T2]
- P3 framing: the gap (Fig. 1); paradigms per layer; types as the shared vocabulary; optional query analogy [T3 T4 T5 T6]
- P4 execution: dataflow mature; CWL types check ports; runs only what is written [T13]
- P5 planning: manual curation; Snakemake filenames; declarative planners; Lamprecht barriers + service decay [T7 T10]
- P6 intent: formal = expressive but expert-only; Galaxy/LLM = accessible but unchecked; gatekept [T8 T11]
- P7 Metasmith: declarative across intent and planning; structural types; tree search; compiles to Nextflow; demo [T9]

## Discussion

- D1 recap: gap and solution; evidence; bridge [T16]
- D2a concerns (evaluation papers) → Loach regrouped (partition B); Loach treats interoperability only under FAIRness and omits automated composition; trade-off principle; Table 1 [T12 T11]
- D2b execution (Basic computing, Scalability, Security, Cost, Reproducibility): additive to Nextflow; compilation answers the missing path to execution; convergence [T13 T10]
- D2c planning (Functions, Flexibility): peers failed on annotation and ranking; types with transforms, cost ranking [T10 T7]
- D2d intent (Usability, Learnability, Support): centre of the trade-off; formalism barrier; trust; LLM contrast [T11 T8 T10]
- D2e ecosystem (FAIRness, Sustainability): service decay; good-enough curation → D3, D4 [T2 T10]
- D3 limitations [T14]
- D4 future: compute market; LLM front end over the typed solver [T15 T8]
- Conclusion

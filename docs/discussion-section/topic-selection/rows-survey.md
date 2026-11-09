# Rows survey (subagent, 2026-11-09)

Background survey for the question "Which systems are the table's rows?". [V] = citation checked against a source this session; [I] = from model knowledge, check the DOI before citing.

Already in Zotero: Nextflow (Di Tommaso 2017), Snakemake (Köster & Rahmann 2012; Mölder 2021), Galaxy (Schatz 2005 only).

| System | Topology | Data type | Control flow | Execution | Tool choice | Citation |
|---|---|---|---|---|---|---|
| Nextflow/nf-core | hand-written dataflow | untyped channels | branch, when, recursion | own engine, -resume | none | Di Tommaso 2017 nbt.3820 [V]; Ewels 2020 [V] |
| Snakemake | backward filename-rule chaining | wildcards | Python conditionals, checkpoints; no loops | own engine | none | Köster 2012 bts480; Mölder 2021 [I] |
| CWL v1.2 | hand-written | File + EDAM `format`, weakly checked | `when`; loops only as extension | spec; cwltool/Toil; CWLProv | none | Crusoe 2022 CACM 10.1145/3486897 [I] |
| WDL/Cromwell | hand-written | nominal static types | if; no loops | Cromwell/miniwdl, call caching | none | weak citation; prefer OpenWDL docs [I] |
| Galaxy | GUI canvas | nominal datatypes, part EDAM | conditional steps; no loops | own engine, history provenance | suggests compatible tools | Galaxy Community 2024 NAR gkae410 [I] |
| Pegasus | hand-written abstract DAG | logical files | none | DAGMan | picks sites, not tools | Deelman 2015 [I] |
| Janis | Python | nominal, checked at connect | none | transpiles to CWL/WDL | none | Whitington 2022? [I, verify] |
| BioShake | Haskell EDSL | phantom types + type classes for file properties (closest to structural) | host language | compiles to Shake | none | Bedő 2019 PeerJ 10.7717/peerj.7223 [V] |
| APE (+Workflomics) | SAT/temporal-logic synthesis | EDAM terms with subsumption | none; linear sequences [I] | no execution; CWL export [I] | enumerates; Workflomics benchmarks candidates | Kasalica & Lamprecht 2020 ICCS 10.1007/978-3-030-50436-6_34 [V]; Palmblad 2021 JPR [V] |
| Wings | semantic templates elaborated by OWL constraints | OWL classes + metadata | none | Pegasus; OPMW provenance | specializes abstract components | Gil 2011 IEEE Intell Syst [I] |
| Dagster/Airflow | Python | Dagster typed assets; Airflow untyped | branch | own schedulers | none | docs only |
| LLM agents | LLM plans steps | none | generated scripts | generated code, no formal provenance | LLM heuristic | AutoBA: Zhou 2024 Adv Sci 10.1002/advs.202407094 [V]; BioMaster: Su 2025 bioRxiv 10.1101/2025.01.23.634608 [V]; BioAgents: Mehandru 2025 Sci Rep 15:39036 [V] |

Possibly missed, verify: Workflomics (Kasalica et al., ~2024–25) — APE synthesis plus benchmarking of candidates, the most direct competitor; PROPHETS/jABC (APE's ancestor); Galaxy tool recommendation (Kumar 2021 GigaScience).

Subagent's shortlist: Nextflow/nf-core, Snakemake, CWL, Galaxy, BioShake, APE+Workflomics, Wings, LLM agents.

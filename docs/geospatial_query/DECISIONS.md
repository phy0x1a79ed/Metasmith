# geospatial_query decisions

## reply-tomer (2026-11-17)
- Question: how to answer Tomer's open questions on the Evidence column and Postgres.
- Decision: the user wrote and sent the reply. It explains the Evidence column, states no prior opinion on Postgres, accepts the KML AOIs as the test set and says the pipeline is in progress.
- Landed: sent by email 2026-11-17.

## aoi-handling (2026-11-19)
- Question: where Koonkie's AOI file and the run outputs live.
- User: "it is data and im not under non disclosure. dvc track it?" and "I want the same layout for these AOIs" as the cyanoverse and engcyc datasets.
- Decision: the KML and outputs go in the metasmith data view under data/geospatial_query/<dataset>/, DVC-tracked, in the engcyc LAYOUT.md grammar.
- Landed: PLAN.md tasks T2, T3, T6.

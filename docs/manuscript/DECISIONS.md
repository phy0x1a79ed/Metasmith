# Engcyc manuscript — decisions

Stack: `docs/manuscript/STACK.md`.

## framing — 2026-11-15

**Question.** Does the Engcyc chapter establish the data framework on its own, or does Cyanoverse serve as the case study that establishes it?

**Tony.** "Agree on framing."

**Decided design.**
- The Engcyc chapter (thesis aim A3) establishes the data framework on its own: the metadata-first manifest, the output layout (`research/engcyc/LAYOUT.md`) and the XGDB format.
- Several entries demonstrate it, as the E1–E5 reproductions demonstrated Metasmith:
  - Cyanoverse is the pilot entry and the largest one, and the layout was derived from it.
  - The other entries are the E5 data sets, the fosmid libraries (ScaDC and others) and AB48.
- The Cyanoverse paper stays a biology paper and cites Engcyc. It keeps two framework points (option A in its gather, `cyanoverse/manuscript/gather/00_overview.md`):
  - the census, as data that fails FAIR and so motivates the manifest
  - the pipeline, as a resource
- The chapter depends on two things:
  - The XGDB format is written in code. It is not yet; see precedent 35be6211.
  - At least Cyanoverse and one E5 data set are published into the format. Cyanoverse first needs its three gaps closed (51a3a2b9): a driver from reads to assembly and genes, the rest of the viral analysis, and an abundance matrix.

**Landed.** This file. Journal post to metasmith/engcyc/manuscript, for the cyanoverse-manuscript session.

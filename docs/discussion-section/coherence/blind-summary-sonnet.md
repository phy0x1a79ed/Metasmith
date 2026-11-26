# Blind summary (Sonnet, 2026-11-25)

Input: coherence/discussion-2026-11-25.txt only (7 paragraphs: D1, 2a, 2b, 1a, 1b, 1c, 3).

**Thesis.** Metasmith derives pipeline routing from typed contracts via a planner, which makes tools interoperable and reusable; LLM agents and planners complement each other, and users own the whole stack.

**Claims read back**
- A. Much pipeline topology can be derived from per-tool contracts over a shared type vocabulary, so adding a tool takes one contract.
- B. Types must describe the state data have reached, not just what it is; earlier systems did not.
- C. No standard vocabulary exists, and Metasmith does not impose one; it offers a principle and leaves adoption to use.
- D. Manual routing makes the developer carry the cost of modularity, causing reimplementation; derived routing aligns incentives.
- E. Planning gives valid, reproducible, checkable plans; earlier planners were held back by weak types and execution; no conditional or cyclic planning yet.
- F. Agents alone fail at the joins; types and planning make joins checkable; agents and planners are complementary.
- G. Typed contracts serve users at different expertise levels; Nextflow gives portability and ownership; limitations; compute market as future work.

**Per paragraph:** P1→A, P2→B, P3→C, P4→D, P5→E (leads into F), P6→F, P7→G.

**Trouble spots**
- P1 opens results-style and overlaps P2 ("described once ... one contract" twice).
- P1's evidence ("reproduce and capture ... well-developed to bespoke") is never returned to.
- P3: "Users own the vocabulary as they own the rest of the stack, so our claim is narrower": uses "own the stack" before P7; the "so" does not follow. How local namespaces become interoperable is asserted, not argued; conceding no standard weakens P1's headline without the connection being drawn.
- P5: "two things held them back" then a third item (acts before execution); strong/conditional/cyclic detail is a limitation, not a reason earlier planners failed. Metasmith's own answer to execution (compiling to Nextflow) is never stated.
- P6: longest; pivot comes late; "only types make a join checkable" strong and unsupported in the paragraph.
- P7 mixes interface levels, Galaxy comparison, limitations, compute market; market has no setup; ownership repeats P3; opening loosely tied to P6; section ends on speculation, not the thesis.
- Limitations scattered (P5, P7); P1's "radical interoperability" not qualified.

**Gap (my note, not the reader's):** the three intended claims were read as seven (A-G), one per paragraph.

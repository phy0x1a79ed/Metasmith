# Limitations

## Survey

Candidate limitations, drawn from the d2 draft (Results, Methods, Discussion fragments):

1. **Topology conflates two partitionings.** Each contract maps 1:1 to an execution step. Conceptual grouping and resource-homogeneous grouping do not converge; re-batching steps for contigs and ORFs exist only for logistics. (d2 Discussion fragment a.)
2. **No conditionals or loops.** Routing has only group-by and split. Branching on a runtime condition or iterating until convergence is not expressible, except inside a contract. (d2 heading b; Methods L98.)
3. **Domain expertise still required.** The solver wires; it does not choose. Redundant contracts (e.g. two assemblers) are not ranked by quality, and someone must curate the library. (d2 fragment c.)
4. **Shared property vocabulary.** Structural typing avoids a central type authority, but contracts written apart only chain when they share property names. Results claims the first without naming the second.
5. **Solver guarantees.** PUCT search is bounded and lineage makes it path-dependent, so the plan is not guaranteed minimal. (Methods.)
6. **Evidence limits.** The effort argument rests on lines of code, and the linear-versus-quadratic growth is an expectation, not a measurement. The accessibility claim has no user study. Reproductions were made by the developers with AI help.
7. **Reproduction scope.** Viromics reproduced only the vOTU core (78.5% recall); metaGEM started from MAGs.
8. **Execution coverage.** Only the local and SLURM executors were tested.

## Decisions

(none yet)

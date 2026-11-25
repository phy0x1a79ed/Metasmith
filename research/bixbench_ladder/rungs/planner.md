The machine also has a workflow planner, `bx`, built on Metasmith. Every step in the tool reference above, and every other step in the catalogue, is a typed step that the planner runs for you with its tested script. You declare which of your files is which data type and name the type you want. The planner finds the chain of steps that produces it and runs the chain.

Prefer the planner to writing a step by hand. When a step covers part of the analysis, run that part with `bx run` and do the rest in your own code. Write the whole analysis yourself only when no step fits.

    bx types [WORD]     list data types: the file layout of each and the step that makes it
    bx steps [WORD]     list steps: inputs, outputs and parameters
    bx add FILE TYPE    declare that a file is a type
    bx plan TYPE ...    show the chain of steps, without running it
    bx run TYPE ... [-p PARAMETER=VALUE ...]
                        run the chain and print the path of each result file

For example, differential expression from a count table and a sample sheet is three calls:

    bx add /workspace/counts.csv count_matrix
    bx add /workspace/samples.csv sample_sheet
    bx run deseq2_results_table -p deseq2_fit_wald_design="~ batch + condition" -p deseq2_results_contrast="condition,treated,control"

The inputs, outputs and parameters of each step in the tool reference are the names to use here. When two steps can make an intermediate type, `bx plan` shows which one the planner chose. Name the intermediate type you want as one more TYPE to choose the other.

A file must match the layout in its type's description. Reformat it with your own code first when it does not. A parameter you do not set keeps the tool's default. A run takes about half a minute plus the time of its steps, so raise the bash timeout for a long chain. A failed step prints its log.

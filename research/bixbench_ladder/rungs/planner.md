The machine also has a workflow planner, `bx`, built on Metasmith. Every step in the tool catalogue is a typed step that the planner can run. You declare which of your files is which data type and name the type you want. The planner finds the chain of steps that produces it and runs the chain.

    bx types [WORD]     list data types: the file layout of each and the step that makes it
    bx steps [WORD]     list steps: inputs, outputs and parameters
    bx add FILE TYPE    declare that a file is a type
    bx plan TYPE ...    show the chain of steps, without running it
    bx run TYPE ... [-p PARAMETER=VALUE ...]
                        run the chain and print the path of each result file

A file must match the layout in its type's description. Reformat it with your own code first when it does not. A parameter you do not set keeps the tool's default. A run takes about half a minute plus the time of its steps, so raise the bash timeout for a long chain. A failed step prints its log.

Using the planner is your choice. Use it where its steps fit the question, and write your own code where they do not.

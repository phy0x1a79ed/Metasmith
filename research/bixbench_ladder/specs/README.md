# Tool specs

## Purpose & Contents

This directory is the one description of the tools in the experiment image. `generate.py` turns it into the Search cards and the Metasmith transforms, so both rungs carry the same text. This file is the contract a spec must meet.

**CAUTION** Write a spec from the image's software list and the tool's public documentation only. A spec author must not read BixBench questions, capsules, answers or run outputs. A spec shaped by the benchmark leaks answers into two of the three rungs.

## Layout

- `types/<domain>.yml` holds the data types. A type name is unique across all files.
- `tools/<name>.yml` holds one tool step.
- `fixtures/<name>/` holds a small synthetic input set for that step.

## A type

    count_matrix:
      description: raw integer read counts, genes in rows, samples in columns, first column the gene id
      ext: csv
      extends: table      # optional

- `description` says what the file holds and how it is laid out. An agent decides from this line whether its own file is that type.
- `ext` is the file extension. Omit it for a directory.
- `extends` names a parent type. A step that takes the parent also takes the child.

## A tool step

    name: mafft_align
    tool: MAFFT 7.526
    summary: Align unaligned sequences into a multiple sequence alignment.
    usage: |
      When to use the step, what it assumes about its inputs, and the choices that change the result.
    inputs:
      seqs: sequences_fasta
    outputs:
      aln: mafft_alignment
    params:
      strategy:
        default: "--auto"
        help: MAFFT strategy flags, for example "--auto" or "--localpair --maxiterate 1000".
    interpreter: bash
    script: |
      mafft $PARAM_strategy "$IN_seqs" > "$OUT_aln"

- `name` equals the file name and is lower_snake.
- `interpreter` is `bash`, `python` or `Rscript`.
- The script reads each input path from the environment variable `IN_<slot>`. It writes each output to the path in `OUT_<slot>`. It reads each parameter as a string from `PARAM_<name>`.
- The script runs offline, in an empty working directory, as a non-root user. It exits non-zero on failure.
- A script creates a directory output itself.

## Rules the generator enforces

1. Exactly one step produces each type. Give two steps that make similar files two types, and let both extend a shared parent when a later step takes either.
2. No step takes a type that its own output satisfies.
3. The script names every input, output and parameter it declares.

## Rules the generator cannot check

- One step is one analysis decision. Expose as a parameter every choice that changes the numbers: the test, the correction method, the model formula, the threshold, the substitution model.
- A default equals the tool's own default.
- A table output has a header and one named column per reported quantity, at full numeric precision.
- A step that needs the network does not belong here.

## Check

    ./check_specs.sh            # lint, then run every script on its fixture in the image
    ./check_specs.sh -v NAME    # one step, and print the head of each output

A fixture names each input `<slot>.<ext>`, or `<slot>` for a directory. `params.json` overrides parameter defaults for the check.

params.outdir = 'out'
params.mode = 'ok'

process produce {
    errorStrategy 'terminate'
    input: val i
    output: path "p${i}.txt"
    script:
    if( params.mode == 'kill' )
        i == 1 ? "exit 1" : "sleep 300"
    else
        "echo producer-${i}-payload > p${i}.txt"
}

process consume {
    publishDir params.outdir, mode: 'copy'
    input: path files
    output: path 'merged.txt'
    script:
    "cat ${files} > merged.txt"
}

workflow {
    consume(produce(Channel.of(1, 2, 3)).collect())
}

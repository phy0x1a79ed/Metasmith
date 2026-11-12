#!/usr/bin/env bash
# Builds and installs the plugin, then runs the toy pipelines against the stub market:
# layer 1 (a normal run and a killed one), layer 2 (two generated workflows sharing a step)
# and layer 3 (a checker that the plan's own step then reuses).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
export JAVA_HOME=${JAVA_HOME:-$(echo ~/.local/jdk/jdk-21*)}
export PATH=$JAVA_HOME/bin:$PATH
NXF=${NXF:-$HOME/lib/miniforge3/envs/msm/bin/nextflow}
MM=${MM:-$HOME/.local/bin/mamba run -n awm --no-capture-output}
(cd "$here/.." && ./gradlew -q test installPlugin)

# nf_run DIR PIPELINE LOG MARKET_ROOT [nextflow args...]: DIR must hold nothing else.
nf_run() {
    local dir=$1 pipeline=$2 log=$3 root=$4; shift 4
    cat > "$dir/nextflow.config" <<CFG
plugins { id 'nf-baitan@0.1.0' }
process.executor = 'baitan'
baitan {
    connect = '$MM python -u $here/stub_market.py $log $root'
    place = 'requester'
}
CFG
    (cd "$dir" && NXF_HOME=$HOME/.nextflow "$NXF" -q run "$pipeline" -c nextflow.config "$@" >nf.out 2>&1) || return 1
}

for mode in ok kill; do
    run=$(mktemp -d); mkdir "$run/market-root"
    nf_run "$run" "$here/main.nf" "$run/market.jsonl" "$run/market-root" --mode $mode || [ $mode = kill ] || { cat "$run/nf.out"; exit 1; }
    $MM python "$here/check.py" $mode "$run/market.jsonl" "$run"
done

run=$(mktemp -d); mkdir "$run/market-root" "$run/a" "$run/b"
PYTHONPATH=$here/../../src ${MSM_PY:-$HOME/lib/miniforge3/envs/msm/bin/python} "$here/gen_l2.py" "$run"
for w in a b; do
    nf_run "$run/$w" "$run/wf_$w.nf" "$run/market.jsonl" "$run/market-root" || { cat "$run/$w/nf.out"; exit 1; }
done
$MM python "$here/check_l2.py" "$run/market.jsonl" "$run"

run=$(mktemp -d); mkdir "$run/market-root" "$run/c"
PYTHONPATH=$here/../../src ${MSM_PY:-$HOME/lib/miniforge3/envs/msm/bin/python} "$here/gen_l3.py" "$run"
nf_run "$run/c" "$run/wf_c.nf" "$run/market.jsonl" "$run/market-root" || { cat "$run/c/nf.out"; exit 1; }
$MM python "$here/check_l3.py" "$run/market.jsonl" "$run/c"

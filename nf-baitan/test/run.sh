#!/usr/bin/env bash
# Builds and installs the plugin, then runs the toy pipeline against the stub market: a normal run, and a killed one.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
export JAVA_HOME=${JAVA_HOME:-$(echo ~/.local/jdk/jdk-21*)}
export PATH=$JAVA_HOME/bin:$PATH
NXF=${NXF:-$HOME/lib/miniforge3/envs/msm/bin/nextflow}
MM=${MM:-$HOME/.local/bin/mamba run -n awm --no-capture-output}
(cd "$here/.." && ./gradlew -q test installPlugin)

for mode in ok kill; do
    run=$(mktemp -d); log=$run/market.jsonl
    cat > "$run/nextflow.config" <<CFG
plugins { id 'nf-baitan@0.1.0' }
process.executor = 'baitan'
baitan {
    connect = '$MM python -u $here/stub_market.py $log $run/market-root'
    place = 'requester'
}
CFG
    mkdir "$run/market-root"
    (cd "$run" && NXF_HOME=$HOME/.nextflow "$NXF" -q run "$here/main.nf" --mode $mode -c nextflow.config >nf.out 2>&1) || [ $mode = kill ] || { cat "$run/nf.out"; exit 1; }
    $MM python "$here/check.py" $mode "$log" "$run"
done

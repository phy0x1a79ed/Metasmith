#!/usr/bin/env bash
# Live run through the deployed market on altair: run.sh 1|2. Submit each workflow once.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
export JAVA_HOME=${JAVA_HOME:-$(echo ~/.local/jdk/jdk-21*)}
export PATH=$JAVA_HOME/bin:$PATH
root=${REAL_DIR:-$HOME/baitan-real}
mkdir -p "$root/wf$1"
[ -f "$root/wf$1.nf" ] || PYTHONPATH=$here/../../../src $HOME/lib/miniforge3/envs/msm/bin/python "$here/gen.py" "$root" "$root/stub"
cat > "$root/wf$1/nextflow.config" <<CFG
plugins { id 'nf-baitan@0.1.0' }
process.executor = 'baitan'
baitan {
    connect = '$HOME/agentic_workspace/.awm/bin/baitan connect'
    place = 'sockeye'
    placeRoot = '/scratch/st-shallam-1/txyliu/baitan-data/results'
    runAt = [name: 'sockeye']
    dispose = false
}
CFG
cd "$root/wf$1" && NXF_HOME=$HOME/.nextflow $HOME/lib/miniforge3/envs/msm/bin/nextflow -q run "$root/wf$1.nf" -c nextflow.config

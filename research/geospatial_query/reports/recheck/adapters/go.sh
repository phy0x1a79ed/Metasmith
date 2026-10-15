#!/bin/bash
cd /home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/reports/recheck/adapters
export PYTHONPATH=/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/poc:/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/reports/recheck/adapters/ext_pyarrow AOI_PATH=/home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/examples/test_aois.geojson
PY=/home/tony/lib/miniforge3/envs/geoquery/bin/python
date +%s > start.txt
$PY /home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/poc/run_all.py > run.log 2>&1
date +%s > end_run.txt
$PY /home/tony/agentic_workspace/projects/metasmith/geospatial_query/dev/research/geospatial_query/poc/build_outputs.py > build.log 2>&1
date +%s > end.txt

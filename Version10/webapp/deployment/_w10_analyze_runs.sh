#!/bin/bash
set -euo pipefail
ENGINE=/opt/steel-beam-estimation/SteelBeamEstimator/Version10
VENV=$ENGINE/webapp/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ENGINE/src"
cd "$ENGINE"
for run in 20260826_065256_4ba41266 20260825_113725_9a8d6014 20260825_112725_777a29d8; do
  echo "===== MONITOR ${run} ====="
  "$VENV" -m PhaseW10_hybrid_production_monitoring "data/web_runs/${run}"
done
echo '===== PUBLIC ====='
curl -sS --max-time 10 http://127.0.0.1/health
echo

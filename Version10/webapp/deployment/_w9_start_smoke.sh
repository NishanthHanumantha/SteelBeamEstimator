#!/bin/bash
set -euo pipefail
ENGINE=/opt/steel-beam-estimation/SteelBeamEstimator/Version10
export PYTHONDONTWRITEBYTECODE=1
nohup "$ENGINE/webapp/.venv/bin/python" -u /tmp/smoke_w9.py > /tmp/w9_smoke.log 2>&1 &
echo SMOKE_PID=$!
echo LOG=/tmp/w9_smoke.log

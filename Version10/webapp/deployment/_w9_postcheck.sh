#!/bin/bash
set -euo pipefail
ENGINE=/opt/steel-beam-estimation/SteelBeamEstimator/Version10
VENV=$ENGINE/webapp/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo ANTHROPIC
$VENV -c 'import anthropic; print(anthropic.__version__)'
echo HEALTH_LOCAL
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo HEALTH_PUBLIC
curl -sS --max-time 10 http://127.0.0.1/health
echo
echo WORKERS
ps -o pid=,cmd= -C gunicorn | grep 8001 || true
echo ONE_BEAM
$VENV /tmp/_w9_one_beam_evidence.py

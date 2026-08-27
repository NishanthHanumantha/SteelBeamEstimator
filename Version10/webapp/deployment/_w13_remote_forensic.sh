#!/bin/bash
set -euo pipefail
echo "==== HYBRID_ENV"
sudo grep -E '^(HYBRID_MODE|HYBRID_PER_CALL_TIMEOUT_S|HYBRID_MAX_LIVE_CALLS|HYBRID_MAX_WALL_S|HYBRID_MAX_RETRIES|HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS|HYBRID_EVIDENCE_TIMEOUT_SECONDS)=' /etc/steel-beam-estimator-v10.env
echo "==== HEALTH"
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo "==== PUBLIC_JS_HEADERS"
curl -sSI --max-time 10 http://127.0.0.1/static/js/app.js | head -20
echo "==== PUBLIC_HTML_SCRIPT"
curl -sS --max-time 10 http://127.0.0.1/ | grep -E 'app.js|btn-download|badge-release' | head -20
echo "==== WORKERS"
ps -o pid=,cmd= -C gunicorn | grep 8001 || true
echo "==== FORENSIC"
/opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/.venv/bin/python /tmp/_w13_forensic_deep.py
echo "==== JOURNAL_VISION"
sudo journalctl -u steel-beam-estimator-v10.service --since "2026-08-26 08:00:00" --until "2026-08-26 15:00:00" --no-pager | grep -E "Claude vision failure|error_type=|RateLimit|429|Download" | tail -80
echo "==== LOG_VISION"
LOG=/opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/logs/webapp.log
if [ -f "$LOG" ]; then
  grep -E "Claude vision failure|error_type=" "$LOG" | tail -40
fi

#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator
ENGINE=$ROOT/Version10
TAR=/tmp/w19_runtime.tar.gz
UNPACK=/tmp/w19_unpack
BACKUP=/opt/steel-beam-estimation/backups/w19_predeploy_$(date -u +%Y%m%dT%H%M%SZ)
VENV=$ENGINE/webapp/.venv/bin/python
ENVFILE=/etc/steel-beam-estimator-v10.env

mkdir -p "$BACKUP/files"
sudo cp /etc/systemd/system/steel-beam-estimator-v10.service "$BACKUP/steel-beam-estimator-v10.service"
curl -sS --max-time 10 http://127.0.0.1:8001/health > "$BACKUP/health_before.json" || true
sudo grep -E '^(HYBRID_MODE|HYBRID_PER_CALL_TIMEOUT_S|HYBRID_MAX_LIVE_CALLS|HYBRID_MAX_WALL_S|HYBRID_MAX_RETRIES|HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS|HYBRID_EVIDENCE_TIMEOUT_SECONDS)=' "$ENVFILE" > "$BACKUP/hybrid_keys.txt" || true

rm -rf "$UNPACK"
mkdir -p "$UNPACK"
tar -xzf "$TAR" -C "$UNPACK"
while IFS= read -r src; do
  rel="${src#$UNPACK/Version10/}"
  dest="$ENGINE/$rel"
  if [ -f "$dest" ]; then
    sudo mkdir -p "$BACKUP/files/$(dirname "$rel")"
    sudo cp -a "$dest" "$BACKUP/files/$rel"
  fi
  sudo mkdir -p "$(dirname "$dest")"
  sudo cp -f "$src" "$dest"
done < <(find "$UNPACK/Version10" -type f)

export PYTHONDONTWRITEBYTECODE=1
cd "$ENGINE/src"
$VENV - <<'PY'
from PhaseW6_hybrid_production_authority.resolution_trace import (
    build_resolution_trace,
    classify_provider_error,
)
from PhaseV9_spacer_rule.spacer_engine import spacer_quantity, SPACER_DIA_MM
row = {
    "called": True,
    "visual_available": True,
    "failure_category": "API_FAILED",
    "api_error": "Error code: 400 - workspace API usage limits",
}
assert classify_provider_error(row) == "WORKSPACE_SPEND_LIMIT"
assert spacer_quantity(1040) == 2
assert spacer_quantity(1500) == 3
assert SPACER_DIA_MM == 25
trace = build_resolution_trace(
    run_id="import-check",
    beam_ids=["B1"],
    shadow_result={"beams": [{"beam_id": "B1", "called": False, "visual_available": False, "skip_reason": "NO_USABLE_EVIDENCE"}]},
)
assert trace["identity_ok"]
print("IMPORT_OK")
PY

sudo systemctl restart steel-beam-estimator-v10.service
sleep 5
echo UNIT="$(systemctl is-active steel-beam-estimator-v10.service)"
echo WORKERS
ps -o pid=,cmd= -C gunicorn | grep 8001 || true
echo HEALTH
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo ANTHROPIC
$VENV -c 'import anthropic; print(anthropic.__version__)'
echo MODELINE
sudo grep -E '^HYBRID_MODE=' "$ENVFILE"
echo KEYSTATUS
if sudo grep -q '^ANTHROPIC_API_KEY=.\+' "$ENVFILE"; then echo PRESENT; else echo ABSENT; fi
echo HTML_SCRIPT
curl -sS --max-time 10 http://127.0.0.1/ | grep -E 'app.js|btn-download' | head -10
echo BACKUP="$BACKUP"

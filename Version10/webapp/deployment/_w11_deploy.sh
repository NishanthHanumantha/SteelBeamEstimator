#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator
ENGINE=$ROOT/Version10
TAR=/tmp/w11_runtime.tar.gz
UNPACK=/tmp/w11_unpack
BACKUP=/opt/steel-beam-estimation/backups/w11_predeploy_$(date -u +%Y%m%dT%H%M%SZ)
VENV=$ENGINE/webapp/.venv/bin/python
ENVFILE=/etc/steel-beam-estimator-v10.env

mkdir -p "$BACKUP/files"
cp /etc/systemd/system/steel-beam-estimator-v10.service "$BACKUP/steel-beam-estimator-v10.service"
curl -sS --max-time 10 http://127.0.0.1:8001/health > "$BACKUP/health_before.json" || true
sudo grep -E '^(HYBRID_MODE|HYBRID_PER_CALL_TIMEOUT_S|HYBRID_MAX_LIVE_CALLS|HYBRID_MAX_WALL_S)=' "$ENVFILE" > "$BACKUP/hybrid_keys.txt" || true

rm -rf "$UNPACK"
mkdir -p "$UNPACK"
tar -xzf "$TAR" -C "$UNPACK"
while IFS= read -r src; do
  rel="${src#$UNPACK/Version10/}"
  dest="$ENGINE/$rel"
  if [ -f "$dest" ]; then
    mkdir -p "$BACKUP/files/$(dirname "$rel")"
    cp -a "$dest" "$BACKUP/files/$rel"
  fi
  mkdir -p "$(dirname "$dest")"
  cp -f "$src" "$dest"
done < <(find "$UNPACK/Version10" -type f)

# Timeout keys only. Never copy API keys. Preserve existing HYBRID_MODE.
if ! sudo grep -q '^HYBRID_MAX_RETRIES=' "$ENVFILE"; then
  echo 'HYBRID_MAX_RETRIES=1' | sudo tee -a "$ENVFILE" >/dev/null
fi
if ! sudo grep -q '^HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS=' "$ENVFILE"; then
  echo 'HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS=250' | sudo tee -a "$ENVFILE" >/dev/null
fi
if ! sudo grep -q '^HYBRID_EVIDENCE_TIMEOUT_SECONDS=' "$ENVFILE"; then
  echo 'HYBRID_EVIDENCE_TIMEOUT_SECONDS=120' | sudo tee -a "$ENVFILE" >/dev/null
fi
if ! sudo grep -q '^HYBRID_PER_CALL_TIMEOUT_S=' "$ENVFILE"; then
  echo 'HYBRID_PER_CALL_TIMEOUT_S=120' | sudo tee -a "$ENVFILE" >/dev/null
fi

export PYTHONDONTWRITEBYTECODE=1
cd "$ENGINE"
$VENV - <<'PY'
import sys
sys.path.insert(0, "src")
from PhaseW11_hybrid_reliability.bounded import run_with_timeout, TimeoutExpired
from PhaseW5_production_hybrid_shadow.settings import load_settings
print("IMPORT_OK")
print("TIMEOUT_HELPER", callable(run_with_timeout))
cfg = load_settings()
print("SETTINGS", cfg.per_call_timeout_s, cfg.max_retries, cfg.total_beam_timeout_s, cfg.evidence_timeout_s)
PY

sudo cp "$ENGINE/webapp/deployment/steel-beam-estimator-v10.service" /etc/systemd/system/steel-beam-estimator-v10.service
sudo systemctl daemon-reload
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
echo TIMEOUTS
sudo grep -E '^(HYBRID_PER_CALL_TIMEOUT_S|HYBRID_MAX_RETRIES|HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS|HYBRID_EVIDENCE_TIMEOUT_SECONDS)=' "$ENVFILE"
echo KEYSTATUS
if sudo grep -q '^ANTHROPIC_API_KEY=.\+' "$ENVFILE"; then echo PRESENT; else echo ABSENT; fi
echo BACKUP="$BACKUP"

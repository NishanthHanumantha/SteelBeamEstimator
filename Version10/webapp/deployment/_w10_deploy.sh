#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator
ENGINE=$ROOT/Version10
TAR=/tmp/w10_runtime.tar.gz
UNPACK=/tmp/w10_unpack
BACKUP=/opt/steel-beam-estimation/backups/w10_predeploy_$(date -u +%Y%m%dT%H%M%SZ)
VENV=$ENGINE/webapp/.venv/bin/python

mkdir -p "$BACKUP/files"
cp /etc/systemd/system/steel-beam-estimator-v10.service "$BACKUP/steel-beam-estimator-v10.service"
curl -sS --max-time 10 http://127.0.0.1:8001/health > "$BACKUP/health_before.json" || true
sudo grep -E '^HYBRID_MODE=' /etc/steel-beam-estimator-v10.env > "$BACKUP/hybrid_mode.txt"

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

export PYTHONDONTWRITEBYTECODE=1
cd "$ENGINE"
$VENV - <<'PY'
import sys
sys.path.insert(0, "src")
from PhaseW10_hybrid_production_monitoring.writer import write_run_monitor
from PhaseW6_hybrid_production_authority.orchestrator import run_production_hybrid
print("IMPORT_OK")
print("WRITE", callable(write_run_monitor))
print("ORCH", callable(run_production_hybrid))
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
sudo grep -E '^HYBRID_MODE=' /etc/steel-beam-estimator-v10.env
echo KEYSTATUS
if sudo grep -q '^ANTHROPIC_API_KEY=.\+' /etc/steel-beam-estimator-v10.env; then echo PRESENT; else echo ABSENT; fi
echo BACKUP="$BACKUP"

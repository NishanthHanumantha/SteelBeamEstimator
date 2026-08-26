#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator
ENGINE=$ROOT/Version10
TAR=/tmp/w12_runtime.tar.gz
UNPACK=/tmp/w12_unpack
BACKUP=/opt/steel-beam-estimation/backups/w12_predeploy_$(date -u +%Y%m%dT%H%M%SZ)
VENV=$ENGINE/webapp/.venv/bin/python
ENVFILE=/etc/steel-beam-estimator-v10.env

mkdir -p "$BACKUP/files"
cp /etc/systemd/system/steel-beam-estimator-v10.service "$BACKUP/steel-beam-estimator-v10.service"
curl -sS --max-time 10 http://127.0.0.1:8001/health > "$BACKUP/health_before.json" || true
sudo grep -E '^(HYBRID_MODE|HYBRID_PER_CALL_TIMEOUT_S|HYBRID_MAX_LIVE_CALLS|HYBRID_MAX_WALL_S|HYBRID_MAX_RETRIES|HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS|HYBRID_EVIDENCE_TIMEOUT_SECONDS)=' "$ENVFILE" > "$BACKUP/hybrid_keys.txt" || true

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
cd "$ENGINE/webapp"
$VENV - <<'PY'
from services.result_registry import is_valid_run_id, workbook_filename
from services.estimation_service import get_job
assert is_valid_run_id("20260826_120000_abcd1234")
assert workbook_filename("20260826_120000_abcd1234").endswith(".xlsx")
print("IMPORT_OK")
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
echo KEYSTATUS
if sudo grep -q '^ANTHROPIC_API_KEY=.\+' "$ENVFILE"; then echo PRESENT; else echo ABSENT; fi
echo BACKUP="$BACKUP"

#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator
ENGINE=$ROOT/Version10
TAR=/tmp/w13_runtime.tar.gz
UNPACK=/tmp/w13_unpack
BACKUP=/opt/steel-beam-estimation/backups/w13_predeploy_$(date -u +%Y%m%dT%H%M%SZ)
VENV=$ENGINE/webapp/.venv/bin/python
ENVFILE=/etc/steel-beam-estimator-v10.env
NGINX_SRC=$ENGINE/webapp/deployment/nginx-v10.conf
NGINX_DST=/etc/nginx/sites-available/steel-beam-estimator.conf

mkdir -p "$BACKUP/files"
sudo cp /etc/systemd/system/steel-beam-estimator-v10.service "$BACKUP/steel-beam-estimator-v10.service"
sudo cp "$NGINX_DST" "$BACKUP/nginx-steel-beam-estimator.conf" || true
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
from PhaseW6_hybrid_production_authority.resolution_trace import build_resolution_trace
trace = build_resolution_trace(
    run_id="import-check",
    beam_ids=["B1"],
    shadow_result={"beams": [{"beam_id": "B1", "called": False, "visual_available": False, "skip_reason": "NO_USABLE_EVIDENCE"}]},
)
assert trace["identity_ok"]
print("IMPORT_OK")
PY

sudo cp "$NGINX_SRC" "$NGINX_DST"
sudo nginx -t
sudo systemctl reload nginx

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
echo JS_CACHE
curl -sSI --max-time 10 http://127.0.0.1/static/js/app.js | head -15
echo HTML_SCRIPT
curl -sS --max-time 10 http://127.0.0.1/ | grep -E 'app.js|btn-download' | head -10
echo BACKUP="$BACKUP"

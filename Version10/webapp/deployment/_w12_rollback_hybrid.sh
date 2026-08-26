#!/bin/bash
set -euo pipefail
ENVFILE=/etc/steel-beam-estimator-v10.env
echo ROLLBACK_START
sudo grep -E '^HYBRID_MODE=' "$ENVFILE"
sudo cp -a "$ENVFILE" /opt/steel-beam-estimation/backups/w12_env_pre_rollback_$(date -u +%Y%m%dT%H%M%SZ)
sudo sed -i 's/^HYBRID_MODE=production$/HYBRID_MODE=off/' "$ENVFILE"
sudo grep -E '^HYBRID_MODE=' "$ENVFILE"
sudo systemctl restart steel-beam-estimator-v10.service
sleep 5
echo HEALTH_OFF
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
sudo sed -i 's/^HYBRID_MODE=off$/HYBRID_MODE=production/' "$ENVFILE"
sudo grep -E '^HYBRID_MODE=' "$ENVFILE"
sudo systemctl restart steel-beam-estimator-v10.service
sleep 5
echo HEALTH_ON
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo UNIT="$(systemctl is-active steel-beam-estimator-v10.service)"
echo ROLLBACK_DONE

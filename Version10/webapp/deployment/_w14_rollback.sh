#!/bin/bash
set -euo pipefail
ENVFILE=/etc/steel-beam-estimator-v10.env
echo "==== ENV_ROLLBACK"
sudo python3 - <<'PY'
from pathlib import Path
p = Path("/etc/steel-beam-estimator-v10.env")
text = p.read_text(encoding="utf-8")
new = []
for line in text.splitlines(True):
    if line.startswith("HYBRID_MODE="):
        new.append("HYBRID_MODE=off\n")
    else:
        new.append(line)
Path("/tmp/w14_env_off").write_text("".join(new), encoding="utf-8")
PY
sudo cp /tmp/w14_env_off "$ENVFILE"
sudo chmod 600 "$ENVFILE"
sudo systemctl restart steel-beam-estimator-v10.service
sleep 4
echo ROLLBACK_HEALTH
curl -sS --max-time 10 http://127.0.0.1:8001/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("phase"), d.get("hybrid",{}).get("mode"), d.get("hybrid",{}).get("enabled"))'
sudo python3 - <<'PY'
from pathlib import Path
p = Path("/etc/steel-beam-estimator-v10.env")
text = p.read_text(encoding="utf-8")
new = []
for line in text.splitlines(True):
    if line.startswith("HYBRID_MODE="):
        new.append("HYBRID_MODE=production\n")
    else:
        new.append(line)
Path("/tmp/w14_env_prod").write_text("".join(new), encoding="utf-8")
PY
sudo cp /tmp/w14_env_prod "$ENVFILE"
sudo chmod 600 "$ENVFILE"
sudo systemctl restart steel-beam-estimator-v10.service
sleep 4
echo RESTORED_HEALTH
curl -sS --max-time 10 http://127.0.0.1:8001/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("phase"), d.get("hybrid",{}).get("mode"), d.get("hybrid",{}).get("enabled"))'
echo KEYSTATUS
if sudo grep -q '^ANTHROPIC_API_KEY=.\+' "$ENVFILE"; then echo PRESENT; else echo ABSENT; fi
echo MODELINE
sudo grep -E '^HYBRID_MODE=' "$ENVFILE"

#!/bin/bash
set -euo pipefail
ENV=/etc/steel-beam-estimator-v10.env

rollback_off() {
  sudo python3 - <<'PY'
from pathlib import Path
p = Path("/etc/steel-beam-estimator-v10.env")
text = p.read_text(encoding="utf-8")
lines = []
found = False
for line in text.splitlines():
    if line.startswith("HYBRID_MODE="):
        lines.append("HYBRID_MODE=off")
        found = True
    else:
        lines.append(line)
if not found:
    lines.append("HYBRID_MODE=off")
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  sudo systemctl restart steel-beam-estimator-v10.service
  sleep 4
  echo MODELINE
  sudo grep -E '^HYBRID_MODE=' "$ENV"
  echo HEALTH
  curl -sS --max-time 10 http://127.0.0.1:8001/health
  echo
}

restore_production() {
  sudo python3 - <<'PY'
from pathlib import Path
p = Path("/etc/steel-beam-estimator-v10.env")
text = p.read_text(encoding="utf-8")
lines = []
found = False
for line in text.splitlines():
    if line.startswith("HYBRID_MODE="):
        lines.append("HYBRID_MODE=production")
        found = True
    else:
        lines.append(line)
if not found:
    lines.append("HYBRID_MODE=production")
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  sudo systemctl restart steel-beam-estimator-v10.service
  sleep 4
  echo MODELINE
  sudo grep -E '^HYBRID_MODE=' "$ENV"
  echo HEALTH
  curl -sS --max-time 10 http://127.0.0.1:8001/health
  echo
  echo WORKERS
  ps -o pid=,cmd= -C gunicorn | grep 8001 || true
  echo ANTHROPIC
  /opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/.venv/bin/python -c 'import anthropic; print(anthropic.__version__)'
  echo KEYSTATUS
  if sudo grep -q '^ANTHROPIC_API_KEY=.\+' "$ENV"; then echo PRESENT; else echo ABSENT; fi
}

echo '==== ROLLBACK OFF ===='
rollback_off
echo '==== RESTORE PRODUCTION ===='
restore_production

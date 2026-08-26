#!/bin/bash
set -u
ENGINE=/opt/steel-beam-estimation/SteelBeamEstimator/Version10
RUNS=$ENGINE/data/web_runs
echo "==== HEALTH ===="
curl -sS http://127.0.0.1:8001/health || true
echo
echo "==== GUNICORN / PYTHON ===="
ps -eo pid,ppid,etime,pcpu,pmem,cmd | grep -E 'gunicorn|wsgi:app|estimate-|run_phase_w6|claude|python' | grep -v grep || true
echo
echo "==== LISTEN 8001 ===="
ss -lntp 2>/dev/null | grep 8001 || netstat -lntp 2>/dev/null | grep 8001 || true
echo
echo "==== RECENT WEB RUNS ===="
ls -lt "$RUNS" 2>/dev/null | head -25
echo
echo "==== NEWEST RUN DIRS ===="
python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
base = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs")
rows = []
for p in sorted(base.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
    if not p.is_dir() or p.name.startswith("."):
        continue
    rows.append(p)
    if len(rows) >= 12:
        break
print("run_id mtime size_mb has_excel has_w6 has_w5 has_w10 stages_hint")
for p in rows:
    excel = p / "data/output/Production_Output/Estimation_Output.xlsx"
    w6 = p / "data/output/PhaseW6_hybrid_semantic_resolution"
    w5 = p / "data/output/PhaseW5_production_hybrid_shadow"
    w10 = p / "data/output/PhaseW10_hybrid_monitoring"
    out = p / "data/output"
    stages = []
    if out.is_dir():
        stages = sorted([d.name for d in out.iterdir() if d.is_dir()])[:8]
    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0
    print(p.name, mtime, round(size/1e6, 2), excel.is_file(), w6.is_dir(), (w5/"hybrid_shadow_report.json").is_file(), (w10/"hybrid_production_monitor.json").is_file(), ",".join(stages[:6]))
PY
echo
echo "==== JOURNAL TAIL ===="
sudo journalctl -u steel-beam-estimator-v10 --no-pager -n 120 || true
echo
echo "==== WEBAPP LOG TAIL ===="
tail -n 80 "$ENGINE/webapp/logs/webapp.log" 2>/dev/null || echo NO_WEBAPP_LOG
echo
echo "==== ENV TIMEOUT KEYS (names/values non-secret) ===="
sudo python3 - <<'PY'
from pathlib import Path
p = Path("/etc/steel-beam-estimator-v10.env")
text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
keys = [
    "HYBRID_MODE","HYBRID_MAX_LIVE_CALLS","HYBRID_MAX_WALL_S","HYBRID_PER_CALL_TIMEOUT_S",
    "HYBRID_CLAUDE_MODEL","HYBRID_VISION_TIMEOUT_SECONDS","HYBRID_MAX_RETRIES",
    "HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS"
]
for line in text.splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    k = k.strip()
    if k in keys:
        print(f"{k}={v.strip() or '<empty>'}")
    elif "KEY" in k.upper() or "SECRET" in k.upper() or "TOKEN" in k.upper():
        print(f"{k}=REDACTED_PRESENT" if v.strip() else f"{k}=EMPTY")
PY
echo
echo "==== OPEN FILES ON PYTHON/GUNICORN (truncated) ===="
for pid in $(pgrep -f 'gunicorn.*8001' || true); do
  echo "PID $pid"
  ls -l /proc/$pid/cwd 2>/dev/null || true
  tr '\0' '\n' < /proc/$pid/cmdline 2>/dev/null; echo
  timeout 5 ls -l /proc/$pid/fd 2>/dev/null | head -40 || true
  echo "--- stack ---"
  sudo timeout 5 cat /proc/$pid/stack 2>/dev/null | head -20 || true
done
echo "==== CHILD THREADS ===="
ps -T -p $(pgrep -d, -f 'gunicorn.*wsgi:app' || echo 1) 2>/dev/null | head -40 || true
echo DONE

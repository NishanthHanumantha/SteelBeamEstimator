#!/bin/bash
set -euo pipefail
ENGINE=/opt/steel-beam-estimation/SteelBeamEstimator/Version10
echo "==== ADAPTER_INVOKE"
grep -n -E 'max_api_attempts|max_attempts|vision_attempts' "$ENGINE/src/PhaseW5_production_hybrid_shadow/adapter.py" | head -40
echo "==== CLAUDE_CLIENT_RETRIES"
grep -n -E 'max_retries' "$ENGINE/src/llm/claude_client.py" | head -20
echo "==== JOURNAL_TO_FILE"
sudo journalctl -u steel-beam-estimator-v10.service --since "2026-08-26 11:00:00" --until "2026-08-26 14:40:00" --no-pager > /tmp/w13_journal.txt || true
python3 - <<'PY'
from collections import Counter
from pathlib import Path
p = Path("/tmp/w13_journal.txt")
text = p.read_text(encoding="utf-8", errors="replace")
print("JOURNAL_BYTES", p.stat().st_size)
print("JOURNAL_LINES", text.count("\n"))
keys = ("Claude vision failure", "error_type=", "RateLimit", "429", "Overloaded", "Authentication")
for k in keys:
    print("COUNT", k, text.count(k))
types = Counter()
for ln in text.splitlines():
    if "error_type=" in ln:
        part = ln.split("error_type=", 1)[1].split()[0]
        types[part] += 1
print("ERROR_TYPES", dict(types))
hits = [ln for ln in text.splitlines() if "Claude vision failure" in ln or ("error_type=" in ln and "vision" in ln.lower())]
print("SAMPLE")
for ln in hits[:8]:
    print(ln[:350])
print("--- TAIL ---")
for ln in hits[-8:]:
    print(ln[:350])
PY
echo "==== W12_DURATIONS"
"$ENGINE/webapp/.venv/bin/python" - <<'PY'
import json
from pathlib import Path
from collections import Counter
root = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_111142_32321cb4")
shadow = json.loads((root/"data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json").read_text())
beams = shadow["beams"]
ok = [b for b in beams if b.get("hybrid_status")=="OBSERVED"]
fail = [b for b in beams if b.get("hybrid_status")!="OBSERVED"]
print("OK_N", len(ok), "FAIL_N", len(fail))
print("OK_DUR_MINMAX", min(b.get("claude_duration_s") or 0 for b in ok), max(b.get("claude_duration_s") or 0 for b in ok))
print("FAIL_DUR_MINMAX", min(b.get("claude_duration_s") or 0 for b in fail), max(b.get("claude_duration_s") or 0 for b in fail))
print("FAIL_RETRY", Counter(b.get("retry_count") for b in fail))
print("FAIL_ATTEMPTS", Counter(b.get("attempts") for b in fail))
print("OK_LAST", ok[-1].get("beam_id"), ok[-1].get("claude_ended_at"), ok[-1].get("claude_duration_s"))
print("FAIL_FIRST", fail[0].get("beam_id"), fail[0].get("claude_started_at"), fail[0].get("claude_duration_s"))
# evidence files exist?
from pathlib import Path as P
ev = P("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_111142_32321cb4/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence")
ctx = list(ev.glob("*/context/selected.png"))
det = list(ev.glob("*/detail/selected.png"))
print("EVIDENCE_CONTEXT", len(ctx), "DETAIL", len(det))
print("CTX_BYTES_SAMPLE", ctx[0].stat().st_size if ctx else None, det[0].stat().st_size if det else None)
# monitor overwrites
monp = root/"data/output/PhaseW10_hybrid_monitoring/hybrid_production_monitor.json"
if monp.is_file():
    mon = json.loads(monp.read_text())
    print("MONITOR", json.dumps(mon.get("engineering_protection") or mon.get("overwrites") or {k:mon.get(k) for k in list(mon)[:12]}, default=str)[:1500])
# coverage
covp = root/"data/output/PhaseW6_hybrid_semantic_resolution/hybrid_coverage.json"
if covp.is_file():
    cov = json.loads(covp.read_text())
    print("COVERAGE", {k:cov.get(k) for k in ["hybrid_eligible","evidence_packages_generated","claude_attempted","claude_success","claude_failure","hybrid_resolved","unresolved","deterministic_fallback"]})
# handoff
hp = root/"data/output/PhaseW6_hybrid_semantic_resolution/hybrid_handoff.json"
if not hp.is_file():
    hp = root/"data/output/PhaseW6_hybrid_semantic_resolution/hybrid_handoff_ledger.json"
if hp.is_file():
    h = json.loads(hp.read_text())
    print("HANDOFF", {k:h.get(k) for k in ["applied","reason","beams_patched","fields_patched"]})
PY
echo "==== USER_RUN_EVIDENCE"
"$ENGINE/webapp/.venv/bin/python" - <<'PY'
import json
from pathlib import Path
root = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_141507_88aff694")
shadow = json.loads((root/"data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json").read_text())
beams = shadow["beams"]
print("BEAMS", len(beams), "CALLED", sum(1 for b in beams if b.get("called")), "OBS", sum(1 for b in beams if b.get("hybrid_status")=="OBSERVED"))
print("SKIP", {})
from collections import Counter
print("SKIP", dict(Counter(b.get("skip_reason") for b in beams)))
monp = root/"data/output/PhaseW10_hybrid_monitoring/hybrid_production_monitor.json"
if monp.is_file():
    mon = json.loads(monp.read_text())
    prot = mon.get("engineering_protection") or {}
    print("PROTECT", prot)
PY
echo "==== NGINX_CONF_PATH"
ls -l /etc/nginx/sites-enabled/
echo DONE

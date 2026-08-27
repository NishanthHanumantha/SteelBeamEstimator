#!/usr/bin/env python3
import json
from pathlib import Path
from collections import Counter

rid = "20260827_055526_cad8ac77"
root = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs") / rid
shadow = json.loads((root / "data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json").read_text())
trace_path = root / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_resolution_trace.json"
trace = json.loads(trace_path.read_text()) if trace_path.is_file() else {}
monp = root / "data/output/PhaseW10_hybrid_monitoring/hybrid_production_monitor.json"
mon = json.loads(monp.read_text()) if monp.is_file() else {}
beams = shadow.get("beams") or []
print("TRACE_COUNTS", json.dumps(trace.get("lifecycle_counts"), indent=2))
print("REASON", json.dumps(trace.get("reason_counts"), indent=2))
print("STATUS", json.dumps(trace.get("status_counts"), indent=2))
print("PROTECT", json.dumps(mon.get("engineering_protection"), indent=2))
et = Counter()
err = Counter()
attempts = Counter()
retries = Counter()
for b in beams:
    et[str(b.get("error_type"))] += 1
    raw = str(b.get("api_error") or "")[:180]
    err[raw] += 1
    attempts[b.get("attempts")] += 1
    retries[b.get("retry_count")] += 1
print("ERROR_TYPES", dict(et))
print("ATTEMPTS", dict(attempts))
print("RETRIES", dict(retries))
print("API_ERROR_SAMPLES")
for k, v in err.most_common(8):
    print(v, k.replace("sk-ant-", "[REDACTED]"))
print("SAMPLE_ROW_KEYS", sorted((beams[0] or {}).keys()) if beams else [])
print("SAMPLE_FAIL", {k: (beams[0] or {}).get(k) for k in (
    "beam_id","called","hybrid_status","skip_reason","failure_category","error_type",
    "api_success","api_error","retry_count","attempts","claude_duration_s","parse_status","schema_valid","semantic_usable"
)})

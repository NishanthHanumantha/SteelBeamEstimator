#!/bin/bash
set -euo pipefail
ENGINE=/opt/steel-beam-estimation/SteelBeamEstimator/Version10
VENV=$ENGINE/webapp/.venv/bin/python
cd "$ENGINE/src"
$VENV - <<'PY'
from pathlib import Path
import json
from PhaseW6_hybrid_production_authority.resolution_trace import reconstruct_from_staging

RUNS = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs")
IDS = [
    "20260826_084708_f74912b8",
    "20260826_111142_32321cb4",
    "20260826_141507_88aff694",
    "20260827_055526_cad8ac77",
]
for rid in IDS:
    staging = RUNS / rid
    trace = reconstruct_from_staging(staging, run_id=rid)
    out = staging / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_resolution_trace.json"
    slim = dict(trace)
    slim["beams"] = [
        {k: b.get(k) for k in (
            "beam_id", "final_status", "reason_code", "existing_code",
            "claude_attempted", "claude_api_success", "e2_accepted",
            "d2_resolved", "r13_patch_applied", "error_type", "api_error",
            "retry_count", "attempts", "failure_category", "skip_reason",
        )}
        for b in trace.get("beams") or []
    ]
    out.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    print("====", rid)
    print(json.dumps({
        "lifecycle_counts": trace.get("lifecycle_counts"),
        "reason_counts": trace.get("reason_counts"),
        "status_counts": trace.get("status_counts"),
        "identity_ok": trace.get("identity_ok"),
        "unexplained": trace.get("unexplained"),
        "handoff": trace.get("handoff"),
    }, indent=2))
PY
echo "==== SMALL_RUNS"
$VENV - <<'PY'
from pathlib import Path
import json
runs = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs")
rows = []
for p in runs.iterdir():
    if not p.is_dir():
        continue
    shadow = p / "data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json"
    n = None
    if shadow.is_file():
        try:
            data = json.loads(shadow.read_text())
            n = len(data.get("beams") or [])
        except Exception:
            n = None
    rows.append((n or 9999, p.name, n))
for n, name, raw in sorted(rows)[:12]:
    print(raw, name)
PY

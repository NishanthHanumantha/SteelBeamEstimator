#!/bin/bash
set -euo pipefail
BASE=/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs
for run in 20260826_065256_4ba41266 20260825_113725_9a8d6014 20260825_112725_777a29d8; do
  echo "===== $run ====="
  W6=$BASE/$run/data/output/PhaseW6_hybrid_semantic_resolution
  W5=$BASE/$run/data/output/PhaseW5_production_hybrid_shadow
  echo W6
  ls "$W6" 2>/dev/null || echo MISSING_W6
  echo W5
  ls "$W5" 2>/dev/null || echo MISSING_W5
  echo STEEL
  ls "$BASE/$run/data/output/Production_Output/steel_weight_summary.json" 2>/dev/null || echo MISSING_STEEL
done
echo '===== B15 MANIFEST ====='
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_065256_4ba41266/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence/B15/evidence_manifest.json")
d = json.loads(p.read_text(encoding="utf-8"))
keys = ["beam_id","evidence_class","visual_source","fallback_status","fallback_reason","completeness_status","attempted_evidence_sources","claude_image_contract"]
print({k: d.get(k) for k in keys})
print("ctx", (d.get("selected_context_evidence") or {}).get("source_phase"))
print("det", (d.get("selected_detail_evidence") or {}).get("source_phase"))
print("c3", d.get("completeness_status") or d.get("c3_status"))
PY
echo '===== SHADOW AGREEMENT ====='
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_065256_4ba41266/data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json")
if not p.is_file():
    print("NO_SHADOW_REPORT")
else:
    d = json.loads(p.read_text(encoding="utf-8"))
    print("agreement", d.get("agreement_counts"))
    print("tokens", d.get("input_tokens"), d.get("output_tokens"), d.get("estimated_cost_usd"), d.get("cost_basis"))
    print("latency", d.get("hybrid_latency_s"))
    beams = d.get("beams") or []
    print("beam_count", len(beams))
    print("first_keys", sorted((beams[0] or {}).keys())[:40] if beams else [])
PY

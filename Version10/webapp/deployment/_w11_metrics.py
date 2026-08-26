from pathlib import Path
import json
p = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8/data/output/PhaseW10_hybrid_monitoring/hybrid_production_monitor.json")
d = json.loads(p.read_text(encoding="utf-8"))
keys = [
    "run_id","hybrid_eligible","primary_evidence_count","compatibility_fallback_count",
    "unavailable_count","unexplained_count","claude_attempted","claude_successful",
    "timeout_count","vision_duration_s","average_vision_duration_s","hybrid_duration_s",
    "evidence_generation_duration_s","pipeline_duration_s","identity_ok"
]
print({k: d.get(k) for k in keys})
print("semantic", d.get("semantic_counts"))
print("api", d.get("api_usage"))
print("steel", d.get("steel_kg") or d.get("total_steel_kg") or d.get("engineering"))
w6 = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_observability.json")
o = json.loads(w6.read_text(encoding="utf-8"))
print("w6_class", o.get("classification"), "latency", o.get("hybrid_latency_s"), "claude", o.get("claude_invocation_count"), o.get("successful_invocation_count"))
print("visual_prep", o.get("visual_prep"))
print("coverage_eligible", (o.get("coverage") or {}).get("hybrid_eligible"), (o.get("coverage") or {}).get("claude_success"))
steel = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8/data/output/Production_Output/steel_weight_summary.json")
print("steel_file", json.loads(steel.read_text()) if steel.is_file() else None)

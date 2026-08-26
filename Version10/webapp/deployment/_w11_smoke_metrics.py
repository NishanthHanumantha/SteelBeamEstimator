from pathlib import Path
import json
run = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_102310_1a616a17")
w6 = run / "data/output/PhaseW6_hybrid_semantic_resolution"
for name in ("hybrid_progress.json", "hybrid_lifecycle.json", "hybrid_observability.json"):
    p = w6 / name
    print("FILE", name, p.is_file())
    if p.is_file() and name != "hybrid_observability.json":
        print(p.read_text(encoding="utf-8")[:2000])
obs = json.loads((w6 / "hybrid_observability.json").read_text(encoding="utf-8"))
print("class", obs.get("classification"), "latency", obs.get("hybrid_latency_s"), "timeout", obs.get("timeout_count"))
print("visual", (obs.get("visual_prep") or {}).get("evidence_generation_duration_s"))
mon = run / "data/output/PhaseW10_hybrid_monitoring/hybrid_production_monitor.json"
if mon.is_file():
    d = json.loads(mon.read_text(encoding="utf-8"))
    print("w10", {k: d.get(k) for k in ("vision_duration_s","average_vision_duration_s","hybrid_duration_s","timeout_count","claude_successful","engineering")})
    print("overwrites", d.get("engineering_overwrites") or d.get("deterministic_engineering_overwrite_count"))

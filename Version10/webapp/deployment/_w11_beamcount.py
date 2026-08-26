from pathlib import Path
p = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8/data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json")
import json
d = json.loads(p.read_text(encoding="utf-8"))
print("model_count", d.get("model_count"))
print("models", len(d.get("models") or {}))
ids = sorted((d.get("models") or {}).keys())
print("first", ids[:8], "last", ids[-8:])
ev = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence")
n = len([x for x in ev.iterdir() if x.is_dir()]) if ev.is_dir() else 0
print("evidence_dirs", n)
print("pid168565", Path("/proc/168565").exists())
print("w5", (Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8/data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json")).is_file())
print("excel", (Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8/data/output/Production_Output/Estimation_Output.xlsx")).is_file())

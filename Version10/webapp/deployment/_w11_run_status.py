from pathlib import Path
import json
run = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8")
out = run / "data/output"
print("pid168565", Path("/proc/168565").exists())
print("excel", (out / "Production_Output/Estimation_Output.xlsx").is_file())
print("w5", (out / "PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json").is_file())
print("w10", (out / "PhaseW10_hybrid_monitoring/hybrid_production_monitor.json").is_file())
ev = out / "PhaseW6_hybrid_semantic_resolution/hybrid_evidence"
print("evidence_dirs", len([x for x in ev.iterdir() if x.is_dir()]) if ev.is_dir() else 0)
w6 = out / "PhaseW6_hybrid_semantic_resolution"
print("w6_files", sorted(p.name for p in w6.iterdir() if p.is_file()) if w6.is_dir() else [])

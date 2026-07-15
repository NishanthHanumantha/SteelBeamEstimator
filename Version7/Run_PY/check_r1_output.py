import json, pathlib, sys

out_dir = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version7\data\output\PhaseR.1_generalized_reinforcement_discovery")

print("=== Files written ===")
for f in sorted(out_dir.iterdir()):
    size = f.stat().st_size
    print(f"  {f.name}: {size:,} bytes")

print()
val = json.loads((out_dir / "reinforcement_validation_report.json").read_text("utf-8"))
print("=== Validation Report ===")
print(f"Overall: {val['overall']}  Passed: {val['passed']}  Failed: {val['failed']}  Warned: {val['warned']}")
for r in val["rules"]:
    print(f"  {r['rule_id']}: [{r['status']}] {r['name']} - {r['message']}")

print()
stats = json.loads((out_dir / "reinforcement_statistics.json").read_text("utf-8"))
print("=== Statistics ===")
for k, v in stats.items():
    if k != "role_distribution":
        print(f"  {k}: {v}")
print("  role_distribution:")
for role, qty in stats.get("role_distribution", {}).items():
    print(f"    {role}: {qty}")

print()
models_data = json.loads((out_dir / "beam_reinforcement_models.json").read_text("utf-8"))
models = models_data.get("models", {})
print(f"=== Beam Reinforcement Models: {len(models)} total ===")
complete = sum(1 for m in models.values() if m.get("classification_complete"))
print(f"  Complete: {complete}, Partial: {len(models)-complete}")
print()
print("Sample (first 5 beams):")
for bid, m in list(models.items())[:5]:
    groups = list(m.get("groups", {}).keys())
    cov = m.get("coverage_pct", 0)
    print(f"  {bid}: groups={groups} coverage={cov}%")

"""
run_phase_r14_integrity_validation.py
Runner for Phase R.1.4 — Reinforcement Integrity & Coverage Validation
MODEL_VERSION: 7.8.0

Usage (from project root):
    python Version8/Run_PY/run_phase_r14_integrity_validation.py
"""
import importlib.util
import pathlib
import sys
import types

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
VERSION7_SRC = PROJECT_ROOT / "Version8" / "src"
VERSION7_ROOT = PROJECT_ROOT / "Version8"

if str(VERSION7_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION7_SRC))

_PKG_DIR = VERSION7_SRC / "PhaseR1.4_integrity_validation"
pkg_name = "PhaseR14"

pkg_mod = types.ModuleType(pkg_name)
pkg_mod.__path__ = [str(_PKG_DIR)]
pkg_mod.__package__ = pkg_name
sys.modules[pkg_name] = pkg_mod


def _load_sub(name: str):
    s = importlib.util.spec_from_file_location(
        f"{pkg_name}.{name}", _PKG_DIR / f"{name}.py"
    )
    m = importlib.util.module_from_spec(s)
    m.__package__ = pkg_name
    sys.modules[f"{pkg_name}.{name}"] = m
    s.loader.exec_module(m)
    return m


for _sub in [
    "__init__",
    "validation_models",
    "pipeline_data_loader",
    "coverage_analyzer",
    "beam_consistency_checker",
    "engineering_bar_validator",
    "pipeline_dependency_validator",
    "coverage_classifier",
    "integrity_quality_gate",
    "validation_statistics",
    "reinforcement_integrity_validator",
    "validation_reporter",
    "validation_export",
    "phase_r14_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR1.4_integrity_validation"
orch_mod = sys.modules[f"{pkg_name}.phase_r14_orchestrator"]
Orchestrator = orch_mod.PhaseR14Orchestrator

orchestrator = Orchestrator(
    v7_root=VERSION7_ROOT,
    output_dir=OUTPUT_DIR,
    reinforcement_source="EngineeringBarModel_R1.3",
    production_models_path=str(
        VERSION7_ROOT
        / "data/output/PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json"
    ),
)
result = orchestrator.run()

print(f"\n  PHASE R.1.4 RESULT")
print(f"  Status           : {result.get('status')}")
vr = result.get("validation_result")
if vr:
    print(f"  Integrity Score  : {vr.integrity_score}")
    print(f"  Pipeline Health  : {vr.pipeline_health_score}")
    print(f"  Quality Gate     : {vr.quality_gate_status}")
    passed = sum(1 for r in vr.rules.values() if r.status == "PASS")
    print(f"  Rules PASS       : {passed}/{len(vr.rules)}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

"""
run_phase_r13_pipeline_integration.py
Runner for Phase R.1.3 — Generalized Reinforcement Pipeline Integration
MODEL_VERSION: 7.7.0

Usage (from project root):
    python Version8/Run_PY/run_phase_r13_pipeline_integration.py
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

_PKG_DIR = VERSION7_SRC / "PhaseR1.3_pipeline_integration"
pkg_name = "PhaseR13"

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
    "engineering_bar_model",
    "engineering_bar_builder",
    "reinforcement_pipeline_adapter",
    "reinforcement_source_selector",
    "l2_engineering_processor",
    "pipeline_integration_manager",
    "production_pipeline_rewire",
    "pipeline_validator",
    "integration_statistics",
    "integration_reporter",
    "integration_export",
    "phase_r13_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR1.3_pipeline_integration"
orch_mod = sys.modules[f"{pkg_name}.phase_r13_orchestrator"]
Orchestrator = orch_mod.PhaseR13Orchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

print(f"\n  PHASE R.1.3 RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation_score')}")
print(f"  Beams (steel)    : {result.get('comparison', {}).get('after', {}).get('beams_reaching_steel')}")
print(f"  Steel (kg)       : {result.get('production_result', {}).get('total_steel_kg', 0):.1f}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

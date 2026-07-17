"""
run_phase_r2b_engineering_context_consumption.py
Runner for Phase R.2B — Engineering Context Consumption Engine
MODEL_VERSION: 7.6.0

Usage (from project root):
    python Version8/Run_PY/run_phase_r2b_engineering_context_consumption.py
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

_PKG_DIR = VERSION7_SRC / "PhaseR.2B_engineering_context_consumption"
pkg_name = "PhaseR2B"

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
    "engineering_context_consumption_models",
    "development_length_consumer",
    "engineering_context_dependency_mapper",
    "engineering_context_usage_validator",
    "engineering_context_statistics",
    "engineering_context_export",
    "engineering_context_reporter",
    "phase_r2b_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR.2B_engineering_context_consumption"
orch_mod = sys.modules[f"{pkg_name}.phase_r2b_orchestrator"]
Orchestrator = orch_mod.PhaseR2BOrchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

print(f"\n  PHASE R.2B RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation_score')}")
print(f"  Consumption      : {result.get('consumption_pct')}%")
print(f"  Steel weight     : {result.get('steel_weight_kg')}")
print(f"  Workbook         : {result.get('workbook_path')}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

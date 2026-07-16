"""
run_phase_r15_engineering_consumption_validation.py
Runner for Phase R.1.5 — Engineering Calculation Consumption Validation
MODEL_VERSION: 7.8.1 — READ-ONLY

Usage (from project root):
    python Version7/Run_PY/run_phase_r15_engineering_consumption_validation.py
"""
import importlib.util
import pathlib
import sys
import types

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
VERSION7_SRC = PROJECT_ROOT / "Version7" / "src"
VERSION7_ROOT = PROJECT_ROOT / "Version7"

if str(VERSION7_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION7_SRC))

_PKG_DIR = VERSION7_SRC / "PhaseR1.5_engineering_consumption_validation"
pkg_name = "PhaseR15"

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
    "engineering_consumption_models",
    "engineering_bar_loader",
    "steel_weight_trace",
    "bbs_trace",
    "diameter_summary_trace",
    "beam_total_trace",
    "project_total_trace",
    "excel_trace",
    "quantity_comparator",
    "engineering_consumption_validator",
    "consumption_statistics",
    "consumption_reporter",
    "consumption_export",
    "phase_r15_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR = (
    VERSION7_ROOT / "data" / "output" / "PhaseR1.5_engineering_consumption_validation"
)
orch_mod = sys.modules[f"{pkg_name}.phase_r15_orchestrator"]
Orchestrator = orch_mod.PhaseR15Orchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

print(f"\n  PHASE R.1.5 RESULT")
print(f"  Status           : {result.get('status')}")
vr = result.get("validation")
if vr:
    passed = sum(1 for r in vr.rules.values() if r["passed"])
    print(f"  Validation       : {passed}/{len(vr.rules)}")
    print(f"  Consumption %    : {vr.consumption_score}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

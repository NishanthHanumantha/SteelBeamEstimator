"""
run_phase_r12_reinforcement_propagation_audit.py
Runner for Phase R.1.2 — Reinforcement Propagation Audit
MODEL_VERSION: 7.3.2

Usage (from project root):
    python Version7/Run_PY/run_phase_r12_reinforcement_propagation_audit.py
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

_PKG_DIR = VERSION7_SRC / "PhaseR.1.2_reinforcement_propagation_audit"
pkg_name = "PhaseR12"

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
    "propagation_models",
    "reinforcement_model_reader",
    "adapter_trace",
    "engineering_bar_trace",
    "steel_weight_trace",
    "bbs_trace",
    "beam_summary_trace",
    "propagation_comparator",
    "missing_bar_detector",
    "root_cause_locator",
    "propagation_statistics",
    "propagation_validator",
    "propagation_reporter",
    "propagation_export",
    "phase_r12_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR.1.2_reinforcement_propagation_audit"
orch_mod = sys.modules[f"{pkg_name}.phase_r12_orchestrator"]
Orchestrator = orch_mod.PhaseR12Orchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

print(f"\n  PHASE R.1.2 RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation_score')}")
print(f"  Beams audited    : {result.get('beam_count')}")
print(f"  Beams with steel : {result.get('beams_with_steel')}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

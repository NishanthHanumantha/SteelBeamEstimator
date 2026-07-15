"""
run_phase_r1_1_production_validation.py
Runner for Phase R.1.1 — Production Estimation Regeneration & Benchmark Validation.

Usage:
    python Version7/Run_PY/run_phase_r1_1_production_validation.py

Must be run from the SteelBeamEstimator project root.
"""

import importlib.util
import pathlib
import sys
import types

SCRIPT_DIR    = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent           # SteelBeamEstimator/
VERSION7_SRC  = PROJECT_ROOT / "Version7" / "src"
VERSION7_ROOT = PROJECT_ROOT / "Version7"

if str(VERSION7_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION7_SRC))

_PKG_DIR = VERSION7_SRC / "PhaseR.1.1_production_validation"

pkg_name = "PhaseR11"
pkg_mod  = types.ModuleType(pkg_name)
pkg_mod.__path__    = [str(_PKG_DIR)]
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
    "reinforcement_source_adapter",
    "production_pipeline_runner",
    "production_comparator",
    "accuracy_statistics",
    "improvement_analyzer",
    "validation_reporter",
    "phase_r1_1_orchestrator",
]:
    _load_sub(_sub)

orch_mod      = sys.modules[f"{pkg_name}.phase_r1_1_orchestrator"]
run_phase_r1_1 = orch_mod.run_phase_r1_1

result = run_phase_r1_1(VERSION7_ROOT)

if result.get("status") in ("PASS", "SUCCESS"):
    sys.exit(0)
else:
    sys.exit(1)

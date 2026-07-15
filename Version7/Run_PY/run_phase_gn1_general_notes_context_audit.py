"""
run_phase_gn1_general_notes_context_audit.py
Runner for Phase GN.1 — General Notes Engineering Context Audit & Consumption Validation
MODEL_VERSION: 7.4.0

Usage:
    python Version7/Run_PY/run_phase_gn1_general_notes_context_audit.py

Must be run from the SteelBeamEstimator project root.
READ-ONLY AUDIT: no production code or engineering calculations are changed.
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

_PKG_DIR = VERSION7_SRC / "PhaseGN.1_general_notes_context_audit"

pkg_name = "PhaseGN1"
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
    "gn_models",
    "gn_discovery",
    "gn_extractor",
    "gn_context_builder",
    "framing_plan_auditor",
    "reinforcement_drawing_auditor",
    "hardcoded_default_detector",
    "engineering_gap_analyzer",
    "project_generalization_checker",
    "gn_validation_rules",
    "gn_reporter",
    "gn_export",
    "phase_gn1_orchestrator",
]:
    _load_sub(_sub)


OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseGN.1_general_notes_context_audit"

orch_mod     = sys.modules[f"{pkg_name}.phase_gn1_orchestrator"]
Orchestrator = orch_mod.PhaseGN1Orchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

score = result["validation_score"]
passed, total = map(int, score.split("/"))

print(f"\n  PHASE GN.1 RESULT")
print(f"  Validation score : {score}")
print(f"  Verdict          : {result['verdict']}")
print(f"  Gaps identified  : {result['gap_count']}")
print(f"  Artefacts written: {len(result['export_paths'])}")

sys.exit(0 if passed == total else 1)

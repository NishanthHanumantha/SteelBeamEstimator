"""
run_phase_r2a_engineering_context.py
Runner for Phase R.2A — General Notes Runtime Parsing & Engineering Context Injection
MODEL_VERSION: 7.5.0

Usage (from project root):
    python Version7/Run_PY/run_phase_r2a_engineering_context.py
"""
import importlib.util
import pathlib
import sys
import types

SCRIPT_DIR    = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent
VERSION7_SRC  = PROJECT_ROOT / "Version7" / "src"
VERSION7_ROOT = PROJECT_ROOT / "Version7"

if str(VERSION7_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION7_SRC))

_PKG_DIR  = VERSION7_SRC / "PhaseR.2A_engineering_context"
pkg_name  = "PhaseR2A"

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
    "engineering_context_model",
    "general_notes_text_extractor",
    "general_notes_classifier",
    "development_length_parser",
    "cover_parser",
    "steel_grade_parser",
    "concrete_grade_parser",
    "hook_rule_parser",
    "lap_rule_parser",
    "engineering_context_builder",
    "engineering_context_validator",
    "engineering_context_loader",
    "engineering_context_cache",
    "engineering_context_factory",
    "engineering_context_validation",
    "engineering_context_writer",
    "engineering_context_statistics",
    "engineering_context_audit",
    "engineering_context_parser",
    "phase_r2a_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR   = VERSION7_ROOT / "data" / "output" / "PhaseR.2A_engineering_context"
orch_mod     = sys.modules[f"{pkg_name}.phase_r2a_orchestrator"]
Orchestrator = orch_mod.PhaseR2AOrchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

score   = result.get("audit_score", "0/0")
status  = result.get("status", "FAIL")

print(f"\n  PHASE R.2A.1 RESULT")
print(f"  Status             : {status}")
print(f"  17-criteria audit  : {score}")
print(f"  10-rule Fe550 val  : {result.get('fe550_validation_score', '?')}")
print(f"  Steel grade        : {result.get('primary_steel_grade')}")
print(f"  Beam cover         : {result.get('cover_beam_mm')}mm")
print(f"  DL entries (total) : {result.get('dl_table_entries')}")
print(f"  Artefacts          : {len(result.get('export_paths', {}))}")

sys.exit(0 if status in ("PASS", "PARTIAL") else 1)

"""
run_phase_r2a2_block_expansion.py
Runner for Phase R.2A.2 — Nested Block Expansion & GN Entity Extraction
MODEL_VERSION: 7.5.3

Usage (from project root):
    python Version7/Run_PY/run_phase_r2a2_block_expansion.py
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

_PKG_DIR = VERSION7_SRC / "PhaseR.2A_engineering_context"
pkg_name = "PhaseR2A"

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
    "engineering_context_model",
    "general_notes_text_extractor",
    "development_length_parser",
    "engineering_context_builder",
    "engineering_context_validator",
    "engineering_context_loader",
    "engineering_context_cache",
    "engineering_context_factory",
    "steel_grade_parser",
    "cover_parser",
    "concrete_grade_parser",
    "hook_rule_parser",
    "lap_rule_parser",
    "general_notes_classifier",
    "block_expansion_validator",
    "block_expansion_writer",
    "phase_r2a2_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR.2A.2_engineering_context"
orch_mod = sys.modules[f"{pkg_name}.phase_r2a2_orchestrator"]
Orchestrator = orch_mod.PhaseR2A2Orchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

print(f"\n  PHASE R.2A.2 RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation_score')}")
print(f"  Total entities   : {result.get('total_entities')}")
print(f"  Block entities   : {result.get('block_entities')}")
print(f"  LD headers       : {result.get('ld_headers')}")
print(f"  DL entries       : {result.get('dl_table_entries')}")
print(f"  Fe550 entries    : {result.get('fe550_entries')}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

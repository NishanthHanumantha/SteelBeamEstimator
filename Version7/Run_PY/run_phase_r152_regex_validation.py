"""
run_phase_r152_regex_validation.py
Runner for Phase R.1.5.2 — Reinforcement Pattern Coverage & Regex Validation
MODEL_VERSION: 7.8.3 — READ-ONLY

Usage (from project root):
    python Version7/Run_PY/run_phase_r152_regex_validation.py
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

_PKG_DIR = VERSION7_SRC / "PhaseR1.5.2_regex_validation"
pkg_name = "PhaseR152"

pkg_mod = types.ModuleType(pkg_name)
pkg_mod.__path__ = [str(_PKG_DIR)]
pkg_mod.__package__ = pkg_name
sys.modules[pkg_name] = pkg_mod

MODULES = [
    "__init__",
    "regex_validation_models",
    "production_regex_loader",
    "raw_text_inventory",
    "mtext_cleaning_trace",
    "pattern_inventory",
    "regex_match_validator",
    "pattern_classifier",
    "unsupported_pattern_detector",
    "engineering_notation_validator",
    "regex_statistics",
    "regex_coverage_analyzer",
    "regex_validation_validator",
    "regex_validation_reporter",
    "regex_validation_export",
    "phase_r152_orchestrator",
]


def _load_sub(name: str):
    spec = importlib.util.spec_from_file_location(
        f"{pkg_name}.{name}", _PKG_DIR / f"{name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = pkg_name
    sys.modules[f"{pkg_name}.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


for _sub in MODULES:
    _load_sub(_sub)

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR1.5.2_regex_validation"
orch_mod = sys.modules[f"{pkg_name}.phase_r152_orchestrator"]
Orchestrator = orch_mod.PhaseR152Orchestrator

result = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR).run()

print("\n  PHASE R.1.5.2 RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation', {}).get('score')}")
print(f"  Regex coverage   : {result.get('coverage', {}).get('regex_coverage_pct')}%")
print(f"  Parser readiness : {result.get('coverage', {}).get('parser_readiness_score')}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

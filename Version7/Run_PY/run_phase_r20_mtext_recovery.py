"""
run_phase_r20_mtext_recovery.py
Runner for Phase R.2.0 — MTEXT Engineering Text Recovery Engine
MODEL_VERSION: 7.9.0

Usage (from project root):
    python Version7/Run_PY/run_phase_r20_mtext_recovery.py
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

_PKG_DIR = VERSION7_SRC / "PhaseR2.0_mtext_engineering_text_recovery"
pkg_name = "PhaseR20"

pkg_mod = types.ModuleType(pkg_name)
pkg_mod.__path__ = [str(_PKG_DIR)]
pkg_mod.__package__ = pkg_name
sys.modules[pkg_name] = pkg_mod

MODULES = [
    "__init__",
    "mtext_models",
    "engineering_text_recovery",
    "mtext_inventory",
    "mtext_tokenizer",
    "mtext_formatter_parser",
    "engineering_text_validator",
    "mtext_statistics",
    "mtext_reporter",
    "mtext_export",
    "phase_r20_orchestrator",
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

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR2.0_mtext_engineering_text_recovery"
orch_mod = sys.modules[f"{pkg_name}.phase_r20_orchestrator"]
Orchestrator = orch_mod.PhaseR20Orchestrator

result = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR).run()

print("\n  PHASE R.2.0 RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation', {}).get('score')}")
print(f"  Recovered        : {result.get('statistics', {}).get('recovered')}")
print(f"  Y10 recovered    : {result.get('regression', {}).get('y10_recovered')}")
print(f"  Backward compat  : {result.get('statistics', {}).get('backward_compat_pct')}%")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

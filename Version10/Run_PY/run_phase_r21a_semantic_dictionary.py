"""
run_phase_r21a_semantic_dictionary.py
Runner for Phase R.2.1A â€” Engineering Semantic Dictionary Engine
MODEL_VERSION: 7.10.0 â€” READ-ONLY FOUNDATION

Usage (from project root):
    python Version8/Run_PY/run_phase_r21a_semantic_dictionary.py
"""
import importlib.util
import pathlib
import sys
import types

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
Version8_SRC = PROJECT_ROOT / "Version8" / "src"
Version8_ROOT = PROJECT_ROOT / "Version8"

if str(Version8_SRC) not in sys.path:
    sys.path.insert(0, str(Version8_SRC))

_PKG_DIR = Version8_SRC / "PhaseR2.1A_engineering_semantic_dictionary"
pkg_name = "PhaseR21A"

pkg_mod = types.ModuleType(pkg_name)
pkg_mod.__path__ = [str(_PKG_DIR)]
pkg_mod.__package__ = pkg_name
sys.modules[pkg_name] = pkg_mod

MODULES = [
    "__init__",
    "semantic_dictionary_models",
    "notation_inventory_loader",
    "engineering_vocabulary_resolver",
    "semantic_dictionary_builder",
    "semantic_dictionary_cache",
    "semantic_dictionary_versioning",
    "semantic_dictionary_loader",
    "semantic_dictionary_validator",
    "semantic_dictionary_statistics",
    "semantic_dictionary_reporter",
    "semantic_dictionary_export",
    "phase_r21a_orchestrator",
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

OUTPUT_DIR = (
    Version8_ROOT / "data" / "output" / "PhaseR2.1A_engineering_semantic_dictionary"
)
orch_mod = sys.modules[f"{pkg_name}.phase_r21a_orchestrator"]
Orchestrator = orch_mod.PhaseR21AOrchestrator

result = Orchestrator(v7_root=Version8_ROOT, output_dir=OUTPUT_DIR).run()

print("\n  PHASE R.2.1A RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation', {}).get('score')}")
print(f"  Entries          : {result.get('statistics', {}).get('unique_entries')}")
print(f"  Coverage %       : {result.get('statistics', {}).get('coverage_pct')}")
print(f"  Dict version     : {result.get('version', {}).get('dictionary_version')}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)


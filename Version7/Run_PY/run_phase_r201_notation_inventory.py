"""
run_phase_r201_notation_inventory.py
Runner for Phase R.2.0.1 — Engineering Notation Semantic Inventory
MODEL_VERSION: 7.9.1 — READ-ONLY DISCOVERY

Usage (from project root):
    python Version7/Run_PY/run_phase_r201_notation_inventory.py
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

_PKG_DIR = VERSION7_SRC / "PhaseR2.0.1_engineering_notation_inventory"
pkg_name = "PhaseR201"

pkg_mod = types.ModuleType(pkg_name)
pkg_mod.__path__ = [str(_PKG_DIR)]
pkg_mod.__package__ = pkg_name
sys.modules[pkg_name] = pkg_mod

MODULES = [
    "__init__",
    "notation_models",
    "notation_inventory_loader",
    "notation_extractor",
    "notation_normalizer",
    "notation_pattern_grouper",
    "engineering_symbol_detector",
    "semantic_category_classifier",
    "notation_frequency_analyzer",
    "notation_support_analyzer",
    "notation_inventory_database",
    "notation_statistics",
    "notation_validator",
    "notation_reporter",
    "notation_export",
    "phase_r201_orchestrator",
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
    VERSION7_ROOT / "data" / "output" / "PhaseR2.0.1_engineering_notation_inventory"
)
orch_mod = sys.modules[f"{pkg_name}.phase_r201_orchestrator"]
Orchestrator = orch_mod.PhaseR201Orchestrator

result = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR).run()

print("\n  PHASE R.2.0.1 RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation', {}).get('score')}")
print(f"  Unique notations : {result.get('statistics', {}).get('total_unique_notations')}")
print(f"  Supported %      : {result.get('statistics', {}).get('supported_pct')}")
print(f"  Unsupported %    : {result.get('statistics', {}).get('unsupported_pct')}")
print(f"  Priorities       : {len(result.get('priorities', []))}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)

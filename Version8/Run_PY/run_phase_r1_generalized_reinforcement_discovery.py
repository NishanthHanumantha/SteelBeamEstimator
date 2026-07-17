"""
run_phase_r1_generalized_reinforcement_discovery.py
Runner script for Phase R.1 — Generalized Reinforcement Discovery.

Usage:
    python Version8/Run_PY/run_phase_r1_generalized_reinforcement_discovery.py

Must be run from the SteelBeamEstimator project root.
"""

import importlib.util
import pathlib
import sys

# ── Resolve paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR   = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent          # SteelBeamEstimator/
VERSION7_SRC = PROJECT_ROOT / "Version8" / "src"

# Add Version8/src to sys.path so PhaseR.1 package is importable
if str(VERSION7_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION7_SRC))

# The package dir contains a dot, so import via importlib
_PKG_DIR  = VERSION7_SRC / "PhaseR.1_generalized_reinforcement_discovery"
_INIT     = _PKG_DIR / "__init__.py"
_ORCH     = _PKG_DIR / "phase_r1_orchestrator.py"

# Load orchestrator module directly
spec = importlib.util.spec_from_file_location(
    "PhaseR1.phase_r1_orchestrator", _ORCH
)
mod = importlib.util.module_from_spec(spec)

# Register sub-modules so relative imports work
import types
pkg_name = "PhaseR1"
pkg_mod  = types.ModuleType(pkg_name)
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
    "reinforcement_models",
    "dxf_text_utils",
    "beam_detail_discovery",
    "adaptive_association_engine",
    "beam_detail_segmenter",
    "annotation_discovery",
    "reinforcement_annotation_classifier",
    "reinforcement_geometry_mapper",
    "reinforcement_group_builder",
    "reinforcement_role_classifier",
    "reinforcement_relationship_builder",
    "engineering_reinforcement_builder",
    "reinforcement_statistics",
    "reinforcement_validator",
    "reinforcement_reporter",
    "reinforcement_export",
    "phase_r1_orchestrator",
]:
    _load_sub(_sub)

# ── Run ────────────────────────────────────────────────────────────────────────
orchestrator_mod = sys.modules[f"{pkg_name}.phase_r1_orchestrator"]
run_phase_r1     = orchestrator_mod.run_phase_r1

version7_root    = PROJECT_ROOT / "Version8"
config_path      = version7_root / "config" / "generalized_reinforcement_discovery.yaml"

result = run_phase_r1(version7_root, config_path)

# ── Exit code ─────────────────────────────────────────────────────────────────
if result.get("status") in ("PASS", "SUCCESS"):
    sys.exit(0)
else:
    sys.exit(1)

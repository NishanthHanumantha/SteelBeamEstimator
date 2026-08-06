"""
run_phase_r1_generalized_reinforcement_discovery.py
Runner script for Phase R.1 — Generalized Reinforcement Discovery.

Usage (from Version9/):
    python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py
    python Run_PY/run_phase_r1_generalized_reinforcement_discovery.py <run_root>

MODEL_VERSION: 9.2.0 — loads Version9 src/config (not Version8).
"""

import importlib.util
import os
import pathlib
import sys
import types

# ── Resolve paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_DIR.parent  # Version9/
VERSION_SRC = ENGINE_ROOT / "src"
PROJECT_ROOT = ENGINE_ROOT.parent  # SteelBeamEstimator/ (for config.run_context)

if str(VERSION_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION_SRC))
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

_PKG_DIR = VERSION_SRC / "PhaseR.1_generalized_reinforcement_discovery"

pkg_name = "PhaseR1"
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

from config.run_context import resolve_run_context, run_root_from_argv

orchestrator_mod = sys.modules[f"{pkg_name}.phase_r1_orchestrator"]
run_phase_r1 = orchestrator_mod.run_phase_r1

# Prefer STEEL_ENGINE_ROOT (set by QA.2 pipeline) else this Version9 tree
engine_root = pathlib.Path(os.environ.get("STEEL_ENGINE_ROOT", str(ENGINE_ROOT)))
arg = run_root_from_argv(sys.argv, 1)
ctx = resolve_run_context(run_root_arg=arg, engine_root=engine_root)
os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

config_path = ctx.engine_root / "config" / "generalized_reinforcement_discovery.yaml"
print(f"[R1] engine_root={ctx.engine_root}")
print(f"[R1] run_root={ctx.run_root}")
print(f"[R1] output_root={ctx.output_root}")
print(f"[R1] config={config_path}")

result = run_phase_r1(ctx.run_root, config_path, engine_root=ctx.engine_root)

if result.get("status") in ("PASS", "SUCCESS"):
    sys.exit(0)
else:
    sys.exit(1)

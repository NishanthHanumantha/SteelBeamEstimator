"""
run_phase_r21b_semantic_interpreter.py — Phase R.2.1B Runner
MODEL_VERSION: 8.9.0

Usage (from project root):
    python Version8/Run_PY/run_phase_r21b_semantic_interpreter.py
    python Version8/Run_PY/run_phase_r21b_semantic_interpreter.py <run_root>

Web: set STEEL_RUN_ROOT / STEEL_OUTPUT_ROOT (preferred) or pass run_root as argv[1].
"""
from __future__ import annotations

import importlib.util
import logging
import os
import pathlib
import sys
import types

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
Version8_SRC = PROJECT_ROOT / "Version8" / "src"
Version8_ROOT = PROJECT_ROOT / "Version8"

for _p in [str(Version8_SRC), str(Version8_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

_PKG_DIR = Version8_SRC / "PhaseR2.1B_engineering_semantic_interpreter"
_PKG_NAME = "PhaseR21B"

_pkg_mod = types.ModuleType(_PKG_NAME)
_pkg_mod.__path__ = [str(_PKG_DIR)]
_pkg_mod.__package__ = _PKG_NAME
sys.modules[_PKG_NAME] = _pkg_mod

_MODULES = [
    "__init__",
    "semantic_models",
    "semantic_context_builder",
    "semantic_modifier_parser",
    "semantic_role_resolver",
    "semantic_quantity_resolver",
    "semantic_placement_resolver",
    "semantic_conflict_resolver",
    "engineering_meaning_builder",
    "semantic_interpreter",
    "semantic_validation",
    "semantic_statistics",
    "semantic_reporter",
    "semantic_export",
    "phase_r21b_orchestrator",
]

for _sub in _MODULES:
    _mod_key = f"{_PKG_NAME}.{_sub}"
    _spec = importlib.util.spec_from_file_location(_mod_key, _PKG_DIR / f"{_sub}.py")
    _mod = importlib.util.module_from_spec(_spec)
    _mod.__package__ = _PKG_NAME
    sys.modules[_mod_key] = _mod
    _spec.loader.exec_module(_mod)

PhaseR21BOrchestrator = sys.modules[f"{_PKG_NAME}.phase_r21b_orchestrator"].PhaseR21BOrchestrator


def main() -> int:
    from config.run_context import PHASE_R21B, resolve_run_context, run_root_from_argv

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=Version8_ROOT)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    out_dir = ctx.artefact(PHASE_R21B)
    print(f"[R2.1B] engine_root={ctx.engine_root}")
    print(f"[R2.1B] run_root={ctx.run_root}")
    print(f"[R2.1B] output_dir={out_dir}")

    orchestrator = PhaseR21BOrchestrator(
        engine_root=ctx.engine_root,
        output_root=ctx.output_root,
        output_dir=out_dir,
    )
    result = orchestrator.run()

    eso = out_dir / "engineering_semantic_objects.json"
    validation = result.get("validation", {})
    all_pass = validation.get("all_pass", False)

    if not all_pass:
        failed = [
            rid for rid, rd in (validation.get("rules") or {}).items()
            if not rd.get("passed")
        ]
        print(f"\n[WARN] {len(failed)} validation rule(s) failed: {', '.join(failed)}")
        if eso.exists():
            print(f"[OK] engineering_semantic_objects.json present at {eso} — continuing")
            return 0
        return 1

    print(f"\n[OK] Phase R.2.1B complete — {validation.get('summary')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

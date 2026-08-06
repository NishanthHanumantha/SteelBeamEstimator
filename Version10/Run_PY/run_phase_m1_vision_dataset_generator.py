"""
run_phase_m1_vision_dataset_generator.py
=========================================
Phase M.1 — Engineering Vision Dataset Generator
MODEL_VERSION: 9.0.0

Generates a structured engineering vision dataset from deterministic
pipeline outputs.  The dataset is completely separate from production
web_runs and can be reused for future AI benchmarking without manual
annotation.

Usage (from Version9/ directory)
---------------------------------
  # Use default pipeline outputs in data/output/
  python Run_PY/run_phase_m1_vision_dataset_generator.py

  # Specify a DXF file explicitly
  python Run_PY/run_phase_m1_vision_dataset_generator.py \\
      --dxf-path data/Benchmark_Set_2/reinforcement/Galera_GF_BeamReinforcementDetails.dxf

  # Full control
  python Run_PY/run_phase_m1_vision_dataset_generator.py \\
      --output-root data/output \\
      --dxf-path data/Benchmark_Set_2/reinforcement/Galera_GF_BeamReinforcementDetails.dxf \\
      --padding-mm 3000

  # Run against a web_run
  python Run_PY/run_phase_m1_vision_dataset_generator.py \\
      --output-root data/web_runs/<run_id>/data/output \\
      --dxf-path   data/web_runs/<run_id>/reinforcement/<file>.dxf

Prerequisites
-------------
  pip install matplotlib Pillow

Output
------
  Version9/data/vision_dataset/run_<timestamp>/
      images/            — clean beam crop PNGs
      annotations/       — annotation JSON (deterministic labels)
      metadata/          — per-beam metadata JSON
      previews/          — quality-inspection preview PNGs
      dataset_manifest.json
      dataset_validation.json
      _full_render.png   — full DXF rendering (kept for reference)

DO NOT MODIFY
-------------
  This phase does NOT modify engineering logic, production pipeline,
  Excel generation, or any web application code.
  Version 8.9.5 remains the production baseline.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import types
from pathlib import Path

# ── Resolve paths ─────────────────────────────────────────────────────────────
_RUNNER_DIR  = Path(__file__).resolve().parent     # Version9/Run_PY/
_ENGINE_ROOT = _RUNNER_DIR.parent                  # Version9/
_PKG_DIR     = _ENGINE_ROOT / "src" / "PhaseM.1_engineering_vision_dataset"

# ── Bootstrap synthetic package "PhaseM1" ────────────────────────────────────
# The directory name contains a dot so it is not a valid Python identifier.
# We register a synthetic package under a clean alias and load each module
# using importlib, matching the pattern used by other phase runners.

_PKG_ALIAS = "PhaseM1"

_SUBMODULES = [
    "__init__",
    "pipeline_reader",
    "dxf_renderer",
    "beam_cropper",
    "annotation_builder",
    "metadata_builder",
    "preview_generator",
    "manifest_builder",
    "dataset_validator",
    "dataset_exporter",
    "phase_m1_orchestrator",
]


def _bootstrap_package() -> types.ModuleType:
    """Register PhaseM.1_engineering_vision_dataset as the 'PhaseM1' package."""
    pkg = types.ModuleType(_PKG_ALIAS)
    pkg.__path__    = [str(_PKG_DIR)]
    pkg.__package__ = _PKG_ALIAS
    sys.modules[_PKG_ALIAS] = pkg

    for sub in _SUBMODULES:
        full_name = f"{_PKG_ALIAS}.{sub}"
        spec = importlib.util.spec_from_file_location(
            full_name, _PKG_DIR / f"{sub}.py"
        )
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = _PKG_ALIAS
        sys.modules[full_name] = mod
        # Also expose as attribute on the package (enables relative imports)
        if sub != "__init__":
            setattr(pkg, sub, mod)

    # Execute all modules (resolves relative imports via sys.modules)
    for sub in _SUBMODULES:
        sys.modules[f"{_PKG_ALIAS}.{sub}"].spec.loader.exec_module(  # type: ignore[attr-defined]
            sys.modules[f"{_PKG_ALIAS}.{sub}"]
        )

    return pkg


# ── Fallback: simpler load that patches relative imports ──────────────────────

def _load_package_simple() -> types.ModuleType:
    """
    Alternative bootstrap: add src/ to sys.path and rename package dir.
    Used if the spec-based approach fails.
    """
    src_dir = str(_ENGINE_ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    pkg = types.ModuleType(_PKG_ALIAS)
    pkg.__path__    = [str(_PKG_DIR)]
    pkg.__package__ = _PKG_ALIAS
    sys.modules[_PKG_ALIAS] = pkg

    loaded: dict = {}

    # Register all module shells FIRST (before executing any)
    # so that relative imports inside exec_module find siblings in sys.modules.
    for sub in _SUBMODULES:
        full_name = f"{_PKG_ALIAS}.{sub}"
        spec = importlib.util.spec_from_file_location(
            full_name, _PKG_DIR / f"{sub}.py"
        )
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = _PKG_ALIAS
        sys.modules[full_name] = mod
        loaded[sub] = (spec, mod)
        if sub != "__init__":
            setattr(pkg, sub, mod)

    # Execute all modules in dependency order
    for sub in _SUBMODULES:
        spec, mod = loaded[sub]
        spec.loader.exec_module(mod)   # type: ignore[union-attr]

        # After executing __init__, merge its public names into the package
        # so that `from . import X` patterns work for sibling modules.
        if sub == "__init__":
            for attr, val in vars(mod).items():
                if not attr.startswith("__"):
                    setattr(pkg, attr, val)

    return pkg


def _get_orchestrator_class():
    """Load the orchestrator class, bootstrapping the package if needed."""
    try:
        pkg = _load_package_simple()
    except Exception as exc:
        print(f"[WARN] Package bootstrap error: {exc}", file=sys.stderr)
        raise

    orch_mod = sys.modules.get(f"{_PKG_ALIAS}.phase_m1_orchestrator")
    if orch_mod is None:
        raise ImportError("phase_m1_orchestrator module not loaded")
    return orch_mod.PhaseM1Orchestrator


# ── Argument parser ───────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase M.1 — Engineering Vision Dataset Generator.\n\n"
            "Generates beam images, annotation JSON, metadata, previews,\n"
            "manifest and validation report from deterministic pipeline outputs."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Pipeline data/output/ directory containing phase artefacts "
            "(PhaseVROOT.1, PhaseR.1, PhaseR3, PhaseR1.3). "
            "Defaults to <engine_root>/data/output/"
        ),
    )
    parser.add_argument(
        "--dxf-path",
        type=Path,
        default=None,
        metavar="FILE",
        help=(
            "Path to the DXF file to render. "
            "Auto-discovered from beam_registry or data/ if omitted."
        ),
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Output directory for the vision dataset. "
            "Defaults to <engine_root>/data/vision_dataset/run_<timestamp>/"
        ),
    )
    parser.add_argument(
        "--padding-mm",
        type=float,
        default=3000.0,
        metavar="MM",
        help="Padding around each beam crop in mm. Default: 3000.",
    )
    return parser.parse_args()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    args = _parse_args()

    output_root = args.output_root or (_ENGINE_ROOT / "data" / "output")
    output_root = Path(output_root)

    if not output_root.exists():
        print(
            f"\n[ERROR] output-root not found: {output_root}\n"
            f"        Run the production pipeline first, or pass a valid "
            f"--output-root path.\n",
            file=sys.stderr,
        )
        return 1

    # Load orchestrator
    try:
        OrchestratorClass = _get_orchestrator_class()
    except ImportError as exc:
        print(
            f"\n[ERROR] Failed to load Phase M.1 package:\n  {exc}\n",
            file=sys.stderr,
        )
        return 1

    orch = OrchestratorClass(
        engine_root  = _ENGINE_ROOT,
        output_root  = output_root,
        dxf_path     = args.dxf_path,
        dataset_root = args.dataset_root,
        padding_mm   = args.padding_mm,
    )

    try:
        summary = orch.run()
    except RuntimeError as exc:
        print(f"\n[ERROR] Phase M.1 failed:\n  {exc}\n", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(
            f"\n[ERROR] Missing dependency:\n  {exc}\n"
            f"  Install with:  pip install matplotlib Pillow\n",
            file=sys.stderr,
        )
        return 1

    return 0 if summary.get("validation_status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

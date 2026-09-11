"""
run_phase_r13_pipeline_integration.py
Runner for Phase R.1.3 — Generalized Reinforcement Pipeline Integration
MODEL_VERSION: 8.9.4

Usage:
    python Version8/Run_PY/run_phase_r13_pipeline_integration.py
    python Version8/Run_PY/run_phase_r13_pipeline_integration.py <run_root>

Output:
    <output_root>/PhaseR1.3_pipeline_integration/
    Soft-exit 0 if beam_reinforcement_models_production.json exists.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import types


def _bootstrap_package(pkg_dir: pathlib.Path, alias: str, pkg_name: str) -> None:
    pkg_dir = pathlib.Path(pkg_dir)
    if not pkg_dir.exists():
        raise FileNotFoundError(f"Package directory not found: {pkg_dir}")

    src_dir = str(pkg_dir.parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    if alias not in sys.modules:
        virtual_pkg = types.ModuleType(alias)
        virtual_pkg.__path__ = [str(pkg_dir)]
        virtual_pkg.__package__ = alias
        virtual_pkg.__spec__ = importlib.util.spec_from_file_location(
            alias, str(pkg_dir / "__init__.py")
        )
        sys.modules[alias] = virtual_pkg

    for py_file in sorted(pkg_dir.glob("*.py")):
        mod_name = py_file.stem
        full_name = alias if mod_name == "__init__" else f"{alias}.{mod_name}"
        if full_name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(full_name, str(py_file))
        if spec is None:
            continue
        module = importlib.util.module_from_spec(spec)
        module.__package__ = alias
        sys.modules[full_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            del sys.modules[full_name]
            raise RuntimeError(f"Failed to load {py_file}: {exc}") from exc

    if pkg_name not in sys.modules:
        sys.modules[pkg_name] = sys.modules[alias]


def main() -> None:
    root = pathlib.Path(__file__).parent.parent  # Version8/
    src = root / "src"
    pkg_dir = src / "PhaseR1.3_pipeline_integration"
    pkg_name = "PhaseR1.3_pipeline_integration"
    alias = "PhaseR13"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import (
        PHASE_R13,
        resolve_run_context,
        run_root_from_argv,
    )
    from PhaseR13.phase_r13_orchestrator import PhaseR13Orchestrator

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    out_dir = ctx.artefact(PHASE_R13)
    prod_models = out_dir / "beam_reinforcement_models_production.json"

    print(f"[R.1.3] engine_root={ctx.engine_root}")
    print(f"[R.1.3] run_root={ctx.run_root}")
    print(f"[R.1.3] output_dir={out_dir}")

    orchestrator = PhaseR13Orchestrator(
        engine_root=ctx.engine_root,
        run_root=ctx.run_root,
        output_root=ctx.output_root,
        output_dir=out_dir,
        skip_production=True,
    )
    result = orchestrator.run()

    print()
    print("=" * 70)
    print("PHASE R.1.3 — PIPELINE INTEGRATION — COMPLETE")
    print("=" * 70)
    print(f"  Model version : {result.get('model_version', PhaseR13Orchestrator.MODEL_VERSION)}")
    print(f"  Status        : {result.get('status')}")
    print(f"  Validation    : {result.get('validation_score')}")
    print(f"  Beams (steel) : {result.get('comparison', {}).get('after', {}).get('beams_reaching_steel')}")
    print(f"  Artefacts     : {len(result.get('export_paths', {}))}")
    print(f"  Output dir    : {out_dir}")
    print()

    if prod_models.exists():
        print(f"  [OK] beam_reinforcement_models_production.json present at {prod_models} — continuing")
        print("=" * 70)
        sys.exit(0)

    if result.get("status") == "PASS":
        print("  [OK] Phase R.1.3 complete")
        print("=" * 70)
        sys.exit(0)

    print("  [FAIL] beam_reinforcement_models_production.json missing")
    print("=" * 70)
    sys.exit(1)


if __name__ == "__main__":
    main()

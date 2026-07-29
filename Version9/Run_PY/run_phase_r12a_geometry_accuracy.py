"""
run_phase_r12a_geometry_accuracy.py
Runner for Phase R.1.2A — Geometry Accuracy & Span Propagation Engine
MODEL_VERSION: 8.9.4

Usage:
    python Version8/Run_PY/run_phase_r12a_geometry_accuracy.py
    python Version8/Run_PY/run_phase_r12a_geometry_accuracy.py <run_root>
    python Version8/Run_PY/run_phase_r12a_geometry_accuracy.py <run_root> --full

Production (web + offline): catalog_only — GeometryProvider resolve only.
Forensic rebuild of R13/VB1: pass --full (offline-only).
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
    pkg_dir = src / "PhaseR1_2A_geometry_accuracy"
    pkg_name = "PhaseR1_2A_geometry_accuracy"
    alias = "PhaseR12A"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import (
        PHASE_R12A,
        resolve_run_context,
    )
    from PhaseR12A.phase_r12a_orchestrator import PhaseR12AOrchestrator

    full_forensic = "--full" in sys.argv[1:]
    positional = [a for a in sys.argv[1:] if not str(a).startswith("-")]
    arg = pathlib.Path(positional[0]) if positional else None

    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    out_dir = ctx.artefact(PHASE_R12A)
    catalog = out_dir / "validated_beam_geometry.json"

    print(f"[R.1.2A] engine_root={ctx.engine_root}")
    print(f"[R.1.2A] run_root={ctx.run_root}")
    print(f"[R.1.2A] output_dir={out_dir}")
    print(f"[R.1.2A] mode={'full_forensic' if full_forensic else 'catalog_only'}")

    orchestrator = PhaseR12AOrchestrator(
        run_root=ctx.run_root,
        output_root=ctx.output_root,
        v7_root=ctx.engine_root,
        catalog_only=not full_forensic,
    )
    result = orchestrator.run()

    print()
    print("=" * 70)
    print("PHASE R.1.2A — GEOMETRY ACCURACY — COMPLETE")
    print("=" * 70)
    print(f"  Model version : {result.get('model_version')}")
    print(f"  Mode          : {result.get('mode')}")
    print(f"  Status        : {result.get('status')}")
    print(f"  Output dir    : {out_dir}")
    print()

    if catalog.exists():
        print(f"  [OK] validated_beam_geometry.json present at {catalog} — continuing")
        print("=" * 70)
        sys.exit(0)

    print("  [FAIL] validated_beam_geometry.json missing")
    print("=" * 70)
    sys.exit(1)


if __name__ == "__main__":
    main()

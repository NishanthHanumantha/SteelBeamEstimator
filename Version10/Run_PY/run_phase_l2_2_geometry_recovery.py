"""
run_phase_l2_2_geometry_recovery.py
Runner for Phase L.2.2 — Geometry Registry Generation.
MODEL_VERSION: 8.9.2

Usage:
    python Version8/Run_PY/run_phase_l2_2_geometry_recovery.py
    python Version8/Run_PY/run_phase_l2_2_geometry_recovery.py <run_root>

Prerequisites:
    Phase VROOT1 must have been run for the same run_root.
    Input: <output_root>/PhaseVROOT.1_.../beam_registry.json
    Optional: <output_root>/PhaseVROOT.1_.../dynamic_beam_geometry.json

Output:
    <output_root>/PhaseL.2.2_geometry_recovery/geometry_registry.json
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
    pkg_dir = src / "PhaseL.2.2_geometry_recovery"
    pkg_name = "PhaseL.2.2_geometry_recovery"
    alias = "PhaseL22"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import PHASE_L22, PHASE_VROOT1, resolve_run_context, run_root_from_argv
    from PhaseL22.phase_l22_orchestrator import PhaseL22Orchestrator

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    beam_reg = ctx.artefact(PHASE_VROOT1, "beam_registry.json")
    dyn_geo = ctx.artefact(PHASE_VROOT1, "dynamic_beam_geometry.json")
    out_dir = ctx.artefact(PHASE_L22)

    print(f"[L.2.2] engine_root={ctx.engine_root}")
    print(f"[L.2.2] run_root={ctx.run_root}")
    print(f"[L.2.2] beam_registry={beam_reg}")
    print(f"[L.2.2] output_dir={out_dir}")

    orchestrator = PhaseL22Orchestrator(
        beam_registry_path=beam_reg,
        dynamic_geometry_path=dyn_geo,
        output_dir=out_dir,
        output_root=ctx.output_root,
        engine_root=ctx.engine_root,
    )
    result = orchestrator.run()

    print()
    print("=" * 60)
    print("PHASE L.2.2 — SUMMARY")
    print("=" * 60)
    print(f"  Beams              : {result['beam_count']}")
    print(f"  Original           : {result['original_count']}")
    print(f"  Recovered          : {result['recovered_count']}")
    print(f"  Failed             : {result['failed_count']}")
    print(f"  Export             : {result['export_validation'].get('status')}")
    print(f"  Elapsed            : {result['elapsed_seconds']}s")
    print(f"  MODEL_VERSION      : {result['model_version']}")
    print(f"  geometry_registry  : {result['geometry_registry_path']}")
    print("=" * 60)

    geo_out = out_dir / "geometry_registry.json"
    if not result["success"]:
        print("\n[WARNING] L.2.2 completed with issues. See details above.")
        if geo_out.exists():
            print(f"[OK] geometry_registry.json present at {geo_out} — continuing")
            sys.exit(0)
        sys.exit(1)

    print("\n[OK] Phase L.2.2 complete — geometry_registry ready for R.3.")


if __name__ == "__main__":
    main()

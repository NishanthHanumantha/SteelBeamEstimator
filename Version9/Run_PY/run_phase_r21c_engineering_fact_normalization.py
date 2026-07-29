"""
run_phase_r21c_engineering_fact_normalization.py
Runner for Phase R.2.1C — Engineering Fact Normalization Engine.
MODEL_VERSION: 8.9.0

Usage:
    python Version8/Run_PY/run_phase_r21c_engineering_fact_normalization.py
    python Version8/Run_PY/run_phase_r21c_engineering_fact_normalization.py <run_root>

Prerequisites:
    Phase R.2.1B must have been run for the same run_root.
    Input: <output_root>/PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json
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
        if mod_name == "__init__":
            full_name = alias
        else:
            full_name = f"{alias}.{mod_name}"

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

    pkg_dir = src / "PhaseR2.1C_engineering_fact_normalization"
    pkg_name = "PhaseR2.1C_engineering_fact_normalization"
    alias = "PhaseR21C"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import PHASE_R21C, resolve_run_context, run_root_from_argv
    from PhaseR21C.phase_r21c_orchestrator import PhaseR21COrchestrator

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    eso_path = ctx.artefact(
        "PhaseR2.1B_engineering_semantic_interpreter",
        "engineering_semantic_objects.json",
    )
    out_dir = ctx.artefact(PHASE_R21C)
    print(f"[R2.1C] engine_root={ctx.engine_root}")
    print(f"[R2.1C] run_root={ctx.run_root}")
    print(f"[R2.1C] eso_path={eso_path}")
    print(f"[R2.1C] output_dir={out_dir}")

    orchestrator = PhaseR21COrchestrator(
        eso_path=eso_path,
        output_dir=out_dir,
        output_root=ctx.output_root,
        engine_root=ctx.engine_root,
    )
    result = orchestrator.run()

    print()
    print("=" * 60)
    print("PHASE R.2.1C — SUMMARY")
    print("=" * 60)
    print(f"  Beams processed : {result['beam_count']}")
    print(f"  Total facts     : {result['total_facts']}")
    stats = result.get("statistics", {})
    print(f"  Intent UNKNOWN  : {stats.get('intent_unknown_count', 0)}/{result['total_facts']}")
    print(f"  Geometry req.   : {stats.get('geometry_required_count', 0)}")
    print(f"  Role coverage   : {stats.get('role_coverage_pct', 0)}%")
    print(f"  Placement cov.  : {stats.get('placement_coverage_pct', 0)}%")
    print(f"  Validation      : {result['validation']['summary']}")
    print(f"  Elapsed         : {result['elapsed_seconds']}s")
    print(f"  MODEL_VERSION   : {result['model_version']}")
    print("=" * 60)

    if not result["success"]:
        print("\n[WARNING] Not all validation rules passed. See details above.")
        # Soft-exit 0 if EngineeringFacts.json was written — pipeline may continue
        facts = out_dir / "EngineeringFacts.json"
        if facts.exists():
            print(f"[OK] EngineeringFacts.json present at {facts}")
            sys.exit(0)
        sys.exit(1)

    print("\n[OK] Phase R.2.1C complete — EngineeringFacts ready for R.2.1D.")


if __name__ == "__main__":
    main()

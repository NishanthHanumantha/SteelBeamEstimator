"""
run_phase_r21c_engineering_fact_normalization.py
Runner for Phase R.2.1C — Engineering Fact Normalization Engine.
MODEL_VERSION: 7.12.0

Usage:
    python Version7/Run_PY/run_phase_r21c_engineering_fact_normalization.py

Prerequisites:
    Phase R.2.1B must have been run first.
    Input: Version7/data/output/PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types


def _bootstrap_package(pkg_dir: pathlib.Path, alias: str, pkg_name: str) -> None:
    """
    Load a package whose directory name contains dots (e.g. PhaseR2.1C_...)
    by aliasing it to a valid Python identifier (e.g. PhaseR21C).

    This mirrors the bootstrapping pattern used in R.2.1A/B runners.
    """
    pkg_dir = pathlib.Path(pkg_dir)
    if not pkg_dir.exists():
        raise FileNotFoundError(f"Package directory not found: {pkg_dir}")

    src_dir = str(pkg_dir.parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Create a virtual package module for the alias
    if alias not in sys.modules:
        virtual_pkg = types.ModuleType(alias)
        virtual_pkg.__path__ = [str(pkg_dir)]
        virtual_pkg.__package__ = alias
        virtual_pkg.__spec__ = importlib.util.spec_from_file_location(
            alias, str(pkg_dir / "__init__.py")
        )
        sys.modules[alias] = virtual_pkg

    # Load each module in the package under the alias namespace
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

    # Also register under original dotted name so internal imports work
    if pkg_name not in sys.modules:
        sys.modules[pkg_name] = sys.modules[alias]


def main() -> None:
    root = pathlib.Path(__file__).parent.parent  # Version7/
    src  = root / "src"

    pkg_dir  = src / "PhaseR2.1C_engineering_fact_normalization"
    pkg_name = "PhaseR2.1C_engineering_fact_normalization"
    alias    = "PhaseR21C"

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from PhaseR21C.phase_r21c_orchestrator import PhaseR21COrchestrator

    orchestrator = PhaseR21COrchestrator()
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
        sys.exit(1)

    print("\n[OK] Phase R.2.1C complete — EngineeringFacts ready for R.3.")


if __name__ == "__main__":
    main()

"""
run_phase_r3_geometry_context_engine.py
Runner for Phase R.3 — Geometry Context Engine (MODEL_VERSION: 8.0.0)

Usage:
    python Version7/Run_PY/run_phase_r3_geometry_context_engine.py

The script locates the Version7 root dynamically and runs the full
Geometry Context Engine pipeline:

  R.2.1D EngineeringFacts → Geometry Context → 12 Artefacts

Intent remains UNKNOWN throughout.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types


def _bootstrap_package(pkg_name: str, pkg_dir: pathlib.Path) -> types.ModuleType:
    """
    Register a package with dotted name so its internal relative imports work.
    Required because the package directories use dotted names unsupported
    by default sys.path discovery.
    """
    if pkg_name in sys.modules:
        return sys.modules[pkg_name]

    pkg_init = pkg_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        pkg_name, str(pkg_init),
        submodule_search_locations=[str(pkg_dir)],
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__path__    = [str(pkg_dir)]
    mod.__package__ = pkg_name
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_module(pkg_name: str, mod_name: str, py_file: pathlib.Path) -> types.ModuleType:
    full_name = f"{pkg_name}.{mod_name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(full_name, str(py_file))
    mod  = importlib.util.module_from_spec(spec)
    mod.__package__ = pkg_name
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    here        = pathlib.Path(__file__).resolve()
    version7    = here.parent.parent          # Version7/
    src         = version7 / "src"
    pkg_dir     = src / "PhaseR3_geometry_context_engine"
    pkg_name    = "PhaseR3_geometry_context_engine"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(version7) not in sys.path:
        sys.path.insert(0, str(version7))

    # Bootstrap root package, then load each module individually
    _bootstrap_package(pkg_name, pkg_dir)

    for mod_name in [
        "geometry_models",
        "beam_axis_builder",
        "support_locator",
        "projection_engine",
        "normalized_position_builder",
        "support_zone_classifier",
        "span_zone_classifier",
        "extent_evidence_builder",
        "geometry_context_builder",
        "geometry_validator",
        "geometry_statistics",
        "geometry_reporter",
        "geometry_export",
        "phase_r3_orchestrator",
    ]:
        _load_module(pkg_name, mod_name, pkg_dir / f"{mod_name}.py")

    from PhaseR3_geometry_context_engine.phase_r3_orchestrator import PhaseR3Orchestrator

    orchestrator = PhaseR3Orchestrator(version7_root=version7)
    result = orchestrator.run()

    print()
    print("=" * 70)
    print("PHASE R.3 — GEOMETRY CONTEXT ENGINE — COMPLETE")
    print("=" * 70)
    print(f"  Model version : {result['model_version']}")
    print(f"  Beams         : {result['beam_count']}")
    print(f"  Contexts      : {result['context_count']}")
    print(f"  Validation    : {result['validation']['summary']}")
    print(f"  Output dir    : {result['output_dir']}")
    print()
    if result["validation"]["all_pass"]:
        print("  ALL VALIDATION RULES PASSED")
    else:
        print("  SOME VALIDATION RULES FAILED — review GeometryValidation.json")
    print("=" * 70)


if __name__ == "__main__":
    main()

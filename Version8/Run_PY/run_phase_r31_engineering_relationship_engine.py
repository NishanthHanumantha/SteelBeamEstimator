"""
run_phase_r31_engineering_relationship_engine.py
Runner for Phase R.3.1 — Engineering Drawing Relationship Engine
MODEL_VERSION: 8.1.0

Usage:
    python Version8/Run_PY/run_phase_r31_engineering_relationship_engine.py

DXF drawing → Leader/Arrow/Bar detection → Relationship graph → 12 artefacts
Intent remains UNKNOWN throughout.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types


def _bootstrap(pkg_name: str, pkg_dir: pathlib.Path) -> types.ModuleType:
    if pkg_name in sys.modules:
        return sys.modules[pkg_name]
    spec = importlib.util.spec_from_file_location(
        pkg_name, str(pkg_dir / "__init__.py"),
        submodule_search_locations=[str(pkg_dir)],
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__path__    = [str(pkg_dir)]
    mod.__package__ = pkg_name
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load(pkg_name: str, mod_name: str, py_file: pathlib.Path) -> types.ModuleType:
    full = f"{pkg_name}.{mod_name}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, str(py_file))
    mod  = importlib.util.module_from_spec(spec)
    mod.__package__ = pkg_name
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    here     = pathlib.Path(__file__).resolve()
    v7       = here.parent.parent
    src      = v7 / "src"
    pkg_dir  = src / "PhaseR3.1_engineering_relationship_engine"
    pkg_name = "PhaseR3_1_engineering_relationship_engine"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(v7) not in sys.path:
        sys.path.insert(0, str(v7))

    # Register the package directory under a Python-safe name
    _bootstrap(pkg_name, pkg_dir)

    for mod_name in [
        "relationship_models",
        "leader_discovery",
        "leader_chain_builder",
        "arrow_detector",
        "annotation_relationship_builder",
        "physical_bar_detector",
        "bar_geometry_builder",
        "support_crossing_builder",
        "extent_builder",
        "relationship_graph_builder",
        "relationship_validator",
        "relationship_statistics",
        "relationship_reporter",
        "relationship_export",
        "phase_r31_orchestrator",
    ]:
        _load(pkg_name, mod_name, pkg_dir / f"{mod_name}.py")

    orch_mod = sys.modules[f"{pkg_name}.phase_r31_orchestrator"]
    PhaseR31Orchestrator = orch_mod.PhaseR31Orchestrator

    orchestrator = PhaseR31Orchestrator(version7_root=v7)
    result       = orchestrator.run()

    print()
    print("=" * 72)
    print("PHASE R.3.1 — ENGINEERING DRAWING RELATIONSHIP ENGINE — COMPLETE")
    print("=" * 72)
    print(f"  Model version  : {result['model_version']}")
    print(f"  Facts          : {result['total_facts']}")
    print(f"  Leaders        : {result['total_leaders']}")
    print(f"  Arrows         : {result['total_arrows']}")
    print(f"  Physical bars  : {result['total_bars']}")
    print(f"  Relationships  : {result['total_relationships']}")
    print(f"  Validation     : {result['validation']['summary']}")
    print(f"  Output dir     : {result['output_dir']}")
    print()
    if result["validation"]["all_pass"]:
        print("  ALL VALIDATION RULES PASSED")
    else:
        print("  SOME VALIDATION RULES FAILED — review RelationshipValidation.json")
    print("=" * 72)


if __name__ == "__main__":
    main()

"""
run_phase_r31_engineering_relationship_engine.py
Runner for Phase R.3.1 — Engineering Drawing Relationship Engine
MODEL_VERSION: 8.9.4

Usage:
    python Version8/Run_PY/run_phase_r31_engineering_relationship_engine.py
    python Version8/Run_PY/run_phase_r31_engineering_relationship_engine.py <run_root>

Prerequisites (same run_root):
    Phase R.2.1D → EngineeringFacts.json
    Phase R.3    → BeamAxis.json, SupportLocations.json, GeometryContexts.json
    Phase R.1    → reinforcement_annotations.json
    Phase VROOT1 → beam_registry.json (+ drawing_path DXF)

Output:
    <output_root>/PhaseR3.1_engineering_relationship_engine/
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
    pkg_dir = src / "PhaseR3.1_engineering_relationship_engine"
    pkg_name = "PhaseR3.1_engineering_relationship_engine"
    alias = "PhaseR31"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import (
        PHASE_R1,
        PHASE_R21D,
        PHASE_R3,
        PHASE_R31,
        PHASE_VROOT1,
        resolve_run_context,
        run_root_from_argv,
    )
    from PhaseR31.phase_r31_orchestrator import PhaseR31Orchestrator

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    facts = ctx.artefact(PHASE_R21D, "EngineeringFacts.json")
    beam_axis = ctx.artefact(PHASE_R3, "BeamAxis.json")
    supports = ctx.artefact(PHASE_R3, "SupportLocations.json")
    geo_contexts = ctx.artefact(PHASE_R3, "GeometryContexts.json")
    anns = ctx.artefact(PHASE_R1, "reinforcement_annotations.json")
    beam_reg = ctx.artefact(PHASE_VROOT1, "beam_registry.json")
    out_dir = ctx.artefact(PHASE_R31)

    print(f"[R.3.1] engine_root={ctx.engine_root}")
    print(f"[R.3.1] run_root={ctx.run_root}")
    print(f"[R.3.1] facts={facts}")
    print(f"[R.3.1] beam_axis={beam_axis}")
    print(f"[R.3.1] output_dir={out_dir}")

    orchestrator = PhaseR31Orchestrator(
        facts_path=facts,
        beam_axis_path=beam_axis,
        supports_path=supports,
        geo_contexts_path=geo_contexts,
        annotations_path=anns,
        beam_registry_path=beam_reg,
        output_dir=out_dir,
        output_root=ctx.output_root,
        engine_root=ctx.engine_root,
    )
    result = orchestrator.run()

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

    rels_out = out_dir / "EngineeringDrawingRelationships.json"
    if result["validation"].get("all_pass"):
        print("  ALL VALIDATION RULES PASSED")
    else:
        print("  SOME VALIDATION RULES FAILED — review RelationshipValidation.json")
        if rels_out.exists():
            print(f"  [OK] EngineeringDrawingRelationships.json present at {rels_out} — continuing")
            print("=" * 72)
            sys.exit(0)
        print("=" * 72)
        sys.exit(1)

    if not rels_out.exists():
        print("  [FAIL] EngineeringDrawingRelationships.json missing")
        print("=" * 72)
        sys.exit(1)

    print("  [OK] Phase R.3.1 complete — drawing relationships ready for R.4.")
    print("=" * 72)


if __name__ == "__main__":
    main()

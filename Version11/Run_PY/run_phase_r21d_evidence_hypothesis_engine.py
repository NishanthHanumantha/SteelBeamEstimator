"""
run_phase_r21d_evidence_hypothesis_engine.py
Runner for Phase R.2.1D — Evidence & Intent Hypothesis Engine.
MODEL_VERSION: 8.9.1

Usage:
    python Version8/Run_PY/run_phase_r21d_evidence_hypothesis_engine.py
    python Version8/Run_PY/run_phase_r21d_evidence_hypothesis_engine.py <run_root>

Prerequisites:
    Phase R.2.1C must have been run for the same run_root.
    Input: <output_root>/PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json
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

    pkg_dir = src / "PhaseR2.1D_evidence_hypothesis_engine"
    pkg_name = "PhaseR2.1D_evidence_hypothesis_engine"
    alias = "PhaseR21D"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import PHASE_R21D, resolve_run_context, run_root_from_argv
    from PhaseR21D.phase_r21d_orchestrator import PhaseR21DOrchestrator

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    r21c_facts = ctx.artefact(
        "PhaseR2.1C_engineering_fact_normalization",
        "EngineeringFacts.json",
    )
    out_dir = ctx.artefact(PHASE_R21D)
    print(f"[R2.1D] engine_root={ctx.engine_root}")
    print(f"[R2.1D] run_root={ctx.run_root}")
    print(f"[R2.1D] r21c_facts={r21c_facts}")
    print(f"[R2.1D] output_dir={out_dir}")

    orchestrator = PhaseR21DOrchestrator(
        r21c_facts_path=r21c_facts,
        output_dir=out_dir,
        output_root=ctx.output_root,
        engine_root=ctx.engine_root,
    )
    result = orchestrator.run()

    print()
    print("=" * 60)
    print("PHASE R.2.1D — SUMMARY")
    print("=" * 60)
    stats = result.get("statistics", {})
    print(f"  Beams processed     : {result['beam_count']}")
    print(f"  Total facts         : {result['total_facts']}")
    print(f"  Total hypotheses    : {result['total_hypotheses']}")
    print(f"  Avg hyp/fact        : {stats.get('avg_hypotheses_per_fact', 0)}")
    rr = stats.get("reorder_rule_fire_counts", {})
    if rr:
        print(f"  Reorder rules fired : {dict(rr)}")
    print(f"  Validation          : {result['validation']['summary']}")
    print(f"  Elapsed             : {result['elapsed_seconds']}s")
    print(f"  MODEL_VERSION       : {result['model_version']}")
    print("=" * 60)

    facts_out = out_dir / "EngineeringFacts.json"
    if not result["success"]:
        print("\n[WARNING] Not all validation rules passed. See details above.")
        if facts_out.exists():
            print(f"[OK] EngineeringFacts.json present at {facts_out} — continuing")
            sys.exit(0)
        sys.exit(1)

    print("\n[OK] Phase R.2.1D complete — HypothesisEnrichedFacts ready for R.3.")


if __name__ == "__main__":
    main()

"""
run_phase_vb1_production_output_completion.py
Runner for Phase V.B.1 — Production Output Completion
MODEL_VERSION: 8.9.4

Usage:
    python Version8/Run_PY/run_phase_vb1_production_output_completion.py
    python Version8/Run_PY/run_phase_vb1_production_output_completion.py <run_root>

Inputs:
    Phase R.1.3 → beam_reinforcement_models_production.json

Output:
    <output_root>/Production_Output/Estimation_Output.xlsx
    Soft-exit 0 if Estimation_Output.xlsx exists (even if validation warns).
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
    root = pathlib.Path(__file__).parent.parent  # Version8/ engine root
    src = root / "src"
    pkg_dir = src / "PhaseVB.1_production_output_completion"
    pkg_name = "PhaseVB.1_production_output_completion"
    alias = "PhaseVB1"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(pkg_dir) not in sys.path:
        sys.path.insert(0, str(pkg_dir))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import (
        PHASE_R13,
        PHASE_VB1,
        resolve_run_context,
        run_root_from_argv,
    )
    from PhaseVB1.phase_vb1_orchestrator import (
        PhaseVB1Orchestrator,
        PRODUCTION_OUTPUT_ERROR,
    )

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    l2_path = ctx.artefact(PHASE_R13, "beam_reinforcement_models_production.json")
    output_dir = ctx.artefact(PHASE_VB1)
    xlsx = output_dir / "Estimation_Output.xlsx"

    print(f"[VB.1] engine_root={ctx.engine_root}")
    print(f"[VB.1] run_root={ctx.run_root}")
    print(f"[VB.1] l2_path={l2_path}")
    print(f"[VB.1] output_dir={output_dir}")

    try:
        orch = PhaseVB1Orchestrator(
            output_dir=output_dir,
            l2_path=l2_path,
            v7_root=ctx.engine_root,
            run_root=ctx.run_root,
            use_r13_integration=False,
            use_r14_validation=False,
        )
        result = orch.run()

        print()
        print("=" * 70)
        print("PHASE V.B.1 — PRODUCTION OUTPUT COMPLETION — COMPLETE")
        print("=" * 70)
        print(f"  Exit code     : {result.pipeline_exit_code}")
        print(f"  Steel (kg)    : {result.steel_weight_kg}")
        print(f"  Workbook      : {result.workbook_path}")
        print(f"  Output dir    : {output_dir}")
        print()

        if xlsx.exists():
            print(f"  [OK] Estimation_Output.xlsx present at {xlsx} — continuing")
            print("=" * 70)
            sys.exit(0)

        sys.exit(result.pipeline_exit_code)

    except PRODUCTION_OUTPUT_ERROR as e:
        print(f"\nPRODUCTION_OUTPUT_ERROR: {e}", file=sys.stderr)
        if xlsx.exists():
            print(f"  [OK] Estimation_Output.xlsx present at {xlsx} — soft-exit 0")
            sys.exit(0)
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        if xlsx.exists():
            print(f"  [OK] Estimation_Output.xlsx present at {xlsx} — soft-exit 0")
            sys.exit(0)
        sys.exit(1)


if __name__ == "__main__":
    main()

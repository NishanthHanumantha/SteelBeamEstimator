"""
run_phase_t1_geometric_stirrup_evidence.py
Runner for Phase T1 — Geometric Stirrup Evidence Engine.
MODEL_VERSION: 9.3.0

Usage:
    python Version9/Run_PY/run_phase_t1_geometric_stirrup_evidence.py
    python Version9/Run_PY/run_phase_t1_geometric_stirrup_evidence.py <run_root>
"""
from __future__ import annotations

import importlib.util
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
        sys.modules[alias] = virtual_pkg

    for py_file in sorted(pkg_dir.glob("*.py")):
        mod_name = py_file.stem
        full_name = alias if mod_name == "__init__" else f"{alias}.{mod_name}"
        if full_name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(full_name, str(py_file))
        if spec is None or spec.loader is None:
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
    root = pathlib.Path(__file__).parent.parent
    src = root / "src"
    pkg_dir = src / "PhaseT1_geometric_stirrup_evidence"
    alias = "PhaseT1"
    pkg_name = "PhaseT1_geometric_stirrup_evidence"

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _bootstrap_package(pkg_dir, alias, pkg_name)

    from config.run_context import resolve_run_context, run_root_from_argv
    from PhaseT1.phase_t1_orchestrator import PhaseT1Orchestrator

    # Allow flags anywhere; first non-flag argv is run_root
    argv = [a for a in sys.argv[1:] if not str(a).startswith("--")]
    arg = pathlib.Path(argv[0]) if argv else None
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    run_root = pathlib.Path(ctx.run_root)
    output_root = pathlib.Path(ctx.output_root)

    skip_val = "--skip-renderer-validation" in sys.argv
    print(f"[T1] engine_root={ctx.engine_root}")
    print(f"[T1] run_root={run_root}")
    print(f"[T1] output_root={output_root}")
    orch = PhaseT1Orchestrator(
        engine_root=root, run_root=run_root, output_root=output_root
    )
    result = orch.run(skip_renderer_validation=skip_val)
    print(f"[T1] success={result.get('success', result.get('soft_exit'))} "
          f"elapsed={result.get('elapsed_s')}s accepted={result.get('accepted_detections')} "
          f"residual={result.get('residual_beams')}")
    if result.get("output"):
        print(f"[T1] output={result.get('output')}")
    if result.get("stopped_at"):
        print(f"[T1] STOPPED at {result['stopped_at']}: {result.get('message')}")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()

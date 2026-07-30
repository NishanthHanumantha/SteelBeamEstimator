#!/usr/bin/env python3
"""
run_phase_qa2_multi_drawing_benchmark.py
Phase QA.2 — Multi-Drawing Accuracy & Error Benchmarking Framework
MODEL_VERSION: 8.9.0

Usage (from Version8/):

  # Full run — discover Test_Input, run production pipeline per set, compare
  python Run_PY/run_phase_qa2_multi_drawing_benchmark.py

  # Compare only (reuse existing Model Excel / prior QA2 web_runs)
  python Run_PY/run_phase_qa2_multi_drawing_benchmark.py --skip-pipeline

  # Custom Test_Input root
  python Run_PY/run_phase_qa2_multi_drawing_benchmark.py --test-input ..\\Test_Input

Does NOT modify engineering logic, EngineeringBars, or Excel generation.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import types
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V8 = _RUNNER_DIR.parent
_PKG_DIR = _V8 / "src" / "PhaseQA.2_multi_drawing_benchmark"
_PKG_ALIAS = "PhaseQA2"

_SUBMODULES = [
    "__init__",
    "drawing_set_discoverer",
    "pipeline_runner",
    "workbook_adapter",
    "comparison_engine",
    "compiled_report",
    "json_exporter",
    "excel_exporter",
    "phase_qa2_orchestrator",
]


def _bootstrap() -> None:
    """Load dotted package PhaseQA.2_* as PhaseQA2 with flat sibling imports."""
    os.chdir(_V8)
    r14 = str(_V8 / "src" / "PhaseR1_4_production_accuracy_benchmark")
    for p in (r14, str(_V8)):
        if p not in sys.path:
            sys.path.insert(0, p)

    pkg = types.ModuleType(_PKG_ALIAS)
    pkg.__path__ = [str(_PKG_DIR)]
    pkg.__package__ = _PKG_ALIAS
    sys.modules[_PKG_ALIAS] = pkg

    loaded = {}
    for sub in _SUBMODULES:
        full = f"{_PKG_ALIAS}.{sub}"
        spec = importlib.util.spec_from_file_location(full, _PKG_DIR / f"{sub}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = _PKG_ALIAS
        sys.modules[full] = mod
        loaded[sub] = (spec, mod)
        if sub != "__init__":
            setattr(pkg, sub, mod)
            # Flat alias so `from comparison_engine import X` works
            sys.modules[sub] = mod

    for sub in _SUBMODULES:
        spec, mod = loaded[sub]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        if sub == "__init__":
            for attr, val in vars(mod).items():
                if not attr.startswith("__"):
                    setattr(pkg, attr, val)
        else:
            # Refresh flat alias after exec
            sys.modules[sub] = mod
            setattr(pkg, sub, mod)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase QA.2 — Multi-Drawing Accuracy & Error Benchmarking Framework"
    )
    p.add_argument(
        "--test-input",
        type=Path,
        default=None,
        help="Root folder containing Drawing Sets (default: <repo>/Test_Input)",
    )
    p.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip production pipeline; compare using existing Model Excel if found",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        _bootstrap()
    except Exception as exc:
        print(f"[ERROR] Failed to load Phase QA.2 package: {exc}", file=sys.stderr)
        return 1

    orch_mod = sys.modules[f"{_PKG_ALIAS}.phase_qa2_orchestrator"]
    Orchestrator = orch_mod.PhaseQA2Orchestrator

    orch = Orchestrator(
        v8_root=_V8,
        test_input=args.test_input,
        skip_pipeline=args.skip_pipeline,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"\n[ERROR] Phase QA.2 failed:\n  {exc}\n", file=sys.stderr)
        return 1

    status = result.get("status")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

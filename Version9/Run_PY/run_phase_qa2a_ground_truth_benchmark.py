#!/usr/bin/env python3
"""
run_phase_qa2a_ground_truth_benchmark.py
Phase QA.2A — Ground Truth Benchmark Comparison Engine
MODEL_VERSION: 9.2.0  (Version9 + DIMENSION discovery + M.2 ACCEPTABLE_EXTRA)

For every Drawing Set under Test_Input:
  1. Run the Version9 production pipeline → Model Estimation_Output.xlsx
  2. Load Estimator Excel (ground truth)
  3. Normalize both → semantic engineering comparison
  4. Emit JSON + GroundTruth_Benchmark_Report.xlsx

Usage (from Version9/):

  python Run_PY/run_phase_qa2a_ground_truth_benchmark.py

  python Run_PY/run_phase_qa2a_ground_truth_benchmark.py --reuse-existing-model

Does NOT modify engineering logic, EngineeringBars, or workbook generation.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import types
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V9 = _RUNNER_DIR.parent
_V8 = _V9  # orchestrator param name retained; engine root is Version9
_PKG_DIR = _V9 / "src" / "PhaseQA.2A_ground_truth_benchmark"
_PKG_ALIAS = "PhaseQA2A"

_SUBMODULES = [
    "__init__",
    "gt_models",
    "workbook_normalizer",
    "beam_matcher",
    "bar_matcher",
    "metrics_engine",
    "error_classifier",
    "report_compiler",
    "json_exporter",
    "excel_exporter",
    "phase_qa2a_orchestrator",
]


def _bootstrap() -> None:
    os.chdir(_V9)
    r14 = str(_V9 / "src" / "PhaseR1_4_production_accuracy_benchmark")
    for p in (r14, str(_V9)):
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
            sys.modules[sub] = mod

    for sub in _SUBMODULES:
        spec, mod = loaded[sub]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        if sub == "__init__":
            for attr, val in vars(mod).items():
                if not attr.startswith("__"):
                    setattr(pkg, attr, val)
        else:
            sys.modules[sub] = mod
            setattr(pkg, sub, mod)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase QA.2A — Ground Truth Benchmark Comparison Engine"
    )
    p.add_argument("--test-input", type=Path, default=None)
    p.add_argument(
        "--reuse-existing-model",
        action="store_true",
        help="Skip pipeline; reuse Model Excel from prior qa2/qa2a web_runs",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        _bootstrap()
    except Exception as exc:
        print(f"[ERROR] Failed to load Phase QA.2A: {exc}", file=sys.stderr)
        return 1

    Orchestrator = sys.modules[f"{_PKG_ALIAS}.phase_qa2a_orchestrator"].PhaseQA2AOrchestrator
    orch = Orchestrator(
        v8_root=_V9,
        test_input=args.test_input,
        reuse_existing_model=args.reuse_existing_model,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"\n[ERROR] Phase QA.2A failed:\n  {exc}\n", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

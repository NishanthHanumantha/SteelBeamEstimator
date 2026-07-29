#!/usr/bin/env python3
"""
run_phase_r14_production_accuracy_benchmark.py
Phase R.1.4 — Production Accuracy Benchmark & Validation Engine
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V8 = _RUNNER_DIR.parent
_SRC = _V8 / "src" / "PhaseR1_4_production_accuracy_benchmark"

for _p in [str(_SRC), str(_V8)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V8)

from phase_r14_orchestrator import PhaseR14Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseR14Orchestrator().run()
    print("\n  PHASE R.1.4 PRODUCTION ACCURACY BENCHMARK")
    print(f"  Status         : {result.get('status')}")
    print(f"  Validation     : {result.get('validation', {}).get('passed')}/"
          f"{result.get('validation', {}).get('total')}")
    kpis = result.get("kpis", {}).get("scorecard", {})
    print(f"  Overall KPI    : {kpis.get('overall_pct')}% ({kpis.get('band')})")
    print(f"  Recommendation : {result.get('recommendation')}")
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

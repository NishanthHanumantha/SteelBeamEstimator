#!/usr/bin/env python3
"""
run_phase_r161_estimator_stirrup_computation.py
Phase R.1.6.1 — Estimator Stirrup Computation Engine
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V8 = _RUNNER_DIR.parent
_SRC = _V8 / "src" / "PhaseR1_6_1_estimator_stirrup_computation"

for _p in [str(_SRC), str(_V8)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V8)

from phase_r161_orchestrator import PhaseR161Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseR161Orchestrator().run()
    print("\n  PHASE R.1.6.1 ESTIMATOR STIRRUP COMPUTATION")
    print(f"  Status         : {result.get('status')}")
    print(f"  Validation     : {result.get('validation', {}).get('passed')}/"
          f"{result.get('validation', {}).get('total')}")
    print(f"  Computations   : {len(result.get('computations') or [])}")
    print(f"  Recommendation : {result.get('recommendation')}")
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

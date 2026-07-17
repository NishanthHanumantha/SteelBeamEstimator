#!/usr/bin/env python3
"""
run_phase_vtest32_estimator_comparison_engine.py
Phase V.TEST.3.2 — Benchmark Set 3 Estimator Output Comparison Engine
MODEL_VERSION: 8.1.2

READ-ONLY engineering audit. No production code modified.
"""
from __future__ import annotations

from pathlib import Path
import os
import sys

_RUNNER_DIR = Path(__file__).resolve().parent
_V7         = _RUNNER_DIR.parent
_VTEST_SRC  = _V7 / "src/PhaseVTEST3_2_estimator_comparison_engine"

for _p in [str(_VTEST_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from phase_vtest32_orchestrator import PhaseVTEST32Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseVTEST32Orchestrator().run()
    return 0 if result.validation.get("overall_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

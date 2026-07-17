#!/usr/bin/env python3
"""
run_phase_r11a_annotation_coverage.py
Phase R.1.1A — Beam Detail Association & Annotation Coverage Recovery Engine
MODEL_VERSION: 8.2.0

Usage:
    python Version7/Run_PY/run_phase_r11a_annotation_coverage.py
    python Version7/Run_PY/run_phase_r11a_annotation_coverage.py Set_3
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7 = _RUNNER_DIR.parent
_R11A_SRC = _V7 / "src/PhaseR1_1A_annotation_coverage"

for _p in [str(_R11A_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from phase_r11a_orchestrator import PhaseR11AOrchestrator  # noqa: E402


def main() -> int:
    bench_filter = sys.argv[1] if len(sys.argv) > 1 else None
    result = PhaseR11AOrchestrator().run(benchmark_filter=bench_filter)
    return 0 if result.get("validation", {}).get("overall_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

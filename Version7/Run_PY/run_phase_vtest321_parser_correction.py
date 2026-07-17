#!/usr/bin/env python3
"""
run_phase_vtest321_parser_correction.py
Phase V.TEST.3.2.1 — Estimator Workbook Parser Correction
MODEL_VERSION: 8.1.3
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7 = _RUNNER_DIR.parent
_VTEST_SRC = _V7 / "src/PhaseVTEST3_2_estimator_comparison_engine"

for _p in [str(_VTEST_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from phase_vtest321_orchestrator import PhaseVTEST321Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseVTEST321Orchestrator().run()
    return 0 if result.validation.get("overall_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_r12a_geometry_accuracy.py
Phase R.1.2A — Geometry Accuracy & Span Propagation Engine
MODEL_VERSION: 8.3.0

Usage:
    python Version8/Run_PY/run_phase_r12a_geometry_accuracy.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7 = _RUNNER_DIR.parent
_SRC = _V7 / "src/PhaseR1_2A_geometry_accuracy"

for _p in [str(_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from phase_r12a_orchestrator import PhaseR12AOrchestrator  # noqa: E402


def main() -> int:
    result = PhaseR12AOrchestrator().run()
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

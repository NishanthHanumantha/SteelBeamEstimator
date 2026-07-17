#!/usr/bin/env python3
"""
run_phase_vtest33_propagation_trace.py
Phase V.TEST.3.3 — Reinforcement Propagation Trace & Root Cause Engine
MODEL_VERSION: 8.1.4
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7 = _RUNNER_DIR.parent
_VTEST_SRC = _V7 / "src/PhaseVTEST3_3_propagation_trace"

for _p in [str(_VTEST_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from phase_vtest33_orchestrator import PhaseVTEST33Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseVTEST33Orchestrator().run()
    return 0 if result.validation.get("overall_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_r12d_reinforcement_detailing.py
Phase R.1.2D — Reinforcement Detailing Interpretation Engine
MODEL_VERSION: 8.4.0
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7 = _RUNNER_DIR.parent
_SRC = _V7 / "src/PhaseR1_2D_reinforcement_detailing"

for _p in [str(_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from phase_r12d_orchestrator import PhaseR12DOrchestrator  # noqa: E402


def main() -> int:
    result = PhaseR12DOrchestrator().run()
    print(f"\n  PHASE R.1.2D RESULT")
    print(f"  Status         : {result.get('status')}")
    print(f"  Validation     : {result.get('validation', {}).get('passed')}/"
          f"{result.get('validation', {}).get('total')}")
    print(f"  Recommendation : {result.get('recommendation')}")
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_r15_engineering_error_intelligence.py
Phase R.1.5 — Engineering Error Intelligence Engine
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V8 = _RUNNER_DIR.parent
_SRC = _V8 / "src" / "PhaseR1_5_engineering_error_intelligence"

for _p in [str(_SRC), str(_V8)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V8)

from phase_r15_orchestrator import PhaseR15Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseR15Orchestrator().run()
    print("\n  PHASE R.1.5 ENGINEERING ERROR INTELLIGENCE")
    print(f"  Status         : {result.get('status')}")
    print(f"  Validation     : {result.get('validation', {}).get('passed')}/"
          f"{result.get('validation', {}).get('total')}")
    print(f"  Issues         : {len(result.get('issues') or [])}")
    print(f"  Recommendation : {result.get('recommendation')}")
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

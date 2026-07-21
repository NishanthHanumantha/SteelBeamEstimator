#!/usr/bin/env python3
"""
run_phase_r162_stirrup_coverage_validation.py
Phase R.1.6.2 — RULE-012 Mandatory Stirrup Coverage Validation
MODEL_VERSION: 8.8.2
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V8 = _RUNNER_DIR.parent
_SRC = _V8 / "src" / "PhaseR1_6_engineering_rule_synthesis"

for _p in [str(_SRC), str(_V8)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V8)

from phase_r162_orchestrator import PhaseR162Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseR162Orchestrator().run()
    print("\n  PHASE R.1.6.2 STIRRUP COVERAGE VALIDATION")
    print(f"  Status         : {result.get('status')}")
    print(f"  Coverage %     : {(result.get('metrics') or {}).get('coverage_pct')}")
    print(f"  Missing        : {result.get('missing_count')}")
    print(f"  Validation     : {result.get('validation', {}).get('passed')}/"
          f"{result.get('validation', {}).get('total')}")
    print(f"  Recommendation : {result.get('recommendation')}")
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

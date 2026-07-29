#!/usr/bin/env python3
"""
run_phase_r163_annotation_discovery_analysis.py
Phase R.1.6.3 — Annotation Discovery Analysis & Engineering Review
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V8 = _RUNNER_DIR.parent
_SRC = _V8 / "src" / "PhaseR1_6_3_annotation_discovery_analysis"

for _p in [str(_SRC), str(_V8)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V8)

from phase_r163_orchestrator import PhaseR163Orchestrator  # noqa: E402


def main() -> int:
    result = PhaseR163Orchestrator().run()
    print("\n  PHASE R.1.6.3 ANNOTATION DISCOVERY ANALYSIS")
    print(f"  Status         : {result.get('status')}")
    print(f"  Coverage %     : {(result.get('statistics') or {}).get('coverage_pct')}")
    print(f"  Pattern        : {result.get('pattern_conclusion')}")
    print(f"  Validation     : {result.get('validation', {}).get('passed')}/"
          f"{result.get('validation', {}).get('total')}")
    print(f"  Recommendation : {result.get('recommendation')}")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

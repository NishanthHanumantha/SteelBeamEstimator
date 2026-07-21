#!/usr/bin/env python3
"""
run_phase_r13_reinforcement_piece_generation.py
Phase R.1.3 — Reinforcement Piece Generation Engine
MODEL_VERSION: 8.5.0
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7 = _RUNNER_DIR.parent
_SRC = _V7 / "src/PhaseR1_3_reinforcement_piece_generation"

for _p in [str(_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from phase_r13_piece_orchestrator import PhaseR13PieceOrchestrator  # noqa: E402


def main() -> int:
    result = PhaseR13PieceOrchestrator().run()
    print(f"\n  PHASE R.1.3 PIECE GENERATION RESULT")
    print(f"  Status         : {result.get('status')}")
    print(f"  Validation     : {result.get('validation', {}).get('passed')}/"
          f"{result.get('validation', {}).get('total')}")
    print(f"  Recommendation : {result.get('recommendation')}")
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_r11b_production_integration.py
Phase R.1.1B — Production Integration of Engineering Interpretation
MODEL_VERSION: 8.2.1

Usage:
    python Version8/Run_PY/run_phase_r11b_production_integration.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7 = _RUNNER_DIR.parent
_R11B_SRC = _V7 / "src/PhaseR1_1B_production_integration"

for _p in [str(_R11B_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)

from production_integration_orchestrator import ProductionIntegrationOrchestrator  # noqa: E402


def main() -> int:
    result = ProductionIntegrationOrchestrator().run()
    return 0 if result.get("status") in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

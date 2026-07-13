"""Runner for Phase L.1 — Accuracy Sprint 1: Estimator Gap Closure."""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: set cwd to Version6 root and inject sys.path
import _bootstrap  # noqa: F401

PHASE_DIR = Path(__file__).resolve().parents[1] / "src" / "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure"
if str(PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE_DIR))

from accuracy_sprint_engine import AccuracySprintEngine  # noqa: E402

if __name__ == "__main__":
    engine = AccuracySprintEngine(Path.cwd())
    result = engine.run()
    sys.exit(0 if (result.get("validation") or {}).get("status") == "PASS" else 1)

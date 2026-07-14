"""
Run Phase V.A.1.1 — End-to-End Validation Recompute (Benchmark Set 1)
MODEL_VERSION: 6.6.3

Entry point for the recompute validation phase.
Adds the package to sys.path and delegates to the orchestrator.
"""
from __future__ import annotations

import pathlib
import sys

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = pathlib.Path(__file__).resolve().parents[2]   # SteelBeamEstimator/
_PKG  = _ROOT / "Version6/src/PhaseVA.1.1_end_to_end_validation_recompute"

for _p in [str(_PKG)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Run ───────────────────────────────────────────────────────────────────────
from phase_va11_orchestrator import PhaseVA11Orchestrator   # noqa: E402


def main() -> None:
    orchestrator = PhaseVA11Orchestrator()
    result = orchestrator.run()
    sys.exit(0 if result.overall_passed else 1)


if __name__ == "__main__":
    main()

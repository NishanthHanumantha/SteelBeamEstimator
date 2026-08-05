#!/usr/bin/env python3
"""
run_phase_qa2b0_pipeline_integration.py
Phase QA.2B.0 — End-to-End Benchmark Pipeline Integration
MODEL_VERSION: 9.6.0

Connects latest engineering / render / crop / ownership outputs to the
benchmark spine. Execution integrity only — no accuracy optimisation.

Usage (from Version9/):
  python Run_PY/run_phase_qa2b0_pipeline_integration.py
  python Run_PY/run_phase_qa2b0_pipeline_integration.py --skip-benchmark
  python Run_PY/run_phase_qa2b0_pipeline_integration.py --force-track1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_V9 = Path(__file__).resolve().parents[1]
_SRC = _V9 / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_V9) not in sys.path:
    sys.path.insert(0, str(_V9))


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase QA.2B.0 pipeline integration")
    p.add_argument(
        "--force-track1",
        action="store_true",
        help="Re-run Track1 visual stages even if artefacts exist",
    )
    p.add_argument(
        "--skip-benchmark",
        action="store_true",
        help="Skip QA.2A reuse execution (integration + validation only)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA2B0_pipeline_integration.phase_qa2b0_orchestrator import (
        PhaseQA2B0Orchestrator,
    )

    orch = PhaseQA2B0Orchestrator(engine_root=_V9)
    try:
        result = orch.run(
            force_track1=args.force_track1,
            run_benchmark=not args.skip_benchmark,
        )
    except Exception as exc:
        print(f"[ERROR] QA.2B.0 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[QA.2B.0] success={result.get('success')}")
    print(f"[QA.2B.0] validation={result.get('pipeline_validation')}")
    print(f"[QA.2B.0] qa={result.get('pipeline_integration_qa')}")
    print(f"[QA.2B.0] summary={result.get('execution_summary')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

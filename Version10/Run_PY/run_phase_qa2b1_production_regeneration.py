#!/usr/bin/env python3
"""
run_phase_qa2b1_production_regeneration.py
Phase QA.2B.1 — Production Output Regeneration & Ground Truth Re-Benchmark
MODEL_VERSION: 9.6.1

Usage (from Version9/):
  python Run_PY/run_phase_qa2b1_production_regeneration.py
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
    p = argparse.ArgumentParser(description="Phase QA.2B.1 production regeneration")
    p.add_argument("--test-input", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA2B1_production_regeneration.phase_qa2b1_orchestrator import (
        PhaseQA2B1Orchestrator,
    )

    orch = PhaseQA2B1Orchestrator(engine_root=_V9, test_input=args.test_input)
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] QA.2B.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[QA.2B.1] success={result.get('success')}")
    print(f"[QA.2B.1] output={result.get('output_root')}")
    print(f"[QA.2B.1] comparison={result.get('regeneration_comparison')}")
    print(f"[QA.2B.1] qa={result.get('production_regeneration_qa')}")
    print(f"[QA.2B.1] benchmark_xlsx={result.get('ground_truth_xlsx')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

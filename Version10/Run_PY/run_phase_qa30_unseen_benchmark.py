#!/usr/bin/env python3
"""
run_phase_qa30_unseen_benchmark.py
Phase QA.3.0 — Unseen Drawing Benchmark (First Generalization Validation)
MODEL_VERSION: 10.0.0

Usage (from Version10/):
  python Run_PY/run_phase_qa30_unseen_benchmark.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_V10 = Path(__file__).resolve().parents[1]
_SRC = _V10 / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_V10) not in sys.path:
    sys.path.insert(0, str(_V10))


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase QA.3.0 unseen drawing benchmark")
    p.add_argument("--test-input", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA30_unseen_benchmark.phase_qa30_orchestrator import (
        PhaseQA30Orchestrator,
    )

    orch = PhaseQA30Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        test_input=args.test_input,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] QA.3.0 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[QA.3.0] success={result.get('success')}")
    print(f"[QA.3.0] output={result.get('output_root')}")
    print(f"[QA.3.0] pass={result.get('validation_overall_pass')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

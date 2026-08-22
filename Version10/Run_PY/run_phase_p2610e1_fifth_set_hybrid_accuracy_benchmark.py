#!/usr/bin/env python3
"""
run_phase_p2610e1_fifth_set_hybrid_accuracy_benchmark.py
Phase P2.6.10-E.1 — Fifth Set Hybrid Architecture Accuracy Benchmark
MODEL_VERSION: 10.11.22

Default OFFLINE_REPLAY. Does not call Claude. Does not mutate production.
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


def main() -> int:
    p = argparse.ArgumentParser(description="P2.6.10-E.1 Fifth Set hybrid accuracy benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", default="OFFLINE_REPLAY")
    args = p.parse_args()

    print("P2.6.10-E.1 FIFTH SET HYBRID ARCHITECTURE ACCURACY BENCHMARK")
    print("OFFLINE_REPLAY DEFAULT / FAIL CLOSED / NO CLAUDE / NO PRODUCTION MUTATION")
    print("LIVE_CLAUDE_CALL = false")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")

    from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.phase_p2610e1_orchestrator import (
        run_phase_p2610e1,
    )

    try:
        r1 = run_phase_p2610e1(
            version10_root=_V10,
            output_root=args.output,
            mode=args.mode,
            run_tests=not args.skip_unit_tests,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-E.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-E.1] status={r1.get('pass_fail')} decision={r1.get('decision')}")
    print(f"[P2.6.10-E.1] output={r1.get('output_root')}")
    print(f"[P2.6.10-E.1] pdf={r1.get('pdf_path')}")
    return 0 if r1.get("pass_fail") != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())

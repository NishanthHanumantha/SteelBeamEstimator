#!/usr/bin/env python3
"""
run_phase_p2610e2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.py
Phase P2.6.10-E.2 — Fifth Set Full-Population Live Vision Hybrid Accuracy Benchmark
MODEL_VERSION: 10.11.23

Default OFFLINE_VALIDATION (no Claude).
Live calls require --mode LIVE_BENCHMARK.
Does not mutate production. Does not overwrite prior C/D/E.1 artefacts.
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
    p = argparse.ArgumentParser(description="P2.6.10-E.2 Fifth Set live Vision hybrid accuracy benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", default="OFFLINE_VALIDATION", help="OFFLINE_VALIDATION (default) or LIVE_BENCHMARK")
    args = p.parse_args()

    print("P2.6.10-E.2 FIFTH SET FULL-POPULATION LIVE VISION HYBRID ACCURACY BENCHMARK")
    print("DEFAULT OFFLINE_VALIDATION / FAIL CLOSED / NO PRODUCTION MUTATION")
    print(f"MODE = {args.mode}")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")

    from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.phase_p2610e2_orchestrator import (
        run_phase_p2610e2,
    )

    try:
        r1 = run_phase_p2610e2(
            version10_root=_V10,
            output_root=args.output,
            mode=args.mode,
            run_tests=not args.skip_unit_tests,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-E.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-E.2] status={r1.get('pass_fail')} decision={r1.get('decision')} live={r1.get('live_completion')}")
    print(f"[P2.6.10-E.2] output={r1.get('output_root')}")
    print(f"[P2.6.10-E.2] pdf={r1.get('pdf_path')}")
    return 0 if r1.get("pass_fail") != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_p261_stratified_vision_candidate_recovery.py
Phase P2.6.1 — Stratified Vision Candidate Recovery Benchmark
MODEL_VERSION: 10.11.1

Shadow / research only. Does not mutate production.

Usage (from Version10/):
  python Run_PY/run_phase_p261_stratified_vision_candidate_recovery.py
  python Run_PY/run_phase_p261_stratified_vision_candidate_recovery.py --mode CACHE_ONLY
  python Run_PY/run_phase_p261_stratified_vision_candidate_recovery.py --mode LIVE_API
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
    p = argparse.ArgumentParser(description="P2.6.1 Stratified Vision Candidate Recovery Benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["LIVE_API", "CACHE_ONLY"], default="LIVE_API")
    p.add_argument("--budget", type=int, default=90)
    p.add_argument("--seed", type=int, default=2611101)
    args = p.parse_args()

    print("SCOPE = STRATIFIED_SAMPLE_FOURTH_FIFTH_SIXTH")
    print("MODE = BENCHMARK_SHADOW")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = SHADOW_CANDIDATE_RECOVERY")
    print("PRODUCTION_WRITE = false")
    print("P2.6.1 does NOT authorize production promotion.")
    print("This is a stratified sample, not a full drawing-set benchmark.")
    print(f"VISION_MODE = {args.mode}")
    print(f"MAX_LIVE_CALLS = {args.budget}")

    from PhaseP261_stratified_vision_candidate_recovery.phase_p261_orchestrator import (
        run_phase_p261,
    )

    try:
        r1 = run_phase_p261(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
            max_live_calls=args.budget,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.1] status={r1.get('pass_fail')}")
    print(f"[P2.6.1] decision={r1.get('decision')}")
    print(f"[P2.6.1] strength={r1.get('strength')}")
    m = r1.get("metrics") or {}
    print(
        f"[P2.6.1] beams={m.get('BEAMS_INSPECTED')} live={m.get('live_calls')} "
        f"cands={m.get('VISION_CANDIDATES')} true_recovery={m.get('TRUE_RECOVERIES')}"
    )
    print(
        f"[P2.6.1] recovery_rate={m.get('TRUE_RECOVERY_RATE')} "
        f"precision={m.get('VISION_CANDIDATE_PRECISION')} "
        f"unsupported={m.get('UNSUPPORTED_RATE')} duplicate={m.get('DUPLICATE_RATE')}"
    )
    prod = r1.get("production") or {}
    print(f"[P2.6.1] production_mutations={prod.get('production_mutation_count')}")
    print("[P2.6.1] P2.6.1 does NOT authorize production promotion.")
    print(f"[P2.6.1] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

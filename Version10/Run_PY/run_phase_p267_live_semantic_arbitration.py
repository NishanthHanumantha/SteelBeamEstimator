#!/usr/bin/env python3
"""
run_phase_p267_live_semantic_arbitration.py
Phase P2.6.7 — Live Semantic Arbitration Benchmark & Repeatability Test
MODEL_VERSION: 10.11.7

Default: LIVE_API. Does not mutate production or P2.6.4/P2.6.5/P2.6.6 artefacts.
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
    p = argparse.ArgumentParser(description="P2.6.7 Live Semantic Arbitration Benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument(
        "--mode",
        choices=["LIVE_API", "REPARSE_STORED_LIVE_RAW"],
        default="LIVE_API",
    )
    p.add_argument(
        "--reparse-stored-raw",
        action="store_true",
        help="Re-validate stored live Claude JSON. Does not call the API and is not P2.6.6 replay.",
    )
    args = p.parse_args()
    mode = "REPARSE_STORED_LIVE_RAW" if args.reparse_stored_raw else args.mode

    print("P2.6.7 LIVE SEMANTIC ARBITRATION")
    print("SHADOW / RESEARCH ONLY")
    print("PRODUCTION ROUTING UNCHANGED")
    if mode == "LIVE_API":
        print("LIVE API CALLS ENABLED")
    else:
        print("REPARSE STORED LIVE RAW — NO NEW API CALLS")
    print("TARGET = 29")
    print("REPEAT PASSES = 2")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {mode}")

    from PhaseP267_live_semantic_arbitration.phase_p267_orchestrator import run_phase_p267

    try:
        r1 = run_phase_p267(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.7 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    acc = m.get("accuracy") or {}
    print(f"[P2.6.7] status={r1.get('pass_fail')}")
    print(f"[P2.6.7] decision={r1.get('decision')}")
    print(
        f"[P2.6.7] live_attempts={m.get('total_live_calls')} "
        f"primary_ok={m.get('successful_primary')} repeat_ok={m.get('successful_repeat')}"
    )
    print(f"[P2.6.7] false_DUPLICATE={acc.get('false_DUPLICATE')} false_DISTINCT={acc.get('false_DISTINCT')}")
    print(f"[P2.6.7] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.7] P2.6.7 does NOT authorize production promotion.")
    print(f"[P2.6.7] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

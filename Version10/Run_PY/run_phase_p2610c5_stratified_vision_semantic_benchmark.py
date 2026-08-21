#!/usr/bin/env python3
"""
run_phase_p2610c5_stratified_vision_semantic_benchmark.py
Phase P2.6.10-C.5 — Stratified Vision Semantic Benchmark
MODEL_VERSION: 10.11.18

Default: OFFLINE_VALIDATION (discover, sample, tests; no Claude).
Use --mode LIVE_SHADOW to call Claude for the selected sample only (max 10).
Does not mutate production. Does not rerender DXF. Does not reselect C.1+C.2.
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
    p = argparse.ArgumentParser(description="P2.6.10-C.5 stratified Vision semantic benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_VALIDATION", "LIVE_SHADOW"], default="OFFLINE_VALIDATION")
    args = p.parse_args()

    print("P2.6.10-C.5 STRATIFIED VISION SEMANTIC BENCHMARK")
    print("SHADOW ONLY / FAIL CLOSED / MAX 10 BEAMS / FOURTH SET ONLY")
    print("NO DXF RERENDER / NO RESELECTION / NO PRODUCTION MUTATION")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP2610C5_stratified_vision_semantic_benchmark.phase_p2610c5_orchestrator import run_phase_p2610c5

    try:
        r1 = run_phase_p2610c5(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-C.5 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-C.5] status={r1.get('pass_fail')} decision={r1.get('decision')}")
    print(f"[P2.6.10-C.5] selected={(r1.get('sample') or {}).get('selected_ids')}")
    print(f"[P2.6.10-C.5] live={r1.get('live_claude_call')}")
    print(f"[P2.6.10-C.5] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-C.5] next: MANUAL VERIFICATION OF THE 10-BEAM FINAL VISION BENCHMARK")
    print(f"[P2.6.10-C.5] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

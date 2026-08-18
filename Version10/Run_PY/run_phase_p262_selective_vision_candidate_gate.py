#!/usr/bin/env python3
"""
run_phase_p262_selective_vision_candidate_gate.py
Phase P2.6.2 — Selective Vision Candidate Gate
MODEL_VERSION: 10.11.2

Default: REPLAY_P261_CACHED. Does not mutate production.

Usage (from Version10/):
  python Run_PY/run_phase_p262_selective_vision_candidate_gate.py
  python Run_PY/run_phase_p262_selective_vision_candidate_gate.py --mode REPLAY_P261_CACHED
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
    p = argparse.ArgumentParser(description="P2.6.2 Selective Vision Candidate Gate")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["REPLAY_P261_CACHED", "LIVE_API"], default="REPLAY_P261_CACHED")
    p.add_argument("--live", action="store_true", help="Request optional live mode (still not a full benchmark).")
    args = p.parse_args()
    mode = "LIVE_API" if args.live else args.mode

    print("SCOPE = FROZEN_P261_STRATIFIED_SAMPLE")
    print("MODE = GATE_SHADOW")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print("Gated replay using frozen P2.6.1 Vision responses.")
    print("This is not a new Vision benchmark.")
    print(f"EXECUTION_MODE = {mode}")

    from PhaseP262_selective_vision_candidate_gate.phase_p262_orchestrator import run_phase_p262

    try:
        r1 = run_phase_p262(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.6.2] status={r1.get('pass_fail')}")
    print(f"[P2.6.2] decision={r1.get('decision')}")
    print(
        f"[P2.6.2] call={m.get('CALL_BEAMS')} skip={m.get('SKIP_BEAMS')} hold={m.get('HOLD_BEAMS')} "
        f"reduction={m.get('CALL_REDUCTION')} retention={m.get('RECOVERY_RETENTION_RATE')}"
    )
    print(f"[P2.6.2] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.2] P2.6.2 does NOT authorize production promotion or engineering recompute.")
    print(f"[P2.6.2] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

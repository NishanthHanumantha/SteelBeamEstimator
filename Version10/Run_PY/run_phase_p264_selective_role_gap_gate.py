#!/usr/bin/env python3
"""
run_phase_p264_selective_role_gap_gate.py
Phase P2.6.4 — Selective XOR / Role-Gap Refinement
MODEL_VERSION: 10.11.4

Default: REPLAY_P261_CACHED. Does not mutate production.
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
    p = argparse.ArgumentParser(description="P2.6.4 Selective XOR / Role-Gap Refinement")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["REPLAY_P261_CACHED", "LIVE_API"], default="REPLAY_P261_CACHED")
    args = p.parse_args()

    print("SCOPE = FROZEN_P261_STRATIFIED_SAMPLE")
    print("MODE = GATE_SHADOW")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print("Gated replay using frozen P2.6.1 Vision responses.")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP264_selective_role_gap_gate.phase_p264_orchestrator import run_phase_p264

    try:
        r1 = run_phase_p264(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.4 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.6.4] status={r1.get('pass_fail')}")
    print(f"[P2.6.4] decision={r1.get('decision')}")
    print(
        f"[P2.6.4] call={m.get('CALL_BEAMS')} skip={m.get('SKIP_BEAMS')} hold={m.get('HOLD_BEAMS')} "
        f"reduction={m.get('CALL_REDUCTION')} retention={m.get('RECOVERY_RETENTION_RATE')}"
    )
    print(
        f"[P2.6.4] stirrup={m.get('STIRRUP_GATED_TRUE_RECOVERIES')}/"
        f"{m.get('STIRRUP_BASELINE_TRUE_RECOVERIES')} "
        f"long={m.get('LONGITUDINAL_GATED_TRUE_RECOVERIES')}/"
        f"{m.get('LONGITUDINAL_BASELINE_TRUE_RECOVERIES')}"
    )
    print(f"[P2.6.4] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.4] P2.6.4 does NOT authorize production promotion.")
    print(f"[P2.6.4] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

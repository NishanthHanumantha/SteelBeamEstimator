#!/usr/bin/env python3
"""
run_phase_p263_longitudinal_aware_gate.py
Phase P2.6.3 — Longitudinal-Aware Selective Vision Gate
MODEL_VERSION: 10.11.3

Default: REPLAY_P261_CACHED. Does not mutate production.

Usage (from Version10/):
  python Run_PY/run_phase_p263_longitudinal_aware_gate.py
  python Run_PY/run_phase_p263_longitudinal_aware_gate.py --mode REPLAY_P261_CACHED
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
    p = argparse.ArgumentParser(description="P2.6.3 Longitudinal-Aware Selective Vision Gate")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["REPLAY_P261_CACHED", "LIVE_API"], default="REPLAY_P261_CACHED")
    args = p.parse_args()

    print("SCOPE = FROZEN_P261_STRATIFIED_SAMPLE")
    print("MODE = GATE_SHADOW")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print("Gated replay using frozen P2.6.1 Vision responses.")
    print("This is not a new Vision benchmark.")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP263_longitudinal_aware_gate.phase_p263_orchestrator import run_phase_p263

    try:
        r1 = run_phase_p263(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.3 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.6.3] status={r1.get('pass_fail')}")
    print(f"[P2.6.3] decision={r1.get('decision')}")
    print(
        f"[P2.6.3] call={m.get('CALL_BEAMS')} skip={m.get('SKIP_BEAMS')} hold={m.get('HOLD_BEAMS')} "
        f"reduction={m.get('CALL_REDUCTION')} retention={m.get('RECOVERY_RETENTION_RATE')}"
    )
    print(
        f"[P2.6.3] stirrup={m.get('STIRRUP_GATED_TRUE_RECOVERIES')}/"
        f"{m.get('STIRRUP_BASELINE_TRUE_RECOVERIES')} "
        f"long={m.get('LONGITUDINAL_GATED_TRUE_RECOVERIES')}/"
        f"{m.get('LONGITUDINAL_BASELINE_TRUE_RECOVERIES')}"
    )
    print(f"[P2.6.3] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.3] P2.6.3 does NOT authorize production promotion.")
    print(f"[P2.6.3] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

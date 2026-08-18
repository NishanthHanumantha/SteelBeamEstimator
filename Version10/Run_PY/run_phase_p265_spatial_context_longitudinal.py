#!/usr/bin/env python3
"""
run_phase_p265_spatial_context_longitudinal.py
Phase P2.6.5 — Spatial / Context-Aware Longitudinal Ambiguity Resolution
MODEL_VERSION: 10.11.5

Default: REPLAY_P261_CACHED. Does not mutate production or P2.6.4 routing.
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
    p = argparse.ArgumentParser(description="P2.6.5 Spatial / Context-Aware Longitudinal Ambiguity Resolution")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["REPLAY_P261_CACHED", "LIVE_API"], default="REPLAY_P261_CACHED")
    args = p.parse_args()

    print("SCOPE = FROZEN_P261_STRATIFIED_SAMPLE")
    print("MODE = SHADOW_RESEARCH")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print("Observed routing = P2.6.4 unchanged.")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP265_spatial_context_longitudinal.phase_p265_orchestrator import run_phase_p265

    try:
        r1 = run_phase_p265(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.5 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.6.5] status={r1.get('pass_fail')}")
    print(f"[P2.6.5] decision={r1.get('decision')}")
    print(
        f"[P2.6.5] observed call={m.get('CALL_BEAMS')} skip={m.get('SKIP_BEAMS')} "
        f"ctx_skip={m.get('CONTEXT_SUPPORTS_SKIP')} ctx_call={m.get('CONTEXT_SUPPORTS_CALL')} "
        f"ctx_amb={m.get('CONTEXT_AMBIGUOUS')}"
    )
    print(f"[P2.6.5] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.5] P2.6.5 does NOT authorize production promotion.")
    print(f"[P2.6.5] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_p259_beam_safe_arbitration.py
Phase P2.5.9 — Beam-Safe Arbitration
MODEL_VERSION: 10.8.5

Usage (from Version10/):
  python Run_PY/run_phase_p259_beam_safe_arbitration.py
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
    p = argparse.ArgumentParser(description="P2.5.9 Beam-Safe Arbitration")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("SCOPE = FIFTH_SET_PRIMARY")
    print("MODE = REPLAY_P257_LIVE_RESULTS")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = REPLAY_ONLY")
    print("PRODUCTION_WRITE = false")
    print("P2.5.9 does NOT authorize production promotion.")

    from PhaseP259_beam_safe_arbitration.phase_p259_orchestrator import run_phase_p259

    try:
        r1 = run_phase_p259(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.9 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.9] status={r1.get('pass_fail')}")
    print(f"[P2.5.9] decision={r1.get('decision')}")
    rec = r1.get("recommendation") or {}
    print(f"[P2.5.9] recommended_class={rec.get('class')} proceed_p2510={rec.get('proceed_p2510')}")
    for row in r1.get("strategy_rows") or []:
        print(
            f"[P2.5.9] {row.get('strategy')} acc={row.get('steel_accuracy')} "
            f"d_det={row.get('delta_vs_deterministic')} "
            f"improved={row.get('improved_beams')} worsened={row.get('worsened_beams')}"
        )
    prod = r1.get("production") or {}
    print(f"[P2.5.9] production_mutations={prod.get('production_mutation_count')}")
    print("[P2.5.9] P2.5.9 does NOT authorize production promotion.")
    print(f"[P2.5.9] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

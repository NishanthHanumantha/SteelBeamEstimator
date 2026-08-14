#!/usr/bin/env python3
"""
run_phase_p258_controlled_vision_field_repair.py
Phase P2.5.8 — Controlled Vision Field-Repair & Engineering Recompute
MODEL_VERSION: 10.8.4

Usage (from Version10/):
  python Run_PY/run_phase_p258_controlled_vision_field_repair.py
  python Run_PY/run_phase_p258_controlled_vision_field_repair.py --live
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
    p = argparse.ArgumentParser(description="P2.5.8 Controlled Vision Field-Repair")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--live", action="store_true", help="Fresh Claude inference (not the official experiment)")
    args = p.parse_args()

    print("SCOPE = FIFTH_SET_PRIMARY")
    print("MODE = REPLAY_P257_LIVE_RESULTS" if not args.live else "MODE = LIVE")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = INTERPRETATION_ONLY")
    print("MAX_PROMOTION = CONTROLLED_RECOMPUTE")
    print("PRODUCTION_WRITE = false")

    from PhaseP258_controlled_vision_field_repair.phase_p258_orchestrator import (
        run_phase_p258,
    )

    try:
        r1 = run_phase_p258(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            live=bool(args.live),
        )
        if r1.get("error") and not r1.get("success"):
            print(f"[ERROR] P2.5.8 aborted: {r1.get('error')}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[ERROR] P2.5.8 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    eng = r1.get("engineering") or {}
    vis = r1.get("vision") or {}
    cost = r1.get("cost") or {}
    beam = r1.get("beam_impact") or {}
    prod = r1.get("production") or {}
    print(f"[P2.5.8] status={r1.get('pass_fail')}")
    print(f"[P2.5.8] decision={r1.get('decision')}")
    print(f"[P2.5.8] promoted={vis.get('fields_promoted')} blocked={vis.get('fields_blocked')}")
    print(
        f"[P2.5.8] baseline_acc={eng.get('baseline_accuracy')} "
        f"vision_acc={eng.get('vision_assisted_accuracy')} "
        f"improvement={eng.get('STEEL_ACCURACY_IMPROVEMENT')} "
        f"error_reduction={eng.get('error_reduction_percent')}"
    )
    print(
        f"[P2.5.8] beams improved={beam.get('beams_improved')} "
        f"unchanged={beam.get('beams_unchanged')} "
        f"worsened={beam.get('beams_worsened')}"
    )
    print(f"[P2.5.8] production_mutations={prod.get('production_mutation_count')}")
    print(f"[P2.5.8] claude_calls={cost.get('live_claude_calls')} cost_usd={cost.get('estimated_cost_usd')}")
    print(f"[P2.5.8] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

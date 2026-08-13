#!/usr/bin/env python3
"""
run_phase_p257_unseen_drawing_controlled_vision_validation.py
Phase P2.5.7 — Unseen-Drawing Controlled Vision Validation
MODEL_VERSION: 10.8.3

Usage (from Version10/):
  python Run_PY/run_phase_p257_unseen_drawing_controlled_vision_validation.py
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
    p = argparse.ArgumentParser(description="P2.5.7 Unseen-Drawing Controlled Vision Validation")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("SCOPE = FIFTH_SET_UNSEEN_ONLY")
    print("MODE = SELECTIVE_LIVE_SHADOW")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = SHADOW_OBSERVER")
    print("P2.5.1 = PRODUCTION AUTHORITY")

    from PhaseP257_unseen_drawing_controlled_vision_validation.phase_p257_orchestrator import (
        run_phase_p257,
    )

    try:
        r1 = run_phase_p257(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            live=True,
        )
        if r1.get("error") and not r1.get("success"):
            print(f"[ERROR] P2.5.7 aborted: {r1.get('error')}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[ERROR] P2.5.7 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    c = r1.get("cost") or {}
    print(f"[P2.5.7] success={r1.get('success')}")
    print(f"[P2.5.7] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.7] decision={r1.get('decision')}")
    print(f"[P2.5.7] candidates={r1.get('candidate_count')} eligible={r1.get('eligible_count')}")
    print(
        f"[P2.5.7] TRUE_INCREMENTAL={m.get('TRUE_VISION_INCREMENTAL_VALUE_RATE')} "
        f"combined={m.get('HYPOTHETICAL_COMBINED_ACCURACY')} "
        f"delta={m.get('IMPROVEMENT_DELTA')} "
        f"dangerous={m.get('dangerous_vision_override_rate')}"
    )
    print(f"[P2.5.7] live={c.get('live_claude_calls')} failed={c.get('failed_calls')} cost_usd={c.get('estimated_cost_usd')}")
    print(f"[P2.5.7] production_mutations={m.get('production_mutation_count')}")
    print(f"[P2.5.7] regression={(r1.get('regression') or {}).get('unchanged')}")
    print(f"[P2.5.7] output={r1.get('output_root')}")
    print(f"[P2.5.7] {r1.get('decision')}")
    return 0 if r1.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

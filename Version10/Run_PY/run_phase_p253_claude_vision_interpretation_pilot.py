#!/usr/bin/env python3
"""
run_phase_p253_claude_vision_interpretation_pilot.py
Phase P2.5.3 — Claude Vision Interpretation Pilot
MODEL_VERSION: 10.7.0

Usage (from Version10/):
  python Run_PY/run_phase_p253_claude_vision_interpretation_pilot.py
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
    p = argparse.ArgumentParser(description="P2.5.3 Claude Vision Interpretation Pilot")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--once", action="store_true", help="Run pilot once (skip second pass)")
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = PILOT_ONLY_NO_PRODUCTION_PROMOTION")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = PILOT_ISOLATED")

    from PhaseP253_claude_vision_interpretation_pilot.phase_p253_orchestrator import (
        run_phase_p253,
    )

    try:
        r1 = run_phase_p253(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
        if r1.get("error") and not r1.get("success"):
            print(f"[ERROR] P2.5.3 aborted: {r1.get('error')}", file=sys.stderr)
            return 1
        if args.once:
            r2 = r1
        else:
            # Second pass: verify deterministic pipeline fingerprint; Claude may vary
            r2 = run_phase_p253(
                version10_root=_V10,
                output_root=args.output,
                run_tests=False,
                prior_pipeline_fingerprint=r1.get("pipeline_fingerprint"),
            )
    except Exception as exc:
        print(f"[ERROR] P2.5.3 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.3] success={r1.get('success')}")
    print(f"[P2.5.3] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.3] decision={r1.get('decision')}")
    print(f"[P2.5.3] claude_model={r1.get('claude_model')}")
    m = r1.get("metrics") or {}
    c = m.get("counts") or {}
    print(
        f"[P2.5.3] calls={m.get('CLAUDE_CALL_COUNT')} "
        f"exact={c.get('exact')} partial={c.get('partial')} "
        f"incorrect={c.get('incorrect')} halluc={c.get('hallucination')} "
        f"abstain={c.get('appropriate_abstention')}"
    )
    print(
        f"[P2.5.3] exact_rate={m.get('VISION_EXACT_INTERPRETATION_RATE')} "
        f"halluc_rate={m.get('VISION_HALLUCINATION_RATE')}"
    )
    print(f"[P2.5.3] regression_unchanged={(r1.get('regression') or {}).get('unchanged')}")
    print(
        f"[P2.5.3] pipeline_det="
        f"{(r1.get('determinism') or {}).get('pipeline_determinism_status')} "
        f"run2={(r2.get('determinism') or {}).get('pipeline_determinism_status')}"
    )
    print(f"[P2.5.3] output={r1.get('output_root')}")
    print(f"[P2.5.3] {r1.get('decision')}")
    return 0 if r1.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

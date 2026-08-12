#!/usr/bin/env python3
"""
run_phase_p2521_crop_readability_refinement.py
Phase P2.5.2.1 — Crop Readability Refinement
MODEL_VERSION: 10.6.6

Usage (from Version10/):
  python Run_PY/run_phase_p2521_crop_readability_refinement.py
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
    p = argparse.ArgumentParser(description="P2.5.2.1 Crop Readability Refinement")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = VISUAL_EVIDENCE_REFINEMENT_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = NOT_INCLUDED")

    from PhaseP2521_crop_readability_refinement.phase_p2521_orchestrator import (
        run_phase_p2521,
    )

    try:
        r1 = run_phase_p2521(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
        if not r1.get("success") and r1.get("error"):
            print(f"[ERROR] P2.5.2.1 aborted: {r1.get('error')}", file=sys.stderr)
            return 1
        fp1 = r1.get("fingerprint")
        r2 = run_phase_p2521(
            version10_root=_V10,
            output_root=args.output,
            run_tests=False,
            prior_fingerprint=fp1,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.2.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.2.1] success={r1.get('success') and r2.get('success')}")
    print(f"[P2.5.2.1] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.2.1] decision={r1.get('decision')}")
    print(
        f"[P2.5.2.1] determinism_run1={(r1.get('determinism') or {}).get('determinism_status')} "
        f"run2={(r2.get('determinism') or {}).get('determinism_status')}"
    )
    print(f"[P2.5.2.1] regression_unchanged={(r1.get('regression') or {}).get('unchanged')}")
    c = r1.get("counts") or {}
    print(
        f"[P2.5.2.1] active={c.get('total_active')} "
        f"PASS={c.get('readability_pass')} PARTIAL={c.get('readability_partial')} "
        f"FAIL={c.get('readability_fail')} REVIEW={c.get('readability_review_required')}"
    )
    print(f"[P2.5.2.1] claude_calls={r1.get('claude_calls')}")
    print(f"[P2.5.2.1] output={r1.get('output_root')}")
    print(f"[P2.5.2.1] manual_review={r1.get('manual_review')}")
    return 0 if r1.get("success") and r2.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

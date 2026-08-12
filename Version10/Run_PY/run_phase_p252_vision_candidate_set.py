#!/usr/bin/env python3
"""
run_phase_p252_vision_candidate_set.py
Phase P2.5.2 — Vision Candidate Set + Visual Evidence Package
MODEL_VERSION: 10.6.5

Usage (from Version10/):
  python Run_PY/run_phase_p252_vision_candidate_set.py
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
    p = argparse.ArgumentParser(description="P2.5.2 Vision Candidate Set")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = CANDIDATE_EVIDENCE_PACKAGING_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = NOT_INCLUDED")

    from PhaseP252_vision_candidate_set.phase_p252_orchestrator import run_phase_p252

    try:
        r1 = run_phase_p252(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
        r2 = run_phase_p252(
            version10_root=_V10,
            output_root=args.output,
            run_tests=False,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.2] success={r1.get('success') and r2.get('success')}")
    print(f"[P2.5.2] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.2] decision={r1.get('decision')}")
    print(
        f"[P2.5.2] determinism_run1={(r1.get('determinism') or {}).get('determinism_status')} "
        f"run2={(r2.get('determinism') or {}).get('determinism_status')}"
    )
    print(f"[P2.5.2] regression_unchanged={(r1.get('regression') or {}).get('unchanged')}")
    m = r1.get("metrics") or {}
    print(
        f"[P2.5.2] candidates={m.get('VISION_CANDIDATE_COUNT')} "
        f"deferred={m.get('DEFERRED_COUNT')} excluded={m.get('EXCLUDED_COUNT')} "
        f"ocr={m.get('OCR_CORRUPTED_COUNT')}"
    )
    print(f"[P2.5.2] claude_calls={r1.get('claude_calls')}")
    print(f"[P2.5.2] output={r1.get('output_root')}")
    return 0 if r1.get("success") and r2.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

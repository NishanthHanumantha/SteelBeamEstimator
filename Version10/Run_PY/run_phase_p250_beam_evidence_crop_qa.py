#!/usr/bin/env python3
"""
run_phase_p250_beam_evidence_crop_qa.py
Phase P2.5.0 — Beam Evidence Rendering & Crop QA
MODEL_VERSION: 10.6.0

SCOPE = FOURTH_SET_ONLY
MODE = DIAGNOSTIC_ONLY
ENGINEERING_CHANGES = NONE

No Claude. No QuantityIntent. No engineering mutations.

Usage (from Version10/):
  python Run_PY/run_phase_p250_beam_evidence_crop_qa.py
  python Run_PY/run_phase_p250_beam_evidence_crop_qa.py --max-beams 5
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


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase P2.5.0 Beam Evidence Rendering & Crop QA (diagnostic only)"
    )
    p.add_argument("--output", type=Path, default=None)
    p.add_argument(
        "--max-beams",
        type=int,
        default=None,
        help="Optional cap for smoke tests (default: all available Fourth Set beams)",
    )
    p.add_argument(
        "--skip-unit-tests",
        action="store_true",
        help="Skip focused unit tests before Fourth Set processing",
    )
    return p.parse_args()


def main() -> int:
    args = _parse()
    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = DIAGNOSTIC_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = NOT_INCLUDED")

    from PhaseP250_beam_evidence_crop_qa.phase_p250_orchestrator import run_phase_p250

    try:
        result = run_phase_p250(
            version10_root=_V10,
            output_root=args.output,
            max_beams=args.max_beams,
            run_tests=not args.skip_unit_tests,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.0 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = result.get("metrics") or {}
    d = result.get("determinism") or {}
    r = result.get("regression") or {}
    print(f"[P2.5.0] success={result.get('success')}")
    print(f"[P2.5.0] model_version={(result.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.0] beams={m.get('beams_processed')}")
    print(f"[P2.5.0] renders_ok={m.get('successful_renders')}")
    print(f"[P2.5.0] crop_qa_pass_pct={m.get('crop_qa_pass_pct')}")
    print(f"[P2.5.0] beam_presence_pct={m.get('beam_presence_pct')}")
    print(f"[P2.5.0] reinf_cov_pct={m.get('reinforcement_evidence_coverage_pct')}")
    print(f"[P2.5.0] ann_cov_pct={m.get('annotation_evidence_coverage_pct')}")
    print(f"[P2.5.0] leader_cov_pct={m.get('leader_evidence_coverage_pct')}")
    print(f"[P2.5.0] determinism={d.get('determinism_status')}")
    print(f"[P2.5.0] regression_unchanged={r.get('unchanged')}")
    print(f"[P2.5.0] output={result.get('output_root')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

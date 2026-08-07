#!/usr/bin/env python3
"""
run_phase_qa34_ownership_competition_validation.py
Phase QA.3.4 — Ownership Competition Validation Engine
MODEL_VERSION: 10.0.4

Usage (from Version10/):
  python Run_PY/run_phase_qa34_ownership_competition_validation.py
  python Run_PY/run_phase_qa34_ownership_competition_validation.py --beams B14,B15
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
    p = argparse.ArgumentParser(description="Phase QA.3.4 ownership competition validation")
    p.add_argument("--set-key", default="Fourth", help="Fourth / Fifth / Sixth")
    p.add_argument("--beams", default=None, help="Comma-separated beam IDs")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--qa30-root", type=Path, default=None)
    p.add_argument("--qa33-root", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA34_ownership_competition_validation.phase_qa34_orchestrator import (
        PhaseQA34Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseQA34Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        qa30_root=args.qa30_root,
        qa33_root=args.qa33_root,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] QA.3.4 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[QA.3.4] success={result.get('success')}")
    print(f"[QA.3.4] output={result.get('output_root')}")
    print(f"[QA.3.4] pass={result.get('validation_overall_pass')}")
    print(f"[QA.3.4] dropped={((result.get('statistics') or {}).get('dropped'))}")
    print(f"[QA.3.4] owned_elsewhere={((result.get('statistics') or {}).get('owned_elsewhere'))}")
    print(f"[QA.3.4] qa40_target={result.get('dominant_qa40_target')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

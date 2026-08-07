#!/usr/bin/env python3
"""
run_phase_qa33_ownership_explainability.py
Phase QA.3.3 — Ownership Explainability & Decision Trace Engine
MODEL_VERSION: 10.0.3

Usage (from Version10/):
  python Run_PY/run_phase_qa33_ownership_explainability.py
  python Run_PY/run_phase_qa33_ownership_explainability.py --beams B14,B15
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
    p = argparse.ArgumentParser(description="Phase QA.3.3 ownership explainability")
    p.add_argument("--set-key", default="Fourth", help="Fourth / Fifth / Sixth")
    p.add_argument(
        "--beams",
        default=None,
        help="Comma-separated beam IDs (default: Fourth priority list)",
    )
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--qa30-root", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA33_ownership_explainability.phase_qa33_orchestrator import (
        PhaseQA33Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseQA33Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        qa30_root=args.qa30_root,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] QA.3.3 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[QA.3.3] success={result.get('success')}")
    print(f"[QA.3.3] output={result.get('output_root')}")
    print(f"[QA.3.3] pass={result.get('validation_overall_pass')}")
    print(f"[QA.3.3] failures={result.get('failure_frequency')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

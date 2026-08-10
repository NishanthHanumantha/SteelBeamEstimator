#!/usr/bin/env python3
"""
run_phase_qa41_dropped_entity_recovery_audit.py
Phase QA.4.1 — Dropped Entity Recovery Audit (diagnostic only)
MODEL_VERSION: 10.5.0

Usage (from Version10/):
  python Run_PY/run_phase_qa41_dropped_entity_recovery_audit.py
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
    p = argparse.ArgumentParser(description="Phase QA.4.1 dropped entity recovery audit")
    p.add_argument("--set-key", default="Fourth", help="Must remain Fourth for controlled audit")
    p.add_argument("--beams", default=None, help="Comma-separated beam IDs (default: priority 11)")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--qa30-root", type=Path, default=None)
    p.add_argument("--qa33-root", type=Path, default=None)
    p.add_argument("--qa34-root", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA41_dropped_entity_recovery_audit.phase_qa41_orchestrator import (
        PhaseQA41Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseQA41Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        qa30_root=args.qa30_root,
        qa33_root=args.qa33_root,
        qa34_root=args.qa34_root,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] QA.4.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[QA.4.1] success={result.get('success')}")
    print(f"[QA.4.1] output={result.get('output_root')}")
    print(f"[QA.4.1] status={result.get('status')}")
    print(f"[QA.4.1] categories={result.get('category_counts')}")
    print(f"[QA.4.1] potentials={result.get('potential_counts')}")
    print(f"[QA.4.1] P1={result.get('evidence_driven_p1')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_qa43_p2_leader_recovery.py
Phase QA.4.3 — P2 Leader Recovery
MODEL_VERSION: 10.5.2

Usage (from Version10/):
  python Run_PY/run_phase_qa43_p2_leader_recovery.py
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
    p = argparse.ArgumentParser(description="Phase QA.4.3 P2 leader recovery")
    p.add_argument("--set-key", default="Fourth")
    p.add_argument("--beams", default=None)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--qa30-root", type=Path, default=None)
    p.add_argument("--qa33-root", type=Path, default=None)
    p.add_argument("--qa34-root", type=Path, default=None)
    p.add_argument("--qa41-root", type=Path, default=None)
    p.add_argument("--qa42-root", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA43_p2_leader_recovery.phase_qa43_orchestrator import (
        PhaseQA43Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseQA43Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        qa30_root=args.qa30_root,
        qa33_root=args.qa33_root,
        qa34_root=args.qa34_root,
        qa41_root=args.qa41_root,
        qa42_root=args.qa42_root,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] QA.4.3 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    s = result.get("summary") or {}
    print(f"[QA.4.3] success={result.get('success')}")
    print(f"[QA.4.3] status={result.get('status')}")
    print(f"[QA.4.3] model_version={result.get('model_version')}")
    print(f"[QA.4.3] output={result.get('output_root')}")
    print(f"[QA.4.3] leaders={s.get('total_dropped_leaders_inspected')}")
    print(f"[QA.4.3] generated={s.get('p2_candidates_generated')}")
    print(f"[QA.4.3] newly_added={s.get('newly_added_count')}")
    print(f"[QA.4.3] t18_accepted={s.get('t18_accepted_count')}")
    print(f"[QA.4.3] t18_rejected={s.get('t18_rejected_count')}")
    print(f"[QA.4.3] contamination={s.get('cross_beam_contamination')}")
    print(f"[QA.4.3] regression={s.get('regression_status')}")
    print(f"[QA.4.3] determinism={s.get('determinism_status')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

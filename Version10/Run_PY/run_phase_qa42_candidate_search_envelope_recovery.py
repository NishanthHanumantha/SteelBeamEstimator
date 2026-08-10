#!/usr/bin/env python3
"""
run_phase_qa42_candidate_search_envelope_recovery.py
Phase QA.4.2 — P1 Candidate / Search Envelope Recovery
MODEL_VERSION: 10.5.1

Usage (from Version10/):
  python Run_PY/run_phase_qa42_candidate_search_envelope_recovery.py
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
        description="Phase QA.4.2 P1 candidate / search envelope recovery"
    )
    p.add_argument("--set-key", default="Fourth", help="Must remain Fourth")
    p.add_argument("--beams", default=None, help="Comma-separated beam IDs")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--qa30-root", type=Path, default=None)
    p.add_argument("--qa33-root", type=Path, default=None)
    p.add_argument("--qa34-root", type=Path, default=None)
    p.add_argument("--qa41-root", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseQA42_candidate_search_envelope_recovery.phase_qa42_orchestrator import (
        PhaseQA42Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseQA42Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        qa30_root=args.qa30_root,
        qa33_root=args.qa33_root,
        qa34_root=args.qa34_root,
        qa41_root=args.qa41_root,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] QA.4.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    s = result.get("summary") or {}
    print(f"[QA.4.2] success={result.get('success')}")
    print(f"[QA.4.2] status={result.get('status')}")
    print(f"[QA.4.2] model_version={result.get('model_version')}")
    print(f"[QA.4.2] output={result.get('output_root')}")
    print(f"[QA.4.2] HIGH={s.get('high_potential_population')}")
    print(f"[QA.4.2] candidate_generated={s.get('recovery_candidate_generated')}")
    print(f"[QA.4.2] candidate_added_new={s.get('recovery_candidate_added')}")
    print(f"[QA.4.2] already_in_production={s.get('already_in_production_pool')}")
    print(f"[QA.4.2] engine_accepted={s.get('existing_engine_accepted')}")
    print(f"[QA.4.2] engine_rejected={s.get('existing_engine_rejected')}")
    print(f"[QA.4.2] contamination={s.get('cross_beam_contamination_count')}")
    print(f"[QA.4.2] regression={s.get('regression_status')}")
    print(f"[QA.4.2] determinism={s.get('determinism_status')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

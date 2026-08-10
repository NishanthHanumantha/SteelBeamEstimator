#!/usr/bin/env python3
"""
run_phase_p21_leader_tip_chain_analysis.py
Phase P2.1 — Leader Tip / Chain Acceptance Analysis
MODEL_VERSION: 10.5.3

Usage (from Version10/):
  python Run_PY/run_phase_p21_leader_tip_chain_analysis.py
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
    p = argparse.ArgumentParser(description="Phase P2.1 leader tip/chain analysis")
    p.add_argument("--set-key", default="Fourth")
    p.add_argument("--beams", default=None)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseP21_leader_tip_chain_analysis.phase_p21_orchestrator import (
        PhaseP21Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseP21Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] P2.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    root = result.get("root_cause") or {}
    ans = root.get("answers") or {}
    print(f"[P2.1] success={result.get('success')}")
    print(f"[P2.1] status={result.get('status')}")
    print(f"[P2.1] model_version={result.get('model_version')}")
    print(f"[P2.1] leaders={result.get('leader_count')}")
    print(f"[P2.1] eligible={result.get('eligible_count')}")
    print(f"[P2.1] r2_too_strict={ans.get('1_is_r2_leader_tip_too_strict')}")
    print(f"[P2.1] best_policy={ans.get('5_best_policy_without_contamination')}")
    print(f"[P2.1] next={(root.get('recommended_next_phase') or {}).get('option')}")
    print(f"[P2.1] determinism={(result.get('determinism') or {}).get('determinism_status')}")
    print(f"[P2.1] output={result.get('output_root')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

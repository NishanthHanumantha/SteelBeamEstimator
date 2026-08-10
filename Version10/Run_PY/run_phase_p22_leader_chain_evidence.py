#!/usr/bin/env python3
"""
run_phase_p22_leader_chain_evidence.py
Phase P2.2 — Leader-Chain Evidence Enhancement
MODEL_VERSION: 10.5.4

Usage (from Version10/):
  python Run_PY/run_phase_p22_leader_chain_evidence.py
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
    p = argparse.ArgumentParser(description="Phase P2.2 leader-chain evidence enhancement")
    p.add_argument("--set-key", default="Fourth")
    p.add_argument("--beams", default=None)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseP22_leader_chain_evidence.phase_p22_orchestrator import (
        PhaseP22Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseP22Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] P2.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    summary = result.get("summary") or {}
    print(f"[P2.2] success={result.get('success')}")
    print(f"[P2.2] status={result.get('status')}")
    print(f"[P2.2] model_version={result.get('model_version')}")
    print(f"[P2.2] leaders={result.get('leader_count')}")
    print(f"[P2.2] policy_E_accepts={summary.get('policy_e_accept_all')}")
    print(f"[P2.2] candidates={summary.get('production_candidate_keys')}")
    print(
        f"[P2.2] ready_for_controlled_production_gate="
        f"{result.get('ready_for_controlled_production_gate')}"
    )
    print(f"[P2.2] determinism={(result.get('determinism') or {}).get('determinism_status')}")
    print(f"[P2.2] output={result.get('output_root')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

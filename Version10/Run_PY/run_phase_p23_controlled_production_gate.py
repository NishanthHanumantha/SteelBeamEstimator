#!/usr/bin/env python3
"""
run_phase_p23_controlled_production_gate.py
Phase P2.3 — Controlled Production Gate + Re-benchmark
MODEL_VERSION: 10.5.5

Usage (from Version10/):
  python Run_PY/run_phase_p23_controlled_production_gate.py
  python Run_PY/run_phase_p23_controlled_production_gate.py --mode baseline
  python Run_PY/run_phase_p23_controlled_production_gate.py --mode controlled
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
    p = argparse.ArgumentParser(description="Phase P2.3 controlled production gate")
    p.add_argument(
        "--mode",
        default="controlled",
        choices=["baseline", "controlled", "off", "BASELINE", "CONTROLLED", "OFF"],
        help="BASELINE reproduces T18; CONTROLLED applies E_STRONG_COMBINED overlay",
    )
    p.add_argument("--set-key", default="Fourth")
    p.add_argument("--beams", default=None)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseP23_controlled_production_gate.phase_p23_orchestrator import (
        PhaseP23Orchestrator,
    )

    beams = None
    if args.beams:
        beams = [b.strip() for b in args.beams.split(",") if b.strip()]

    orch = PhaseP23Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        mode=args.mode,
        set_key=args.set_key,
        beam_ids=beams,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] P2.3 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.3] success={result.get('success')}")
    print(f"[P2.3] status={result.get('status')}")
    print(f"[P2.3] decision={result.get('decision_class')}")
    print(f"[P2.3] model_version={result.get('model_version')}")
    print(f"[P2.3] mode={result.get('mode')}")
    print(
        f"[P2.3] accepted_E={(result.get('gate') or {}).get('accepted_count')} "
        f"migrations={len(result.get('migrations') or [])}"
    )
    print(f"[P2.3] determinism={(result.get('determinism') or {}).get('determinism_status')}")
    print(f"[P2.3] output={result.get('output_root')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

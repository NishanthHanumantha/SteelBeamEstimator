#!/usr/bin/env python3
"""
run_phase_p23_1_controlled_engineering_recompute.py
Phase P2.3.1 — Controlled Engineering Recompute / Steel Re-benchmark
MODEL_VERSION: 10.5.6

Usage (from Version10/):
  python Run_PY/run_phase_p23_1_controlled_engineering_recompute.py --mode controlled
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
    p = argparse.ArgumentParser(description="Phase P2.3.1 controlled engineering recompute")
    p.add_argument(
        "--mode",
        default="controlled",
        choices=["baseline", "controlled", "BASELINE", "CONTROLLED"],
        help="Measurement mode label (both baseline and controlled recomputes always run)",
    )
    p.add_argument("--set-key", default="Fourth")
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    from PhaseP231_controlled_engineering_recompute.phase_p231_orchestrator import (
        PhaseP231Orchestrator,
    )

    orch = PhaseP231Orchestrator(
        engine_root=_V10,
        output_root=args.output,
        mode=args.mode,
        set_key=args.set_key,
    )
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] P2.3.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    summary = result.get("summary") or {}
    print(f"[P2.3.1] success={result.get('success')}")
    print(f"[P2.3.1] status={result.get('status')}")
    print(f"[P2.3.1] decision={result.get('decision')}")
    print(f"[P2.3.1] model_version={result.get('model_version')}")
    print(f"[P2.3.1] steel_delta_pp={(summary.get('delta') or {}).get('steel_accuracy_pp')}")
    print(f"[P2.3.1] workbook_identical={summary.get('workbook_identical')}")
    print(f"[P2.3.1] broader_e={result.get('broader_e_validation')}")
    print(f"[P2.3.1] determinism={(result.get('determinism') or {}).get('determinism_status')}")
    print(f"[P2.3.1] output={result.get('output_root')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_p24_fourth_set_bar_failure_audit.py
Phase P2.4 — Fourth Set Generalized Bar Failure Attribution & Recovery Audit
MODEL_VERSION: 10.6.0

SCOPE = FOURTH_SET_ONLY
MODE = DIAGNOSTIC_ONLY
ENGINEERING_CHANGES = NONE

Usage (from Version10/):
  python Run_PY/run_phase_p24_fourth_set_bar_failure_audit.py
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
        description="Phase P2.4 Fourth Set bar failure attribution audit (diagnostic only)"
    )
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = _parse()
    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = DIAGNOSTIC_ONLY")
    print("ENGINEERING_CHANGES = NONE")

    from PhaseP24_fourth_set_bar_failure_audit.phase_p24_orchestrator import (
        PhaseP24Orchestrator,
    )

    orch = PhaseP24Orchestrator(engine_root=_V10, output_root=args.output)
    try:
        result = orch.run()
    except Exception as exc:
        print(f"[ERROR] P2.4 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = result.get("metrics") or {}
    q = m.get("questions") or {}
    print(f"[P2.4] success={result.get('success')}")
    print(f"[P2.4] status={result.get('status')}")
    print(f"[P2.4] model_version={result.get('model_version')}")
    print(f"[P2.4] gt_bars={m.get('gt_total_bars')}")
    print(f"[P2.4] matched={m.get('matched_bars')}")
    print(f"[P2.4] unmatched={m.get('unmatched_gt_bars')}")
    print(f"[P2.4] extra={m.get('extra_model_bars')}")
    print(f"[P2.4] dominant={q.get('Q6_largest_first_fail')}")
    print(f"[P2.4] recommend={m.get('recommended_next_phase')}")
    print(f"[P2.4] determinism={(result.get('determinism') or {}).get('determinism_status')}")
    print(f"[P2.4] output={result.get('output_root')}")
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

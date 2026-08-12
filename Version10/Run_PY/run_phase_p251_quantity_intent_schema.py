#!/usr/bin/env python3
"""
run_phase_p251_quantity_intent_schema.py
Phase P2.5.1 — Quantity Intent Schema
MODEL_VERSION: 10.6.4

Usage (from Version10/):
  python Run_PY/run_phase_p251_quantity_intent_schema.py
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


def main() -> int:
    p = argparse.ArgumentParser(description="P2.5.1 Quantity Intent Schema")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = DETERMINISTIC_SCHEMA_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = NOT_INCLUDED")

    from PhaseP251_quantity_intent_schema.phase_p251_orchestrator import run_phase_p251

    try:
        r1 = run_phase_p251(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
        r2 = run_phase_p251(
            version10_root=_V10,
            output_root=args.output,
            run_tests=False,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.1] success={r1.get('success') and r2.get('success')}")
    print(f"[P2.5.1] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.1] decision={r1.get('decision')}")
    print(
        f"[P2.5.1] determinism_run1={(r1.get('determinism') or {}).get('determinism_status')} "
        f"run2={(r2.get('determinism') or {}).get('determinism_status')}"
    )
    print(f"[P2.5.1] regression_unchanged={(r1.get('regression') or {}).get('unchanged')}")
    m = r1.get("metrics") or {}
    print(
        f"[P2.5.1] intents={m.get('quantity_intents_generated')} "
        f"coverage={m.get('QUANTITY_INTENT_COVERAGE')}% "
        f"explicit={m.get('EXPLICIT_QUANTITY_RATE')}% "
        f"unresolved={m.get('UNRESOLVED_QUANTITY_RATE')}%"
    )
    print(f"[P2.5.1] output={r1.get('output_root')}")
    return 0 if r1.get("success") and r2.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

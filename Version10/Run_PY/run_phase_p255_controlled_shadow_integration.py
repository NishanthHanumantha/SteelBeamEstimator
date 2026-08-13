#!/usr/bin/env python3
"""
run_phase_p255_controlled_shadow_integration.py
Phase P2.5.5 — Controlled Shadow Integration
MODEL_VERSION: 10.8.1

Usage (from Version10/):
  python Run_PY/run_phase_p255_controlled_shadow_integration.py
  python Run_PY/run_phase_p255_controlled_shadow_integration.py --live
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
    p = argparse.ArgumentParser(description="P2.5.5 Controlled Shadow Integration")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument(
        "--live",
        action="store_true",
        help="Re-call Claude Vision (default replays frozen P2.5.4 responses)",
    )
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = SHADOW_INTEGRATION_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = SHADOW_OBSERVER")

    from PhaseP255_controlled_shadow_integration.phase_p255_orchestrator import (
        run_phase_p255,
    )

    try:
        r1 = run_phase_p255(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            live=bool(args.live),
        )
        if r1.get("error") and not r1.get("success"):
            print(f"[ERROR] P2.5.5 aborted: {r1.get('error')}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[ERROR] P2.5.5 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.5.5] success={r1.get('success')}")
    print(f"[P2.5.5] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.5] decision={r1.get('decision')}")
    print(f"[P2.5.5] vision_source={r1.get('vision_source')}")
    print(f"[P2.5.5] candidates={r1.get('candidate_count')}")
    print(
        f"[P2.5.5] BOTH_AGREE={m.get('BOTH_AGREE')} "
        f"VISION_ONLY={m.get('VISION_ONLY_RESOLVED')} "
        f"DET_ONLY={m.get('DETERMINISTIC_ONLY_RESOLVED')} "
        f"CONFLICT={m.get('VISION_CONFLICT')} "
        f"BOTH_UNRES={m.get('BOTH_UNRESOLVED')} "
        f"VISION_WRONG={m.get('VISION_WRONG')}"
    )
    print(f"[P2.5.5] production_mutations={m.get('production_mutation_count')}")
    print(f"[P2.5.5] steel/bbs/excel diffs={m.get('steel_quantity_differences')}/{m.get('bbs_differences')}/{m.get('excel_differences')}")
    print(f"[P2.5.5] regression={(r1.get('regression') or {}).get('unchanged')}")
    print(f"[P2.5.5] firewall={(r1.get('firewall') or {}).get('ok')}")
    print(f"[P2.5.5] B58={r1.get('b58_ok')}")
    print(f"[P2.5.5] estimated_cost_usd={r1.get('estimated_api_cost_usd')}")
    print(f"[P2.5.5] output={r1.get('output_root')}")
    print(f"[P2.5.5] {r1.get('decision')}")
    return 0 if r1.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

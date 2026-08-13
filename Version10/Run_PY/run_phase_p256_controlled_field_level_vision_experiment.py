#!/usr/bin/env python3
"""
run_phase_p256_controlled_field_level_vision_experiment.py
Phase P2.5.6 — Controlled Field-Level Vision Experiment
MODEL_VERSION: 10.8.2

Usage (from Version10/):
  python Run_PY/run_phase_p256_controlled_field_level_vision_experiment.py
  python Run_PY/run_phase_p256_controlled_field_level_vision_experiment.py --live
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
    p = argparse.ArgumentParser(description="P2.5.6 Controlled Field-Level Vision Experiment")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument(
        "--live",
        action="store_true",
        help="Re-call Claude Vision (default replays frozen P2.5.4 responses)",
    )
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = SHADOW_FIELD_EXPERIMENT_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = SHADOW_OBSERVER")

    from PhaseP256_controlled_field_level_vision_experiment.phase_p256_orchestrator import (
        run_phase_p256,
    )

    try:
        r1 = run_phase_p256(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            live=bool(args.live),
        )
        if r1.get("error") and not r1.get("success"):
            print(f"[ERROR] P2.5.6 aborted: {r1.get('error')}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[ERROR] P2.5.6 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.5.6] success={r1.get('success')}")
    print(f"[P2.5.6] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.6] decision={r1.get('decision')}")
    print(f"[P2.5.6] vision_source={r1.get('vision_source')}")
    print(f"[P2.5.6] candidates={r1.get('candidate_count')}")
    print(
        f"[P2.5.6] accepted_fields={m.get('accepted_vision_field_candidates')} "
        f"rejected={m.get('rejected_vision_fields')} "
        f"conflicts={m.get('conflicting_vision_fields')} "
        f"SAFE={m.get('SAFE_FIELD_CANDIDATE_RATE')} "
        f"CONFLICT_RATE={m.get('FIELD_CONFLICT_RATE')}"
    )
    print(f"[P2.5.6] B46/B58/B120={r1.get('b46_ok')}/{r1.get('b58_ok')}/{r1.get('b120_ok')}")
    print(f"[P2.5.6] production_mutations={m.get('production_mutation_count')}")
    print(f"[P2.5.6] regression={(r1.get('regression') or {}).get('unchanged')}")
    print(f"[P2.5.6] estimated_cost_usd={r1.get('estimated_api_cost_usd')}")
    print(f"[P2.5.6] output={r1.get('output_root')}")
    print(f"[P2.5.6] {r1.get('decision')}")
    return 0 if r1.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

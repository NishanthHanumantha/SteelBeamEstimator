#!/usr/bin/env python3
"""
run_phase_p269_reinforcement_group_interpretation.py
Phase P2.6.9 — Reinforcement Group Interpretation Benchmark
MODEL_VERSION: 10.11.9

Default: OFFLINE_BENCHMARK. Does not mutate production or P2.6.4–P2.6.8 artefacts.
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
    p = argparse.ArgumentParser(description="P2.6.9 Reinforcement Group Interpretation Benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_BENCHMARK"], default="OFFLINE_BENCHMARK")
    args = p.parse_args()

    print("P2.6.9 REINFORCEMENT GROUP INTERPRETATION BENCHMARK")
    print("SHADOW / RESEARCH ONLY")
    print("PRODUCTION ROUTING UNCHANGED")
    print("NO LIVE API")
    print("TARGET = 6")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP269_reinforcement_group_interpretation.phase_p269_orchestrator import run_phase_p269

    try:
        r1 = run_phase_p269(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.9 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.6.9] status={r1.get('pass_fail')}")
    print(f"[P2.6.9] decision={r1.get('decision')}")
    print(f"[P2.6.9] capability={r1.get('capability')}")
    print(f"[P2.6.9] aggregate={m.get('aggregate')}")
    print(f"[P2.6.9] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.9] P2.6.9 does NOT authorize production promotion.")
    print(f"[P2.6.9] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

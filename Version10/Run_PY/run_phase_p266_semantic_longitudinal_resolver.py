#!/usr/bin/env python3
"""
run_phase_p266_semantic_longitudinal_resolver.py
Phase P2.6.6 — Semantic Longitudinal Ambiguity Resolver
MODEL_VERSION: 10.11.6

Default: REPLAY_P261_CACHED. Does not mutate production or P2.6.4/P2.6.5 routing.
LIVE_API is opt-in shadow only and never writes production state.
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
    p = argparse.ArgumentParser(description="P2.6.6 Semantic Longitudinal Ambiguity Resolver")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["REPLAY_P261_CACHED", "LIVE_API"], default="REPLAY_P261_CACHED")
    args = p.parse_args()

    print("SCOPE = ROLE_COVERAGE_GAP_SEMANTIC_SHADOW")
    print("MODE = SHADOW_RESEARCH")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print("Observed routing = P2.6.4/P2.6.5 unchanged.")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP266_semantic_longitudinal_resolver.phase_p266_orchestrator import run_phase_p266

    try:
        r1 = run_phase_p266(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.6 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.6.6] status={r1.get('pass_fail')}")
    print(f"[P2.6.6] decision={r1.get('decision')}")
    print(
        f"[P2.6.6] targets={m.get('TARGET_BEAMS')} "
        f"DISTINCT={m.get('DISTINCT_REINFORCEMENT')} DUP={m.get('DUPLICATE_OR_REPEAT')} "
        f"AMB={m.get('AMBIGUOUS')} UNS={m.get('UNSUPPORTED')}"
    )
    sep = (m.get("separability") or {}).get("semantic_distinguishes_b128_from_b141_b23")
    print(f"[P2.6.6] B128/B141/B23 semantic split={sep}")
    print(f"[P2.6.6] live_calls={m.get('LIVE_VISION_CALLS')}")
    print(f"[P2.6.6] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.6] P2.6.6 does NOT authorize production promotion.")
    print(f"[P2.6.6] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

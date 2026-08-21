#!/usr/bin/env python3
"""
run_phase_p2610d2_shadow_hybrid_semantic_resolver.py
Phase P2.6.10-D.2 — Shadow Hybrid Semantic Resolver
MODEL_VERSION: 10.11.20

OFFLINE ONLY. Applies the D.1 authority contract to the D.1 benchmark population.
Does not call Claude. Does not rerender. Does not mutate production.
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
    p = argparse.ArgumentParser(description="P2.6.10-D.2 shadow hybrid semantic resolver")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("P2.6.10-D.2 SHADOW HYBRID SEMANTIC RESOLVER")
    print("SHADOW ONLY / FAIL CLOSED / NO CLAUDE / NO PRODUCTION MUTATION")
    print("LIVE_CLAUDE_CALL = false")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")

    from PhaseP2610D2_shadow_hybrid_semantic_resolver.phase_p2610d2_orchestrator import (
        run_phase_p2610d2,
    )

    try:
        r1 = run_phase_p2610d2(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-D.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-D.2] status={r1.get('pass_fail')} decision={r1.get('decision')}")
    pop = r1.get("population") or {}
    print(f"[P2.6.10-D.2] population={pop.get('discovered_count')} expected={pop.get('expected')}")
    print(f"[P2.6.10-D.2] live_claude_call={r1.get('live_claude_call')}")
    print(f"[P2.6.10-D.2] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-D.2] next: P2.6.10-D.3 shadow engineering-input binding (still no production)")
    print(f"[P2.6.10-D.2] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

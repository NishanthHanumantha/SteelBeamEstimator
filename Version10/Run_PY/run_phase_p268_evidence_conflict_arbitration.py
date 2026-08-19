#!/usr/bin/env python3
"""
run_phase_p268_evidence_conflict_arbitration.py
Phase P2.6.8 — Evidence-Conflict Arbitration / Layer-Aware Semantic Resolver
MODEL_VERSION: 10.11.8

Default: OFFLINE_ARBITRATION. Does not mutate production or P2.6.4–P2.6.7 artefacts.
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
    p = argparse.ArgumentParser(description="P2.6.8 Evidence-Conflict Arbitration")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_ARBITRATION"], default="OFFLINE_ARBITRATION")
    args = p.parse_args()

    print("P2.6.8 EVIDENCE-CONFLICT ARBITRATION")
    print("SHADOW / RESEARCH ONLY")
    print("PRODUCTION ROUTING UNCHANGED")
    print("NO LIVE API")
    print("TARGET = 29")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP268_evidence_conflict_arbitration.phase_p268_orchestrator import run_phase_p268

    try:
        r1 = run_phase_p268(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.8 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    m = r1.get("metrics") or {}
    print(f"[P2.6.8] status={r1.get('pass_fail')}")
    print(f"[P2.6.8] decision={r1.get('decision')}")
    print(f"[P2.6.8] conflicts={m.get('conflict_distribution')}")
    print(f"[P2.6.8] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.8] P2.6.8 does NOT authorize production promotion.")
    print(f"[P2.6.8] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

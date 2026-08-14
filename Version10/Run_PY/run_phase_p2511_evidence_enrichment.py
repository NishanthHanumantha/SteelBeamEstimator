#!/usr/bin/env python3
"""
run_phase_p2511_evidence_enrichment.py
Phase P2.5.11 — Evidence Enrichment for Held New-Stirrup Recoveries
MODEL_VERSION: 10.10.0

Usage (from Version10/):
  python Run_PY/run_phase_p2511_evidence_enrichment.py
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
    p = argparse.ArgumentParser(description="P2.5.11 Evidence Enrichment")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("SCOPE = FIFTH_SET_PRIMARY")
    print("MODE = REPLAY_P257_LIVE_RESULTS")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = REPLAY_ONLY")
    print("PRODUCTION_WRITE = false")
    print("P2.5.11 does NOT authorize production promotion.")

    from PhaseP2511_evidence_enrichment.phase_p2511_orchestrator import run_phase_p2511

    try:
        r1 = run_phase_p2511(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.11 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.11] status={r1.get('pass_fail')}")
    print(f"[P2.5.11] decision={r1.get('decision')}")
    cmp = r1.get("comparison") or {}
    m = cmp.get("metrics") or {}
    print(
        f"[P2.5.11] det={m.get('deterministic_accuracy')} p259={m.get('p259_accuracy')} "
        f"p2510={m.get('p2510_accuracy')} p2511={m.get('p2511_accuracy')}"
    )
    print(f"[P2.5.11] gate={cmp.get('gate_counts')} holds_promoted={cmp.get('holds_promoted')}")
    prod = r1.get("production") or {}
    print(f"[P2.5.11] production_mutations={prod.get('production_mutation_count')}")
    print("[P2.5.11] P2.5.11 does NOT authorize production promotion.")
    print(f"[P2.5.11] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_p2610c1c2_evidence_inventory_candidate_selection.py
Phase P2.6.10-C.1+C.2 — Evidence Inventory & Preference-Preserving Candidate Selection
MODEL_VERSION: 10.11.15

Default: OFFLINE_VALIDATION. Read-only over B.1/B.2/B.3 artefacts.
Does not mutate production or prior-phase artefacts.
No Claude Vision. No DXF rerender.
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
    p = argparse.ArgumentParser(description="P2.6.10-C.1+C.2 evidence inventory and candidate selection")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_VALIDATION"], default="OFFLINE_VALIDATION")
    args = p.parse_args()

    print("P2.6.10-C.1+C.2 EVIDENCE INVENTORY & PREFERENCE-PRESERVING CANDIDATE SELECTION")
    print("SHADOW / READ-ONLY / NO PRODUCTION MUTATION")
    print("NO DXF RERENDER")
    print("NO LIVE CLAUDE VISION")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP2610C1C2_evidence_inventory_candidate_selection.phase_p2610c1c2_orchestrator import (
        run_phase_p2610c1c2,
    )

    try:
        r1 = run_phase_p2610c1c2(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-C.1+C.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-C.1+C.2] status={r1.get('pass_fail')}")
    print(f"[P2.6.10-C.1+C.2] decision={r1.get('decision')}")
    print(f"[P2.6.10-C.1+C.2] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-C.1+C.2] LIVE_CLAUDE_VISION = NOT_CALLED")
    print("[P2.6.10-C.1+C.2] does NOT authorize Claude Vision or production promotion.")
    print(f"[P2.6.10-C.1+C.2] output={r1.get('output_root')}")
    return 0 if str(r1.get("decision") or "").startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())

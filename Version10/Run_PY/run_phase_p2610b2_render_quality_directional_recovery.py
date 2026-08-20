#!/usr/bin/env python3
"""
run_phase_p2610b2_render_quality_directional_recovery.py
Phase P2.6.10-B.2 — Render Quality & Direction-Aware Adaptive Crop Recovery
MODEL_VERSION: 10.11.13

Default: OFFLINE_VALIDATION. Fourth drawing set only.
Does not mutate production or P2.6.6–P2.6.10-B.1 artefacts.
No Claude Vision.
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
    p = argparse.ArgumentParser(description="P2.6.10-B.2 render quality and directional recovery")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_VALIDATION"], default="OFFLINE_VALIDATION")
    args = p.parse_args()

    print("P2.6.10-B.2 RENDER QUALITY & DIRECTION-AWARE ADAPTIVE CROP RECOVERY")
    print("SHADOW / VALIDATION ONLY")
    print("FOURTH DRAWING SET ONLY")
    print("CONTEXT-FIRST THEN DETAIL")
    print("PRODUCTION ROUTING UNCHANGED")
    print("NO LIVE CLAUDE VISION")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP2610B2_render_quality_directional_recovery.phase_p2610b2_orchestrator import run_phase_p2610b2

    try:
        r1 = run_phase_p2610b2(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-B.2 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-B.2] status={r1.get('pass_fail')}")
    print(f"[P2.6.10-B.2] decision={r1.get('decision')}")
    print(f"[P2.6.10-B.2] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-B.2] does NOT authorize Claude Vision or production promotion.")
    print(f"[P2.6.10-B.2] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") in ("PASS", "PARTIAL") else 2


if __name__ == "__main__":
    raise SystemExit(main())

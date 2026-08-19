#!/usr/bin/env python3
"""
run_phase_p2610a_beam_region_crop_audit.py
Phase P2.6.10-A — Existing Beam-Region Crop Capability Audit
MODEL_VERSION: 10.11.10

Default: OFFLINE_AUDIT. Does not mutate production or P2.6.6–P2.6.9 artefacts.
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
    p = argparse.ArgumentParser(description="P2.6.10-A Existing Beam-Region Crop Capability Audit")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_AUDIT"], default="OFFLINE_AUDIT")
    args = p.parse_args()

    print("P2.6.10-A EXISTING BEAM-REGION CROP CAPABILITY AUDIT")
    print("SHADOW / RESEARCH ONLY")
    print("PRODUCTION ROUTING UNCHANGED")
    print("NO LIVE CLAUDE VISION")
    print("TARGET = 6")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP2610A_beam_region_crop_audit.phase_p2610a_orchestrator import run_phase_p2610a

    try:
        r1 = run_phase_p2610a(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-A failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-A] status={r1.get('pass_fail')}")
    print(f"[P2.6.10-A] decision={r1.get('decision')}")
    print(f"[P2.6.10-A] reusability={r1.get('reusability_class')}")
    print(f"[P2.6.10-A] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-A] P2.6.10-A does NOT authorize production promotion.")
    print(f"[P2.6.10-A] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") in ("PASS", "PARTIAL") else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_p2501_evidence_spatial_sanity.py
Phase P2.5.0.1 — Evidence Spatial Sanity Diagnostic
MODEL_VERSION: 10.6.1

Usage (from Version10/):
  python Run_PY/run_phase_p2501_evidence_spatial_sanity.py
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
    p = argparse.ArgumentParser(description="P2.5.0.1 Evidence Spatial Sanity Diagnostic")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--skip-regenerate", action="store_true")
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = DIAGNOSTIC_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = NOT_INCLUDED")

    from PhaseP2501_evidence_spatial_sanity.phase_p2501_orchestrator import run_phase_p2501

    # Run twice for determinism requirement
    try:
        r1 = run_phase_p2501(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            regenerate_focus_crops=not args.skip_regenerate,
        )
        r2 = run_phase_p2501(
            version10_root=_V10,
            output_root=args.output,
            run_tests=False,
            regenerate_focus_crops=False,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.0.1 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    d1 = (r1.get("determinism") or {}).get("determinism_status")
    d2 = (r2.get("determinism") or {}).get("determinism_status")
    print(f"[P2.5.0.1] success={r1.get('success') and r2.get('success')}")
    print(f"[P2.5.0.1] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.0.1] determinism_run1={d1} run2={d2}")
    print(f"[P2.5.0.1] regression_unchanged={(r1.get('regression') or {}).get('unchanged')}")
    for bid, rc in (r1.get("root_causes") or {}).items():
        print(f"[P2.5.0.1] {bid}_root_cause={rc.get('label')}")
    print(f"[P2.5.0.1] output={r1.get('output_root')}")
    return 0 if r1.get("success") and r2.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

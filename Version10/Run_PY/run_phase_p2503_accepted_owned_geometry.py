#!/usr/bin/env python3
"""
run_phase_p2503_accepted_owned_geometry.py
Phase P2.5.0.3 — Accepted OWN TOP_BAR Evidence Packaging Fix
MODEL_VERSION: 10.6.2

Usage (from Version10/):
  python Run_PY/run_phase_p2503_accepted_owned_geometry.py
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
    p = argparse.ArgumentParser(description="P2.5.0.3 Accepted OWN TOP_BAR Evidence Packaging")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = EVIDENCE_LAYER_FIX")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = NOT_INCLUDED")

    from PhaseP2503_accepted_owned_geometry.phase_p2503_orchestrator import run_phase_p2503

    try:
        r1 = run_phase_p2503(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
        )
        r2 = run_phase_p2503(
            version10_root=_V10,
            output_root=args.output,
            run_tests=False,
        )
    except Exception as exc:
        print(f"[ERROR] P2.5.0.3 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.0.3] success={r1.get('success') and r2.get('success')}")
    print(f"[P2.5.0.3] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.0.3] decision={r1.get('decision')}")
    print(
        f"[P2.5.0.3] determinism_run1={(r1.get('determinism') or {}).get('determinism_status')} "
        f"run2={(r2.get('determinism') or {}).get('determinism_status')}"
    )
    print(f"[P2.5.0.3] regression_unchanged={(r1.get('regression') or {}).get('unchanged')}")
    print(f"[P2.5.0.3] output={r1.get('output_root')}")
    return 0 if r1.get("success") and r2.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

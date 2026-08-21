#!/usr/bin/env python3
"""
run_phase_p2610c4_shadow_truth_reconciliation.py
Phase P2.6.10-C.4 — Shadow Truth Reconciliation & Vision Benchmark Calibration
MODEL_VERSION: 10.11.17

Read-only. Consumes existing C.3 six-beam artefacts.
No Claude API. No DXF rerender. No production writes.
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
    p = argparse.ArgumentParser(description="P2.6.10-C.4 shadow truth reconciliation (read-only)")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--run-tests", action="store_true", help="Explicitly run unit tests (default unless --skip-unit-tests)")
    p.add_argument("--report-only", action="store_true", help="Skip unit tests; write reports from existing C.3 evidence")
    p.add_argument("--verify-manual-evidence", action="store_true", default=True)
    p.add_argument("--no-verify-manual-evidence", action="store_false", dest="verify_manual_evidence")
    args = p.parse_args()

    print("P2.6.10-C.4 SHADOW TRUTH RECONCILIATION & VISION BENCHMARK CALIBRATION")
    print("SHADOW ONLY / FAIL CLOSED / NO PRODUCTION MUTATION")
    print("CONSUMES C.3 six-beam artefacts")
    print("LIVE_CLAUDE_CALL = false")
    print("NO DXF RERENDER / NO RESELECTION")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")

    from PhaseP2610C4_shadow_truth_reconciliation.phase_p2610c4_orchestrator import run_phase_p2610c4

    try:
        r1 = run_phase_p2610c4(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests and not args.report_only,
            report_only=args.report_only,
            verify_manual_evidence=args.verify_manual_evidence,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-C.4 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-C.4] terminal_gate={r1.get('terminal_gate')}")
    print(f"[P2.6.10-C.4] decision={r1.get('decision')}")
    print(f"[P2.6.10-C.4] LIVE_CLAUDE_CALL={r1.get('live_claude_call')}")
    print(f"[P2.6.10-C.4] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-C.4] does NOT authorize production promotion.")
    print(f"[P2.6.10-C.4] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

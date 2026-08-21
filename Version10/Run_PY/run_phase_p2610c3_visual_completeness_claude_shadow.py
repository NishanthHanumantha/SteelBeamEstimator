#!/usr/bin/env python3
"""
run_phase_p2610c3_visual_completeness_claude_shadow.py
Phase P2.6.10-C.3 — Visual Completeness Gate + Claude Vision Shadow Benchmark
MODEL_VERSION: 10.11.16

Default: OFFLINE_VALIDATION (gate + tests, no live API).
Use --mode LIVE_SHADOW for the six-beam then eligible-population Vision benchmark.
Does not mutate production. Does not reselect or rerender C.1+C.2 artefacts.
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
    p = argparse.ArgumentParser(description="P2.6.10-C.3 visual completeness + Claude shadow benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_VALIDATION", "LIVE_SHADOW"], default="OFFLINE_VALIDATION")
    p.add_argument("--include-limitations", action="store_true", help="Also call Claude for VISION_READY_WITH_LIMITATIONS (labelled diagnostic)")
    args = p.parse_args()

    print("P2.6.10-C.3 VISUAL COMPLETENESS GATE + CLAUDE VISION SHADOW BENCHMARK")
    print("SHADOW ONLY / FAIL CLOSED / NO PRODUCTION MUTATION")
    print("CONSUMES C.1+C.2 selection_manifest.json")
    print("NO DXF RERENDER / NO RESELECTION")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP2610C3_visual_completeness_claude_shadow.phase_p2610c3_orchestrator import run_phase_p2610c3

    try:
        r1 = run_phase_p2610c3(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
            include_limitations=args.include_limitations,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-C.3 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.6.10-C.3] status={r1.get('pass_fail')}")
    print(f"[P2.6.10-C.3] decision={r1.get('decision')}")
    print(f"[P2.6.10-C.3] live={r1.get('live_claude_vision')}")
    print(f"[P2.6.10-C.3] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-C.3] does NOT authorize production promotion.")
    print(f"[P2.6.10-C.3] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
run_phase_p2610b_adaptive_beam_detail_crop.py
Phase P2.6.10-B — Adaptive Beam Detail Completeness & Reinforcement Evidence Crop Benchmark
MODEL_VERSION: 10.11.11

Default: OFFLINE_BENCHMARK. Does not mutate production or P2.6.6–P2.6.10-A artefacts.
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
    p = argparse.ArgumentParser(description="P2.6.10-B Adaptive Beam Detail Completeness Crop Benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--mode", choices=["OFFLINE_BENCHMARK"], default="OFFLINE_BENCHMARK")
    args = p.parse_args()

    print("P2.6.10-B ADAPTIVE BEAM DETAIL COMPLETENESS CROP BENCHMARK")
    print("SHADOW / RESEARCH ONLY")
    print("PRODUCTION ROUTING UNCHANGED")
    print("NO LIVE CLAUDE VISION")
    print("TARGET = 6")
    print("ENGINEERING_CHANGES = NONE")
    print("PRODUCTION_WRITE = false")
    print(f"EXECUTION_MODE = {args.mode}")

    from PhaseP2610B_adaptive_beam_detail_crop.phase_p2610b_orchestrator import run_phase_p2610b

    try:
        r1 = run_phase_p2610b(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            mode=args.mode,
        )
    except Exception as exc:
        print(f"[ERROR] P2.6.10-B failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    rec = r1.get("recommendation") or {}
    print(f"[P2.6.10-B] status={r1.get('pass_fail')}")
    print(f"[P2.6.10-B] decision={r1.get('decision')}")
    print(f"[P2.6.10-B] readiness={rec.get('readiness')}")
    print(f"[P2.6.10-B] production_mutations={(r1.get('production') or {}).get('production_mutation_count')}")
    print("[P2.6.10-B] P2.6.10-B does NOT authorize Claude Vision or production promotion.")
    print(f"[P2.6.10-B] output={r1.get('output_root')}")
    return 0 if r1.get("pass_fail") in ("PASS", "PARTIAL") else 2


if __name__ == "__main__":
    raise SystemExit(main())

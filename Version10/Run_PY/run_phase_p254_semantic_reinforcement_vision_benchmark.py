#!/usr/bin/env python3
"""
run_phase_p254_semantic_reinforcement_vision_benchmark.py
Phase P2.5.4 — Semantic Reinforcement Vision Benchmark & Shadow Resolver
MODEL_VERSION: 10.8.0

Usage (from Version10/):
  python Run_PY/run_phase_p254_semantic_reinforcement_vision_benchmark.py
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
    p = argparse.ArgumentParser(description="P2.5.4 Semantic Reinforcement Vision Benchmark")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument(
        "--prep-only",
        action="store_true",
        help="Build benchmark twice without Claude calls",
    )
    args = p.parse_args()

    print("SCOPE = FOURTH_SET_ONLY")
    print("MODE = SHADOW_BENCHMARK_ONLY")
    print("ENGINEERING_CHANGES = NONE")
    print("CLAUDE = SHADOW_ISOLATED")

    from PhaseP254_semantic_reinforcement_vision_benchmark.phase_p254_orchestrator import (
        run_phase_p254,
    )

    try:
        r1 = run_phase_p254(
            version10_root=_V10,
            output_root=args.output,
            run_tests=not args.skip_unit_tests,
            run_claude=not args.prep_only,
        )
        if r1.get("error") and not r1.get("success"):
            print(f"[ERROR] P2.5.4 aborted: {r1.get('error')}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[ERROR] P2.5.4 failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"[P2.5.4] success={r1.get('success')}")
    print(f"[P2.5.4] model_version={(r1.get('meta') or {}).get('model_version')}")
    print(f"[P2.5.4] decision={r1.get('decision')}")
    print(f"[P2.5.4] claude_model={r1.get('claude_model')}")
    print(f"[P2.5.4] benchmark={r1.get('benchmark_count')}")
    print(f"[P2.5.4] classes={r1.get('class_distribution')}")
    m = r1.get("metrics") or {}
    c = m.get("counts") or {}
    print(
        f"[P2.5.4] calls={m.get('CLAUDE_CALL_COUNT')} "
        f"exact={c.get('exact')} partial={c.get('partial')} "
        f"incorrect={c.get('incorrect')} halluc={c.get('hallucination')} "
        f"abstain={c.get('appropriate_abstention')}"
    )
    print(
        f"[P2.5.4] semantic_acc={m.get('SEMANTIC_INTERPRETATION_ACCURACY')} "
        f"type_acc={m.get('TYPE_ACCURACY')} role_acc={m.get('ROLE_ACCURACY')} "
        f"assoc_acc={m.get('BEAM_ASSOCIATION_ACCURACY')} "
        f"vor={m.get('VISION_ONLY_RESOLUTION_RATE')} "
        f"halluc_rate={m.get('HALLUCINATION_RATE')}"
    )
    print(f"[P2.5.4] regression_unchanged={(r1.get('regression') or {}).get('unchanged')}")
    print(f"[P2.5.4] firewall={(r1.get('firewall') or {}).get('ok')}")
    print(
        f"[P2.5.4] pipeline_det="
        f"{(r1.get('determinism') or {}).get('pipeline_determinism_status')}"
    )
    print(f"[P2.5.4] output={r1.get('output_root')}")
    print(f"[P2.5.4] {r1.get('decision')}")
    return 0 if r1.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())

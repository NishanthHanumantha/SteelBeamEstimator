"""
run_phase_w6_hybrid_production_authority.py
Runner for Phase W.6 — Hybrid Production Authority Integration.

Usage:
    python Run_PY/run_phase_w6_hybrid_production_authority.py
    python Run_PY/run_phase_w6_hybrid_production_authority.py <run_root>

Inserts Hybrid semantic resolution between R.1.3 and V.B.1.
Soft-exit 0 when HYBRID_MODE=off or when deterministic fallback is used.
Exit 1 only when the required R13 production model is missing.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys


def main() -> None:
    root = pathlib.Path(__file__).parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from config.run_context import resolve_run_context, run_root_from_argv
    from PhaseW6_hybrid_production_authority.orchestrator import run_production_hybrid

    arg = run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=arg, engine_root=root)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    print(f"[W.6] engine_root={ctx.engine_root}")
    print(f"[W.6] run_root={ctx.run_root}")
    print(f"[W.6] output_root={ctx.output_root}")

    result = run_production_hybrid(
        run_id=ctx.run_root.name,
        staging=ctx.run_root,
        persist=True,
    )
    print(json.dumps(
        {
            "ok": result.get("ok"),
            "hybrid_mode": result.get("hybrid_mode"),
            "classification": result.get("classification"),
            "production_authority_applied": result.get("production_authority_applied"),
            "request_count": result.get("request_count"),
            "reason": result.get("reason"),
        },
        indent=2,
    ))
    if result.get("ok"):
        sys.exit(0)
    if result.get("reason") == "R13_MISSING":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

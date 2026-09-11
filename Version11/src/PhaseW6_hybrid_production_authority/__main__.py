"""CLI / subprocess entry: W.6 Hybrid production authority stage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

ensure_src_on_path()

from PhaseW5_production_hybrid_shadow.settings import load_settings

from .orchestrator import run_production_hybrid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="W.6 Hybrid production authority (R13 semantic handoff before VB.1)."
    )
    parser.add_argument(
        "run_root",
        nargs="?",
        default="",
        help="Path to data/web_runs/<run_id> (or Version10 offline root)",
    )
    parser.add_argument("--run-id", default="", help="Override run_id (default: folder name)")
    args = parser.parse_args(argv)
    from config.run_context import resolve_run_context, run_root_from_argv

    staging_arg = Path(args.run_root).resolve() if args.run_root else run_root_from_argv(sys.argv, 1)
    ctx = resolve_run_context(run_root_arg=staging_arg)
    run_id = args.run_id or ctx.run_root.name
    result = run_production_hybrid(
        run_id=run_id,
        staging=ctx.run_root,
        settings=load_settings(),
        persist=True,
    )
    print(
        json.dumps(
            {
                "ok": result.get("ok"),
                "hybrid_mode": result.get("hybrid_mode"),
                "classification": result.get("classification"),
                "production_authority_applied": result.get("production_authority_applied"),
                "request_count": result.get("request_count"),
                "reason": result.get("reason"),
            },
            indent=2,
        )
    )
    if result.get("ok"):
        return 0
    return 1 if result.get("reason") == "R13_MISSING" else 0


if __name__ == "__main__":
    raise SystemExit(main())

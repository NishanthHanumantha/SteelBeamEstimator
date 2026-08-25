"""CLI: post-hoc Hybrid shadow on an existing web run. Does not regenerate Excel."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .paths import ensure_src_on_path

ensure_src_on_path()

from .adapter import public_summary, run_hybrid_shadow
from .settings import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="W.5 Hybrid shadow on an existing Version10 web run (no Excel mutation)."
    )
    parser.add_argument("--run-root", required=True, help="Path to data/web_runs/<run_id>")
    parser.add_argument("--run-id", default="", help="Override run_id (default: folder name)")
    args = parser.parse_args(argv)
    staging = Path(args.run_root).resolve()
    if not staging.is_dir():
        print(f"run-root not found: {staging}", file=sys.stderr)
        return 2
    run_id = args.run_id or staging.name
    result = run_hybrid_shadow(
        run_id=run_id,
        staging=staging,
        settings=load_settings(),
        persist=True,
    )
    print(json.dumps(public_summary(result), indent=2))
    return 0 if result.get("hybrid_status") != "ERROR" else 1


if __name__ == "__main__":
    raise SystemExit(main())

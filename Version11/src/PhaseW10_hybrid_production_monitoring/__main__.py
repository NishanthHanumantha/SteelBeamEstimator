"""CLI: build W.10 monitoring for an existing run tree. No Claude."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

ensure_src_on_path()

from .writer import write_run_monitor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="W.10 Hybrid production monitor (offline, no Claude)."
    )
    parser.add_argument("run_root", help="Path to data/web_runs/<run_id>")
    parser.add_argument("--run-id", default="", help="Override run_id")
    args = parser.parse_args(argv)
    staging = Path(args.run_root).resolve()
    if not staging.is_dir():
        print(json.dumps({"ok": False, "reason": "RUN_ROOT_MISSING", "path": str(staging)}))
        return 2
    run_id = args.run_id or staging.name
    monitor = write_run_monitor(staging=staging, run_id=run_id)
    if monitor is None:
        print(json.dumps({"ok": False, "reason": "MONITOR_WRITE_FAILED", "run_id": run_id}))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "run_id": monitor.get("run_id"),
                "hybrid_eligible": monitor.get("hybrid_eligible"),
                "primary_evidence_count": monitor.get("primary_evidence_count"),
                "compatibility_fallback_count": monitor.get("compatibility_fallback_count"),
                "unexplained_count": monitor.get("unexplained_count"),
                "claude_successful": monitor.get("claude_successful"),
                "cost_classification": (monitor.get("api_usage") or {}).get("cost_classification"),
                "crop_decision": (monitor.get("crop_improvement") or {}).get("decision"),
                "identity_ok": monitor.get("identity_ok"),
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

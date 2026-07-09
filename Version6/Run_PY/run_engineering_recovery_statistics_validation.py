"""Phase J.2.1 — Recovery Statistics Consistency Engine runner."""

import _bootstrap  # noqa: F401

import sys
from pathlib import Path

from src.recovery_statistics_validation.consistency_engine import ConsistencyEngine


def run() -> int:
    project_root = Path.cwd()
    result = ConsistencyEngine(project_root).run()
    validation = result.get("statistics_validation") or {}
    export_validation = result.get("export_validation") or {}
    failed = [item for item in validation.get("checks", []) if item.get("status") == "FAIL"]
    if failed:
        for item in failed:
            print(f"Validation FAIL: {item.get('name')}")
    all_pass = validation.get("status") == "PASS" and export_validation.get("status") == "PASS"
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())

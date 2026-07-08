"""Phase J.2 — Engineering Object Recovery Expansion runner."""

import _bootstrap  # noqa: F401

import sys
from pathlib import Path

from src.engineering_recovery_expansion.expansion_engine import ExpansionEngine


def run() -> int:
    project_root = Path.cwd()
    result = ExpansionEngine(project_root).run()
    validation = result.get("validation") or {}
    export_validation = result.get("export_validation") or {}
    failed = [item for item in validation.get("checks", []) if item.get("status") == "FAIL"]
    if failed:
        for item in failed:
            print(f"Validation FAIL: {item.get('name')}")
    all_pass = validation.get("status") == "PASS" and export_validation.get("status") == "PASS"
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())

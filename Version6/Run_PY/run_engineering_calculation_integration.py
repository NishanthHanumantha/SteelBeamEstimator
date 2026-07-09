"""Phase J.1.3 — Engineering Calculation Integration Repair runner."""

import _bootstrap  # noqa: F401

import sys
from pathlib import Path

from src.engineering_calculation_integration.integration_engine import IntegrationEngine


def run() -> int:
    project_root = Path.cwd()
    engine = IntegrationEngine(project_root)
    result = engine.run()
    validation = result.get("integration_validation") or {}
    export_validation = result.get("export_validation") or {}
    failed = [item for item in validation.get("checks", []) if item.get("status") == "FAIL"]
    if failed:
        for item in failed:
            print(f"Validation FAIL: {item.get('name')}")
    all_pass = validation.get("status") == "PASS" and export_validation.get("status") == "PASS"
    print(
        f"Exports: {export_validation.get('summary', {}).get('passed', 0)}/"
        f"{export_validation.get('summary', {}).get('total_checks', 0)} PASS"
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())

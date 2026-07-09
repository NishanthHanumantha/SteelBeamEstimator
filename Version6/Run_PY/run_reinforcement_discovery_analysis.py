"""Phase QA.ENGINEERING.2 — Reinforcement Discovery Coverage runner."""

import _bootstrap  # noqa: F401

import sys
from pathlib import Path

from src.reinforcement_discovery_analysis.discovery_engine import DiscoveryEngine


def run() -> int:
    project_root = Path.cwd()
    engine = DiscoveryEngine(project_root)
    result = engine.run()
    validation = result.get("validation_report") or {}
    export_validation = result.get("export_validation") or {}
    all_pass = validation.get("status") == "PASS" and export_validation.get("status") == "PASS"
    print(
        f"Validation: {validation.get('summary', {}).get('passed', 0)}/"
        f"{validation.get('summary', {}).get('total_checks', 0)} PASS"
    )
    print(
        f"Exports: {export_validation.get('summary', {}).get('passed', 0)}/"
        f"{export_validation.get('summary', {}).get('total_checks', 0)} PASS"
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())

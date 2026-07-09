"""Phase QA.ENGINEERING.1 — Engineering Coverage Analysis runner."""

import _bootstrap  # noqa: F401

import sys
from pathlib import Path

from src.engineering_analysis.coverage_analysis_engine import CoverageAnalysisEngine


def run() -> int:
    project_root = Path.cwd()
    engine = CoverageAnalysisEngine(project_root)
    result = engine.run()

    validation = result.get("validation_report") or {}
    export_validation = result.get("export_validation") or {}
    all_pass = validation.get("status") == "PASS" and export_validation.get("status") == "PASS"
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())

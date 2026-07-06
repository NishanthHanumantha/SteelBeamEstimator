"""Phase QA.1 — Estimator Output Audit runner."""

import _bootstrap  # noqa: F401

import json
import sys
from pathlib import Path

from src.estimator_validation.audit_engine import AuditEngine
from src.estimator_validation.audit_exporter import AuditExporter
from src.estimator_validation.audit_reporting import AuditReporting
from src.estimator_validation.audit_summary import AuditSummary
from src.estimator_validation.audit_validator import AuditValidator
from src.estimator_validation.audit_types import default_paths


def run() -> int:
    project_root = Path.cwd()
    engine = AuditEngine(project_root)
    result = engine.run()
    summary = AuditSummary.build(result)
    result["audit_summary"] = summary
    result["engineering_code_modified"] = False
    result["engineering_pipeline_frozen"] = True
    validation = AuditValidator().validate(result)
    reporting = AuditReporting.build({**result, "validation_report": validation}, summary)
    result["validation_report"] = validation
    result["audit_report"] = reporting
    output_dir = default_paths(project_root)["output_dir"]
    AuditExporter.export_all(output_dir, result)

    print("\n" + "=" * 60)
    print("PHASE QA.1")
    print("Estimator Output Audit & Root Cause Analysis")
    print("=" * 60)
    print(f"Generated Workbook: {result['generated_workbook']}")
    print(f"Estimator Workbook: {result['estimator_workbook']}")
    print(f"Audit Validation: {validation['status']}")
    print(f"Beams (Estimator/Generated): {summary['total_beams_estimator']}/{summary['total_beams_generated']}")
    print(f"Missing Rows: {summary['missing_rows']}")
    print(f"Extra Rows: {summary['extra_rows']}")
    print(f"Different Cells: {summary['different_cells']}")
    print(f"Discrepancies: {summary['discrepancy_count']}")
    print(f"Recommendations: {summary['recommendation_count']}")
    print(f"Output Directory: {output_dir}")
    print("=" * 60 + "\n")
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())

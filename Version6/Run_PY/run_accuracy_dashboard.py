"""Phase QA.COVERAGE.3 — Engineering Coverage Dashboard runner."""

import _bootstrap  # noqa: F401

import sys
from datetime import datetime, timezone
from pathlib import Path

from src.accuracy_dashboard.accuracy_engine import AccuracyEngine
from src.accuracy_dashboard.accuracy_exporter import AccuracyExporter
from src.accuracy_dashboard.accuracy_reporting import AccuracyReporting
from src.accuracy_dashboard.accuracy_summary import AccuracySummary
from src.accuracy_dashboard.accuracy_types import DASHBOARD_TITLE, OFFICIAL_SUMMARY_EXTENSION, default_paths
from src.accuracy_dashboard.accuracy_validator import AccuracyValidator


def run() -> int:
    project_root = Path.cwd()
    engine = AccuracyEngine(project_root)
    result = engine.run()
    result["run_timestamp"] = datetime.now(timezone.utc).isoformat()

    summary = AccuracySummary.build(result)
    result["accuracy_summary"] = summary

    recommendation = AccuracyReporting._recommended_focus(
        result.get("excel_accuracy", {}),
        result.get("steel_accuracy", {}),
    )
    result["management_summary"] = AccuracyReporting.build_management_summary(result, recommendation)
    result["accuracy_report"] = AccuracyReporting.build(result, summary)

    output_dir = default_paths(project_root)["output_dir"]
    result["improvement_tracker"] = AccuracyExporter.build_improvement_tracker(output_dir, result)

    validation = AccuracyValidator().validate(result)
    result["validation_report"] = validation

    AccuracyExporter.export_all(output_dir, result)
    export_validation = AccuracyValidator.validate_exports(output_dir, result)

    schedule = result["accuracy_dashboard"]["schedule_coverage"]
    steel = result["accuracy_dashboard"]["steel_quantity_coverage"]
    diameter_summary = result["diameter_coverage"]["summary"]
    official = result["official_quantity_summary"]

    print("\n" + "=" * 60)
    print(OFFICIAL_SUMMARY_EXTENSION)
    print(DASHBOARD_TITLE)
    print("=" * 60)
    print(f"Model Version: {result['model_version']}")
    print(f"Generated Workbook: {result['generated_workbook']}")
    print(f"Estimator Workbook: {result['estimator_workbook']}")
    print(f"Beam Coverage: {schedule['beam_coverage_percent']}%")
    print(f"Schedule Coverage: {schedule['schedule_coverage_percent']}%")
    print(f"Official Steel Coverage: {steel['coverage_percent']}%")
    print(f"Official Estimator Total: {official['estimator']['total']} kg")
    print(f"Official Generated Total: {official['generated']['total']} kg")
    print(
        f"Best Diameter: D{diameter_summary.get('best_performing_diameter_mm')} "
        f"({diameter_summary.get('best_performing_coverage_percent')}%)"
    )
    print(
        f"Worst Diameter: D{diameter_summary.get('worst_performing_diameter_mm')} "
        f"({diameter_summary.get('worst_performing_coverage_percent')}%)"
    )
    gap = diameter_summary.get("largest_quantity_gap") or {}
    print(f"Largest Quantity Gap: D{gap.get('diameter_mm')} ({gap.get('difference_kg')} kg)")
    print(f"Validation: {validation['summary']['passed']}/{validation['summary']['total_checks']} PASS")
    print(f"Exports: {export_validation['summary']['passed']}/{export_validation['summary']['total_checks']} PASS")
    print(f"Major Improvement Opportunity: {recommendation['major_improvement_opportunity']}")
    print(f"Output Directory: {output_dir}")
    print("=" * 60 + "\n")

    all_pass = validation["status"] == "PASS" and export_validation["status"] == "PASS"
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())

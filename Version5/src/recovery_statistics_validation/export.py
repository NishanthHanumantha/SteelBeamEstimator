"""Export recovery statistics consistency artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.recovery_statistics_validation.statistics_collector import MODEL_VERSION, PHASE


EXPORT_FILES = (
    "production_snapshot.json",
    "statistics_reconciliation.json",
    "cross_artifact_validation.json",
    "metric_consistency_matrix.json",
    "lineage_consistency.json",
    "consistency_health.json",
    "root_cause_analysis.json",
    "statistics_validation.json",
    "statistics_summary.json",
    "statistics_report.json",
)


class ConsistencyExporter:
    """Write consistency validation JSON exports."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        matrix = (result.get("statistics_reconciliation") or {}).get("matrix") or []
        mapping = {
            "production_snapshot.json": result.get("production_snapshot"),
            "statistics_reconciliation.json": result.get("statistics_reconciliation"),
            "cross_artifact_validation.json": result.get("cross_artifact_validation"),
            "metric_consistency_matrix.json": {
                "matrix_count": len(matrix),
                "matrix": matrix,
            },
            "lineage_consistency.json": result.get("lineage_consistency"),
            "consistency_health.json": result.get("consistency_health"),
            "root_cause_analysis.json": {
                "root_cause_count": len(result.get("root_cause_analysis") or []),
                "root_causes": result.get("root_cause_analysis"),
            },
            "statistics_validation.json": result.get("statistics_validation"),
            "statistics_summary.json": result.get("statistics_summary"),
            "statistics_report.json": result.get("statistics_report"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            ConsistencyExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def validate_exports(output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks = []
        for filename in export_files:
            path = output_dir / filename
            payload = ConsistencyExporter._read_json(path)
            checks.append({"name": f"Export Exists {filename}", "status": "PASS" if payload is not None else "FAIL"})
            checks.append({"name": f"Export Valid JSON {filename}", "status": "PASS" if payload is not None else "FAIL"})
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        summary = result.get("statistics_summary") or {}
        health = result.get("consistency_health") or {}
        print("\n" + "=" * 60)
        print("Recovery Statistics Consistency")
        print("=" * 60)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print()
        print(f"Metrics Verified: {summary.get('metrics_verified', 0)}")
        print(f"Artifacts Compared: {len(summary.get('artifacts_compared') or [])}")
        print(f"Consistency Checks: {summary.get('consistency_checks', 0)}")
        print(f"Pass: {summary.get('pass_count', 0)}")
        print(f"Fail: {summary.get('fail_count', 0)}")
        print(f"Total Production Bars: {summary.get('authoritative_total_production_bars', 0)}")
        print(f"Normalization Coverage: {summary.get('authoritative_normalization_coverage_percent', 0)}%")
        print(f"Overall Consistency Health: {health.get('overall_consistency_health', 0)}")
        print()
        print("Export Locations")
        print("-" * 60)
        for filename, path in (result.get("export_paths") or {}).items():
            print(f"{filename}: {path}")
        print("=" * 60)
        validation = result.get("statistics_validation") or {}
        export_validation = result.get("export_validation") or {}
        print(
            f"\nValidation: {validation.get('summary', {}).get('passed', 0)}/"
            f"{validation.get('summary', {}).get('total_checks', 0)} PASS"
        )
        print(
            f"Exports: {export_validation.get('summary', {}).get('passed', 0)}/"
            f"{export_validation.get('summary', {}).get('total_checks', 0)} PASS"
        )

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> Any | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

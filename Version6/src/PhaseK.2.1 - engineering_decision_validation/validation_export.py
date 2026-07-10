"""Export Phase K.2.1 validation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from decision_loader import MODEL_VERSION, PHASE
from validation_reporting import ValidationReporting


EXPORT_FILES = (
    "validated_decision_registry.json",
    "decision_validation_registry.json",
    "decision_validation_statistics.json",
    "decision_validation_summary.json",
    "decision_validation_report.json",
    "decision_validation_errors.json",
    "decision_validation_warnings.json",
    "decision_validation_health.json",
    "decision_validation_traceability.json",
    "decision_validation_matrix.json",
    "decision_validation_rules.json",
    "decision_validation_configuration.json",
    "decision_validation_execution_gate.json",
)


class ValidationExport:
    """Write validation JSON/XLSX exports and console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        registry = result.get("validation_registry")
        mapping = {
            "validated_decision_registry.json": registry,
            "decision_validation_registry.json": registry,
            "decision_validation_statistics.json": result.get("statistics"),
            "decision_validation_summary.json": result.get("summary"),
            "decision_validation_report.json": ValidationReporting.build_report(result),
            "decision_validation_errors.json": ValidationReporting.build_errors(
                result.get("validations") or []
            ),
            "decision_validation_warnings.json": ValidationReporting.build_warnings(
                result.get("validations") or []
            ),
            "decision_validation_health.json": result.get("health"),
            "decision_validation_traceability.json": ValidationReporting.build_traceability(
                result.get("validations") or []
            ),
            "decision_validation_matrix.json": ValidationReporting.build_matrix(
                result.get("validations") or []
            ),
            "decision_validation_rules.json": ValidationReporting.build_rules_catalog(),
            "decision_validation_configuration.json": {
                "phase": PHASE,
                "model_version": MODEL_VERSION,
                "config": config,
            },
            "decision_validation_execution_gate.json": result.get("execution_gate"),
        }
        for filename in EXPORT_FILES:
            if filename in {
                "validated_decision_registry.json",
                "decision_validation_registry.json",
            } and not config.get("export_validation_registry", True):
                continue
            if filename == "decision_validation_statistics.json" and not config.get(
                "export_statistics", True
            ):
                continue
            path = output_dir / filename
            ValidationExport._write_json(path, mapping[filename])
            written[filename] = str(path)

        if config.get("export_excel_report", True):
            xlsx_path = output_dir / "decision_validation_report.xlsx"
            ok = ValidationReporting.write_excel(
                xlsx_path,
                result.get("validations") or [],
                result.get("statistics") or {},
            )
            if ok:
                written["decision_validation_report.xlsx"] = str(xlsx_path)

        result["export_paths"] = written
        return written

    @staticmethod
    def validate_exports(
        output_dir: Path,
        export_files: tuple[str, ...],
        *,
        require_excel: bool = True,
    ) -> dict[str, Any]:
        checks = []
        for filename in export_files:
            path = output_dir / filename
            exists = path.exists() and path.stat().st_size > 0
            parsed_ok = False
            if exists:
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                    parsed_ok = True
                except (OSError, json.JSONDecodeError):
                    parsed_ok = False
            checks.append(
                {"name": f"Export Exists {filename}", "status": "PASS" if exists else "FAIL"}
            )
            checks.append(
                {
                    "name": f"Export Valid JSON {filename}",
                    "status": "PASS" if parsed_ok else "FAIL",
                }
            )
        if require_excel:
            xlsx = output_dir / "decision_validation_report.xlsx"
            checks.append(
                {
                    "name": "Export Exists decision_validation_report.xlsx",
                    "status": "PASS" if xlsx.exists() and xlsx.stat().st_size > 0 else "FAIL",
                }
            )
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
        summary = result.get("summary") or {}
        health = result.get("health") or {}
        export_paths = result.get("export_paths") or {}
        print("\n" + "=" * 80)
        print("Engineering Decision Validation Engine")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Engineering Decisions: {summary.get('engineering_decisions', 0)}")
        print(f"Validated Decisions: {summary.get('validated_decisions', 0)}")
        print(f"Invalid Decisions: {summary.get('invalid_decisions', 0)}")
        print(f"Warning Decisions: {summary.get('warning_decisions', 0)}")
        print(f"Validation Coverage: {summary.get('validation_coverage_percent', 0)}%")
        print(f"Execution Allowed: {summary.get('execution_allowed', 0)}")
        print(f"Execution Blocked: {summary.get('execution_blocked', 0)}")
        print(f"Average Validation Score: {summary.get('average_validation_score', 0)}")
        print(f"Broken References: {summary.get('broken_references', 0)}")
        print(f"Broken Traceability: {summary.get('broken_traceability', 0)}")
        print(f"Duplicate Targets: {summary.get('duplicate_execution_targets', 0)}")
        print(f"Validation Health: {health.get('validation_health')}")
        print(f"Execution Health: {health.get('execution_health')}")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")

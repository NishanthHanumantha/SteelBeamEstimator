"""Export engineering quantity validation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_quantity_validation.quantity_traceability import QUANTITY_STATES
from src.engineering_quantity_validation.validation_collector import MODEL_VERSION, PHASE


EXPORT_FILES = (
    "quantity_traceability.json",
    "integration_stage_analysis.json",
    "steel_weight_validation.json",
    "bbs_validation.json",
    "excel_validation.json",
    "lifecycle_validation.json",
    "quantity_dependency_analysis.json",
    "quantity_contribution_analysis.json",
    "integration_matrix.json",
    "engineering_quantity_health.json",
    "quantity_root_cause_summary.json",
    "engineering_quantity_validation_summary.json",
)


class QuantityValidationExporter:
    """Write quantity validation JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "quantity_traceability.json": result.get("quantity_traceability"),
            "integration_stage_analysis.json": result.get("integration_stage_analysis"),
            "steel_weight_validation.json": result.get("steel_weight_validation"),
            "bbs_validation.json": result.get("bbs_validation"),
            "excel_validation.json": result.get("excel_validation"),
            "lifecycle_validation.json": result.get("lifecycle_validation"),
            "quantity_dependency_analysis.json": result.get("quantity_dependency_analysis"),
            "quantity_contribution_analysis.json": result.get("quantity_contribution_analysis"),
            "integration_matrix.json": result.get("integration_matrix"),
            "engineering_quantity_health.json": result.get("engineering_quantity_health"),
            "quantity_root_cause_summary.json": result.get("quantity_root_cause_summary"),
            "engineering_quantity_validation_summary.json": result.get("engineering_quantity_validation_summary"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            QuantityValidationExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        summary = result.get("engineering_quantity_validation_summary") or {}
        health = summary.get("integration_health") or {}
        export_paths = result.get("export_paths") or {}

        print("\n" + "=" * 80)
        print("Engineering Quantity Integration Validation")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Recovered Objects: {summary.get('recovered_objects', 0)}")
        print(f"Recovered Steel Contributors: {summary.get('recovered_steel_contributors', 0)}")
        print(f"Recovered BBS Contributors: {summary.get('recovered_bbs_contributors', 0)}")
        print(f"Recovered Excel Contributors: {summary.get('recovered_excel_contributors', 0)}")
        print(f"Overall Integration Health: {health.get('overall_quantity_integration_health', 0)}")
        print(f"No Regression Status: {summary.get('no_regression_status')}")
        print("")
        print("Top Blocking Reasons")
        print("-" * 80)
        for item in summary.get("top_blocking_reasons") or []:
            print(f"{item.get('reason')} — {item.get('count')}")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


class QuantityValidationExportValidator:
    """Validate quantity integration export completeness."""

    def validate_result(self, result: dict[str, Any]) -> dict[str, Any]:
        traces = (result.get("quantity_traceability") or {}).get("traces") or []
        recovered_count = (result.get("quantity_traceability") or {}).get("trace_count", 0)
        checks = [
            self._check("Model Version 5.26.2", result.get("model_version") == "5.26.2"),
            self._check("Read Only Analysis", result.get("read_only_analysis") is True),
            self._check("Production Not Modified", result.get("production_modified") is False),
            self._check("Every Recovered Object Analysed", len(traces) == recovered_count and recovered_count > 0),
            self._check("First Failure Identified", all(trace.get("first_failure_stage") for trace in traces)),
            self._check(
                "Every Recovered Object Has One Quantity State",
                all(trace.get("current_quantity_state") in QUANTITY_STATES for trace in traces),
            ),
            self._check("Dependency Analysis Complete", bool(result.get("quantity_dependency_analysis"))),
            self._check("Steel Validation Complete", bool(result.get("steel_weight_validation"))),
            self._check("BBS Validation Complete", bool(result.get("bbs_validation"))),
            self._check("Excel Validation Complete", bool(result.get("excel_validation"))),
            self._check("Lifecycle Validation Complete", bool(result.get("lifecycle_validation"))),
            self._check("Integration Matrix Complete", bool((result.get("integration_matrix") or {}).get("rows"))),
            self._check("Root Causes Generated", bool(result.get("quantity_root_cause_summary"))),
            self._check("Health Metrics Generated", bool(result.get("engineering_quantity_health"))),
            self._check("Recommendations Generated", bool((result.get("engineering_quantity_validation_summary") or {}).get("engineering_recommendations"))),
        ]
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

    def validate_exports(self, output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        for filename in export_files:
            path = output_dir / filename
            checks.append(self._check(f"Export Exists {filename}", path.exists()))
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                checks.append(self._check(f"Export JSON Valid {filename}", isinstance(payload, (dict, list))))
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
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}

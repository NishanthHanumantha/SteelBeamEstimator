"""Export calculation integration repair artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_calculation_integration.integration_collector import MODEL_VERSION, PHASE


EXPORT_FILES = (
    "bar_identity_registry.json",
    "readiness_registry.json",
    "dependency_graph_integration.json",
    "calculation_context_integration.json",
    "cut_length_integration.json",
    "lifecycle_integration.json",
    "production_pipeline_integration.json",
    "integration_validation.json",
    "integration_statistics.json",
    "integration_health.json",
    "integration_summary.json",
    "integration_report.json",
)


class IntegrationExporter:
    """Write integration JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "bar_identity_registry.json": result.get("bar_identity_registry"),
            "readiness_registry.json": result.get("readiness_registry"),
            "dependency_graph_integration.json": result.get("dependency_graph_integration"),
            "calculation_context_integration.json": result.get("calculation_context_integration"),
            "cut_length_integration.json": result.get("cut_length_integration"),
            "lifecycle_integration.json": result.get("lifecycle_integration"),
            "production_pipeline_integration.json": result.get("production_pipeline_integration"),
            "integration_validation.json": result.get("integration_validation"),
            "integration_statistics.json": result.get("integration_statistics"),
            "integration_health.json": result.get("integration_health"),
            "integration_summary.json": result.get("integration_summary"),
            "integration_report.json": result.get("integration_report"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            IntegrationExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        summary = result.get("integration_summary") or {}
        health = summary.get("integration_health") or {}
        validation = result.get("integration_validation") or {}
        export_paths = result.get("export_paths") or {}

        print("\n" + "=" * 80)
        print("Engineering Calculation Integration")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print(f"Recovered Bars: {summary.get('recovered_bars', 0)}")
        print(f"Registered Identities: {summary.get('registered_identities', 0)}")
        print(f"Ready Bars: {summary.get('ready_bars', 0)}")
        print(f"Calculated Bars: {summary.get('calculated_bars', 0)}")
        print(f"Steel Generated: {summary.get('steel_generated', 0)}")
        print(f"BBS Generated: {summary.get('bbs_generated', 0)}")
        print(f"Excel Generated: {summary.get('excel_generated', 0)}")
        print(f"Overall Integration Health: {health.get('overall_integration_health', 0)}")
        print(f"No Regression Status: {summary.get('no_regression_status')}")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")
        print(
            f"Validation: {validation.get('summary', {}).get('passed', 0)}/"
            f"{validation.get('summary', {}).get('total_checks', 0)} PASS"
        )

    @staticmethod
    def validate_exports(output_dir: Path, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        for filename in export_files:
            path = output_dir / filename
            checks.append({"name": f"Export Exists {filename}", "status": "PASS" if path.exists() else "FAIL"})
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                checks.append(
                    {
                        "name": f"Export JSON Valid {filename}",
                        "status": "PASS" if isinstance(payload, (dict, list)) else "FAIL",
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
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")

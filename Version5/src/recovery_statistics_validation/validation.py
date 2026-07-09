"""Deterministic validation for statistics consistency engine."""

from __future__ import annotations

from typing import Any, Dict, List


class ConsistencyValidator:
    """Validate reconciliation completeness and read-only execution."""

    def validate(self, result: dict[str, Any]) -> dict[str, Any]:
        reconciliation = result.get("statistics_reconciliation") or {}
        cross_artifact = result.get("cross_artifact_validation") or {}
        lineage = result.get("lineage_consistency") or {}
        health = result.get("consistency_health") or {}
        metric_checks = result.get("metric_verification_checks") or []
        root_causes = result.get("root_cause_analysis") or []

        checks = [
            self._check("Model Version 5.28.1", result.get("model_version") == "5.28.1"),
            self._check("Read-Only Verification", result.get("read_only_analysis") is True),
            self._check("Production Snapshot Generated", bool(result.get("production_snapshot"))),
            self._check("Every Metric Has Authoritative Source", bool((result.get("production_snapshot") or {}).get("authoritative_sources"))),
            self._check("Registry Reconciliation Complete", reconciliation.get("status") == "PASS"),
            self._check("Production Reconciliation Complete", reconciliation.get("fail_count", 1) == 0),
            self._check("Cross Artifact Validation Complete", cross_artifact.get("status") == "PASS"),
            self._check("Lineage Consistency Complete", lineage.get("status") == "PASS"),
            self._check("Metric Verification Complete", all(item.get("status") == "PASS" for item in metric_checks)),
            self._check("Coverage Reconciliation Complete", self._coverage_pass(reconciliation)),
            self._check("Health Metrics Generated", bool(health)),
            self._check("Root Causes Generated", isinstance(root_causes, list)),
            self._check("Statistics Summary Generated", bool(result.get("statistics_summary"))),
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

    @staticmethod
    def _coverage_pass(reconciliation: dict[str, Any]) -> bool:
        matrix = reconciliation.get("matrix") or []
        coverage_rows = [row for row in matrix if "Coverage" in str(row.get("metric") or "")]
        if not coverage_rows:
            return False
        return all(row.get("status") == "PASS" for row in coverage_rows)

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}

    def validate_exports(self, output_dir, export_files: tuple[str, ...]) -> dict[str, Any]:
        from src.recovery_statistics_validation.export import ConsistencyExporter

        return ConsistencyExporter.validate_exports(output_dir, export_files)

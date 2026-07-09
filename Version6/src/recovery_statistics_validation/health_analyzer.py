"""Compute consistency health scores."""

from __future__ import annotations

from typing import Any, Dict


class HealthAnalyzer:
    """Derive consistency health metrics."""

    def analyze(
        self,
        reconciliation: dict[str, Any],
        cross_artifact: dict[str, Any],
        lineage: dict[str, Any],
        metric_checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        statistics_consistency = self._percent(
            reconciliation.get("pass_count", 0),
            reconciliation.get("consistency_checks", 1),
        )
        artifact_consistency = 100.0 if cross_artifact.get("status") == "PASS" else 0.0
        registry_consistency = self._registry_score(cross_artifact.get("registry_checks") or [])
        dashboard_consistency = statistics_consistency
        reporting_consistency = self._percent(
            sum(1 for item in metric_checks if item.get("status") == "PASS"),
            max(len(metric_checks), 1),
        )
        traceability_consistency = self._percent(
            lineage.get("passed", 0),
            max(lineage.get("chain_count", 1), 1),
        )
        overall = round(
            (
                statistics_consistency * 0.25
                + artifact_consistency * 0.15
                + registry_consistency * 0.15
                + dashboard_consistency * 0.1
                + reporting_consistency * 0.2
                + traceability_consistency * 0.15
            ),
            2,
        )
        return {
            "statistics_consistency": statistics_consistency,
            "artifact_consistency": artifact_consistency,
            "registry_consistency": registry_consistency,
            "dashboard_consistency": dashboard_consistency,
            "reporting_consistency": reporting_consistency,
            "traceability_consistency": traceability_consistency,
            "overall_consistency_health": overall,
        }

    @staticmethod
    def _percent(passed: int, total: int) -> float:
        return round((passed / max(total, 1)) * 100, 2)

    @staticmethod
    def _registry_score(checks: list[dict[str, Any]]) -> float:
        if not checks:
            return 0.0
        passed = sum(1 for item in checks if item.get("status") == "PASS")
        return round((passed / len(checks)) * 100, 2)

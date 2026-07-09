"""Reconcile metrics across registry, production, and reporting artifacts."""

from __future__ import annotations

from typing import Any, Dict, List


class ReconciliationEngine:
    """Compare authoritative production metrics against all consumers."""

    def reconcile(self, snapshot: dict[str, Any], authoritative: dict[str, Any]) -> dict[str, Any]:
        matrix = MetricMatrixBuilder.build(snapshot, authoritative)
        mismatches = [row for row in matrix if row.get("status") == "FAIL"]
        return {
            "metrics_verified": len(matrix),
            "artifacts_compared": self._artifacts_compared(snapshot),
            "consistency_checks": len(matrix),
            "pass_count": sum(1 for row in matrix if row.get("status") == "PASS"),
            "fail_count": len(mismatches),
            "matrix": matrix,
            "top_mismatches": mismatches[:10],
            "status": "PASS" if not mismatches else "FAIL",
        }

    @staticmethod
    def _artifacts_compared(snapshot: dict[str, Any]) -> List[str]:
        return sorted(
            key
            for key, loaded in (snapshot.get("load_status") or {}).items()
            if loaded
        )


class MetricMatrixBuilder:
    """Build metric consistency matrix rows."""

    @staticmethod
    def build(snapshot: dict[str, Any], authoritative: dict[str, Any]) -> List[dict[str, Any]]:
        recovery_stats = snapshot.get("recovery_statistics") or {}
        recovery_summary = snapshot.get("recovery_summary") or {}
        recovery_health = snapshot.get("recovery_health") or {}
        expansion_stats = snapshot.get("expansion_statistics") or {}
        expansion_summary = snapshot.get("expansion_summary") or {}
        impact_summary = snapshot.get("recovery_impact_summary") or {}

        rows: List[dict[str, Any]] = []
        rows.append(
            MetricMatrixBuilder._row(
                metric="J.1 Recovered Objects",
                source="recovery_registry.json",
                authoritative=authoritative["j1_registry_count"],
                production=authoritative["j1_recovered_bars"],
                summary=recovery_summary.get("recovered_objects"),
                statistics=recovery_stats.get("recovered_objects"),
                validation=recovery_stats.get("recovery_success_count"),
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="J.1 Recovered Bars",
                source="recovery_registry.json",
                authoritative=authoritative["j1_recovered_bars"],
                production=authoritative["j1_recovered_bars"],
                summary=recovery_summary.get("recovered_normalized_bars"),
                statistics=recovery_stats.get("recovered_normalized_bars"),
                validation=recovery_stats.get("recovered_normalized_bars"),
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="J.2 Recovered Objects",
                source="expansion_registry.json",
                authoritative=authoritative["j2_registry_count"],
                production=authoritative["j2_recovered_bars"],
                summary=expansion_summary.get("recovered"),
                statistics=expansion_stats.get("recovered"),
                validation=expansion_stats.get("recovered"),
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="Total Production Bars",
                source="reinforcement_objects.json",
                authoritative=authoritative["total_production_bars"],
                production=authoritative["total_production_bars"],
                summary=expansion_stats.get("coverage_after_bars"),
                statistics=expansion_stats.get("coverage_after_bars"),
                validation=authoritative["total_production_bars"],
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="Native Bars (Pre-Recovery)",
                source="reinforcement_objects.json",
                authoritative=authoritative["native_bars"],
                production=authoritative["native_bars"],
                summary=impact_summary.get("normalized_bars", {}).get("before"),
                statistics=None,
                validation=authoritative["native_bars"],
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="Normalization Coverage % (Total)",
                source="reinforcement_objects.json + inventory",
                authoritative=authoritative["normalization_coverage_percent"],
                production=authoritative["normalization_coverage_percent"],
                summary=expansion_summary.get("coverage_after_percent"),
                statistics=expansion_stats.get("coverage_after_percent"),
                validation=authoritative["normalization_coverage_percent"],
                console=expansion_stats.get("coverage_after_percent"),
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="J.1 Scoped Coverage % (Post-J.1)",
                source="native+j1 bars / inventory",
                authoritative=authoritative["post_j1_coverage_percent"],
                production=authoritative["post_j1_coverage_percent"],
                summary=recovery_summary.get("steel_coverage_after_percent"),
                statistics=recovery_health.get("steel_coverage_after_percent"),
                validation=impact_summary.get("inventory_coverage_percent", {}).get("after"),
                dashboard=impact_summary.get("qa_dashboard_impact", {})
                .get("normalization_coverage", {})
                .get("after"),
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="Inventory Count",
                source="reinforcement_inventory.json",
                authoritative=authoritative["inventory_count"],
                production=authoritative["inventory_count"],
                summary=expansion_summary.get("inventory_count"),
                statistics=expansion_stats.get("inventory_count"),
                validation=authoritative["inventory_count"],
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="Expansion Coverage Before Bars",
                source="reinforcement_objects.json",
                authoritative=authoritative["total_production_bars"],
                production=authoritative["total_production_bars"],
                summary=expansion_summary.get("coverage_before_bars"),
                statistics=expansion_stats.get("coverage_before_bars"),
                validation=expansion_stats.get("coverage_before_bars"),
                console=expansion_stats.get("coverage_before_bars"),
            )
        )
        rows.append(
            MetricMatrixBuilder._row(
                metric="Expansion Coverage After Bars",
                source="reinforcement_objects.json",
                authoritative=authoritative["total_production_bars"],
                production=authoritative["total_production_bars"],
                summary=expansion_summary.get("coverage_after_bars"),
                statistics=expansion_stats.get("coverage_after_bars"),
                validation=expansion_stats.get("coverage_after_bars"),
                console=expansion_stats.get("coverage_after_bars"),
            )
        )
        return rows

    @staticmethod
    def _row(
        metric: str,
        source: str,
        authoritative: Any,
        production: Any,
        summary: Any = None,
        statistics: Any = None,
        validation: Any = None,
        dashboard: Any = None,
        console: Any = None,
    ) -> dict[str, Any]:
        observed = {
            "authoritative": authoritative,
            "production": production,
            "summary": summary,
            "statistics": statistics,
            "validation": validation,
            "dashboard": dashboard,
            "console": console,
        }
        comparable = {
            key: value
            for key, value in observed.items()
            if value is not None and key != "authoritative"
        }
        mismatched = [
            key
            for key, value in comparable.items()
            if not MetricMatrixBuilder._values_equal(value, authoritative)
        ]
        status = "PASS" if not mismatched else "FAIL"
        reason = None
        resolution = None
        if mismatched:
            reason = f"Consumer mismatch: {', '.join(mismatched)}"
            resolution = f"Use authoritative value {authoritative} from {source}"
        return {
            "metric": metric,
            "authoritative_source": source,
            "authoritative_value": authoritative,
            "observed_values": observed,
            "summary_value": summary,
            "statistics_value": statistics,
            "dashboard_value": dashboard,
            "console_value": console,
            "validation_value": validation,
            "status": status,
            "mismatch_reason": reason,
            "resolution": resolution,
            "mismatched_consumers": mismatched,
        }

    @staticmethod
    def _values_equal(left: Any, right: Any) -> bool:
        if left is None or right is None:
            return left is right
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return round(float(left), 2) == round(float(right), 2)
        return left == right

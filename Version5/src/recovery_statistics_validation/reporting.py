"""Reporting for recovery statistics consistency."""

from __future__ import annotations

from typing import Any, Dict


class ConsistencyReporting:
    """Build summary and report payloads."""

    def build_summary(
        self,
        authoritative: dict[str, Any],
        reconciliation: dict[str, Any],
        health: dict[str, Any],
        validation: dict[str, Any],
        root_causes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "metrics_verified": reconciliation.get("metrics_verified"),
            "artifacts_compared": reconciliation.get("artifacts_compared"),
            "consistency_checks": reconciliation.get("consistency_checks"),
            "pass_count": reconciliation.get("pass_count"),
            "fail_count": reconciliation.get("fail_count"),
            "authoritative_normalization_coverage_percent": authoritative.get("normalization_coverage_percent"),
            "authoritative_total_production_bars": authoritative.get("total_production_bars"),
            "authoritative_j1_recovered_bars": authoritative.get("j1_recovered_bars"),
            "authoritative_j2_recovered_bars": authoritative.get("j2_recovered_bars"),
            "consistency_health": health,
            "validation_status": validation.get("status"),
            "top_mismatches": reconciliation.get("top_mismatches"),
            "root_cause_count": len(root_causes),
            "engineering_recommendation": self._recommendation(validation, root_causes),
        }

    def build_report(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": result.get("phase"),
            "model_version": result.get("model_version"),
            "engine_version": result.get("engine_version"),
            "run_timestamp": result.get("run_timestamp"),
            "read_only_analysis": result.get("read_only_analysis"),
            "summary": result.get("statistics_summary"),
            "authoritative_sources": (result.get("production_snapshot") or {}).get("authoritative_sources"),
            "health": result.get("consistency_health"),
            "validation": result.get("statistics_validation"),
            "root_causes": result.get("root_cause_analysis"),
        }

    @staticmethod
    def _recommendation(validation: dict[str, Any], root_causes: list[dict[str, Any]]) -> str:
        if validation.get("status") == "PASS":
            return "All recovery statistics reconcile with authoritative production artifacts."
        if root_causes:
            return root_causes[0].get("resolution") or "Review top mismatches and align consumers to production_snapshot.json."
        return "Review metric_consistency_matrix.json and align reporting consumers to authoritative sources."
